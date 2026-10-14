"""Bounded, road-aligned preview states; SUMO still executes city driving.

These sampled previews account for observed traffic, current signal schedules,
lane speed limits and adjacent-lane transition time. They are not a certificate
of continuous collision avoidance or the straight-road KARS planner.
"""
import math
import xml.etree.ElementTree as ET

import networkx as nx


def project(points,x,y):
    best=None;station=0
    for i,(a,b) in enumerate(zip(points,points[1:])):
        length=math.dist(a,b)
        if not length:continue
        fraction=max(0,min(1,((x-a[0])*(b[0]-a[0])+(y-a[1])*(b[1]-a[1]))/length**2))
        p=[a[0]+fraction*(b[0]-a[0]),a[1]+fraction*(b[1]-a[1])]
        candidate=(math.dist(p,(x,y)),station+fraction*length,i,p)
        if best is None or candidate[0]<best[0]:best=candidate
        station+=length
    return best


class CityReachability:
    def __init__(self,path):
        root=ET.parse(path).getroot()
        self.lanes={lane.get('id'):{'shape':[[float(v) for v in p.split(',')] for p in lane.get('shape').split()],
                                  'speed':float(lane.get('speed')),'edge':edge.get('id')}
                    for edge in root.findall('edge') for lane in edge.findall('lane')}
        self.graph=nx.DiGraph();self.graph.add_nodes_from(self.lanes)
        for link in root.findall('connection'):
            a=link.get('from')+'_'+link.get('fromLane');b=link.get('via') or link.get('to')+'_'+link.get('toLane')
            if a in self.lanes and b in self.lanes:
                self.graph.add_edge(a,b,weight=sum(math.dist(x,y) for x,y in zip(self.lanes[b]['shape'],self.lanes[b]['shape'][1:])))

    def lane_path(self,lane_id,route,x,y):
        if lane_id not in self.lanes:return []
        points=self.lanes[lane_id]['shape'];nearest=project(points,x,y)
        if nearest is None:return []
        chain=[(nearest[3],lane_id)]+[(p,lane_id) for p in points[nearest[2]+1:]]
        current=lane_id
        for edge in route:
            if edge==self.lanes[current]['edge']:continue
            targets=[lid for lid,v in self.lanes.items() if v['edge']==edge]
            allowed=[lid for lid,v in self.lanes.items() if v['edge'].startswith(':') or lid==current or v['edge']==edge]
            graph=self.graph.subgraph(allowed);choices=[]
            for target in targets:
                try:
                    path=nx.shortest_path(graph,current,target,weight='weight')
                    choices.append((sum(graph[a][b]['weight'] for a,b in zip(path,path[1:])),path))
                except nx.NetworkXNoPath:pass
            if not choices:break
            path=min(choices,key=lambda item:item[0])[1]
            for item in path[1:]:chain.extend((p,item) for p in self.lanes[item]['shape'])
            current=path[-1]
            if len(chain)>100:break
        segments=[];distance=0
        for (a,la),(b,lb) in zip(chain,chain[1:]):
            length=math.dist(a,b)
            if length>1e-6:
                segments.append({'a':a,'b':b,'begin':distance,'end':distance+length,'lane':lb,
                                 'speed':min(self.lanes[la]['speed'],self.lanes[lb]['speed'])})
                distance+=length
        return segments

    @staticmethod
    def pose(path,distance):
        for segment in path:
            if distance<=segment['end']+1e-6:
                r=max(0,min(1,(distance-segment['begin'])/(segment['end']-segment['begin'])))
                a,b=segment['a'],segment['b'];heading=math.degrees(math.atan2(b[0]-a[0],b[1]-a[1]))%360
                return a[0]+r*(b[0]-a[0]),a[1]+r*(b[1]-a[1]),heading,segment['lane']
        return None

    def forecast(self,connection,ego,vehicles,now):
        route=connection.vehicle.getRoute('ego');index=max(0,connection.vehicle.getRouteIndex('ego'))
        remaining=list(route[index:index+4])
        if ego.road_id.startswith(':'):remaining=list(route[index+1:index+5])
        candidates=[ego.lane_id] if ego.road_id.startswith(':') else [lid for lid,v in self.lanes.items() if v['edge']==ego.road_id]
        paths={lid:self.lane_path(lid,remaining,ego.x,ego.y) for lid in candidates}
        paths={lid:path for lid,path in paths.items() if path}
        tls=connection.vehicle.getNextTLS('ego');signal=None
        if tls and tls[0][2]>=0:
            tid,link,distance,color=tls[0]
            logic=next((p for p in connection.trafficlight.getAllProgramLogics(tid) if p.programID==connection.trafficlight.getProgram(tid)),None)
            if logic and logic.type==0:
                signal=(max(0,distance-3),link,logic,connection.trafficlight.getPhase(tid),connection.trafficlight.getNextSwitch(tid)-now)
        def red_at(t):
            if signal is None:return False
            _,link,logic,phase,remaining_time=signal
            while t>remaining_time:
                phase=(phase+1)%len(logic.phases);remaining_time+=logic.phases[phase].duration
            return logic.phases[phase].state[link].lower() in ('r','y')
        raw=[];valid=[];all_nodes={};parents={};layer=[{'id':0,'distance':0.,'speed':ego.speed,'layer':0,'path':None,'valid':True}];counter=1
        for step in range(1,6):
            next_layer=[];seen=set()
            for previous in layer:
                for lid in ([previous['path']] if previous['path'] else paths):
                    path=paths[lid]
                    for acceleration in (-4.,0.,2.):
                        speed=max(0.,min(13.9,previous['speed']+acceleration))
                        distance=previous['distance']+.5*(previous['speed']+speed)
                        key=(lid,round(distance,1),round(speed,1))
                        if key in seen:continue
                        seen.add(key);pose=self.pose(path,distance)
                        if pose is None:continue
                        x,y,heading,lane=pose
                        if lid!=ego.lane_id and step<7.0 and self.lanes[lane]['edge']!=ego.road_id:continue
                        # Smoothly converge from the observed position to an adjacent lane.
                        initial=self.pose(path,0);blend=min(1,step/7.0);blend=blend*blend*(3-2*blend)
                        if previous['speed']<.01 and speed<.01:blend=previous.get('blend',0.)
                        x+=(ego.x-initial[0])*(1-blend);y+=(ego.y-initial[1])*(1-blend)
                        rate=6*min(1,step/7.0)*(1-min(1,step/7.0))/7.0
                        dx=speed*math.sin(math.radians(heading))-(ego.x-initial[0])*rate
                        dy=speed*math.cos(math.radians(heading))-(ego.y-initial[1])*rate
                        if speed>.1 and math.hypot(dx,dy)>.1:heading=math.degrees(math.atan2(dx,dy))%360
                        node={'id':counter,'x':x,'y':y,'heading':heading,'speed':speed,'layer':step,
                              'time':now+step,'distance':distance,'lane_id':lane,'path':lid,'blend':blend}
                        counter+=1;raw.append(node);all_nodes[node['id']]=node;parents[node['id']]=previous['id']
                        limit=min(s['speed'] for s in path if s['end']>=previous['distance'] and s['begin']<=distance)
                        permitted=previous['valid'] and max(previous['speed'],speed)<=limit+.01
                        if lid!=ego.lane_id and distance<5*min(step,7.0):permitted=False
                        if lid!=ego.lane_id and step<7.0 and self.lanes[lane]['edge']!=ego.road_id:permitted=False
                        if signal and previous['distance']<=signal[0]<distance:
                            delta=signal[0]-previous['distance'];a=speed-previous['speed'];v=previous['speed']
                            crossing=delta/max(v,1e-6) if abs(a)<1e-6 else (-v+math.sqrt(max(0,v*v+2*a*delta)))/a
                            if red_at(step-1+max(0,min(1,crossing))):permitted=False
                        # Check swept motion at 0.2 s intervals, including crossings.
                        for fraction in (.2,.4,.6,.8,1.):
                            elapsed=step-1+fraction
                            swept=previous['distance']+previous['speed']*fraction+.5*(speed-previous['speed'])*fraction**2
                            px,py,ph,_=self.pose(path,swept)
                            u=min(1,elapsed/7.0);blend=u*u*(3-2*u)
                            if previous['speed']<.01 and speed<.01:blend=previous.get('blend',0.)
                            px+=(ego.x-initial[0])*(1-blend);py+=(ego.y-initial[1])*(1-blend)
                            sv=previous['speed']+(speed-previous['speed'])*fraction
                            rate=6*u*(1-u)/7.0
                            sx=sv*math.sin(math.radians(ph))-(ego.x-initial[0])*rate
                            sy=sv*math.cos(math.radians(ph))-(ego.y-initial[1])*rate
                            if math.hypot(sx,sy)>.1:ph=math.degrees(math.atan2(sx,sy))%360
                            direction=(math.sin(math.radians(ph)),math.cos(math.radians(ph)))
                            cx=px-ego.length/2*direction[0];cy=py-ego.length/2*direction[1]
                            for v in vehicles:
                                if v.vehicle_id=='ego':continue
                                angle=math.radians(v.heading);vx=v.x+(v.speed*elapsed-v.length/2)*math.sin(angle);vy=v.y+(v.speed*elapsed-v.length/2)*math.cos(angle)
                                dx,dy=vx-cx,vy-cy
                                longitudinal=abs(math.sin(angle)*direction[0]+math.cos(angle)*direction[1])
                                lateral=abs(-math.sin(angle)*direction[1]+math.cos(angle)*direction[0])
                                long_extent=ego.length/2+v.length/2*longitudinal+v.width/2*lateral+3
                                lat_extent=ego.width/2+v.length/2*lateral+v.width/2*longitudinal+.3
                                if abs(dx*direction[0]+dy*direction[1])<long_extent and abs(-dx*direction[1]+dy*direction[0])<lat_extent:
                                    permitted=False;break
                            if not permitted:break
                        node['valid']=permitted
                        if permitted:valid.append(node)
                        next_layer.append(node)
            # Uniform quotas preserve both adjacent-lane branches without runaway growth.
            layer=[]
            for lid in paths:
                valid_group=sorted([n for n in next_layer if n['path']==lid and n['valid']],key=lambda n:(n['distance'],n['speed']))
                invalid_group=sorted([n for n in next_layer if n['path']==lid and not n['valid']],key=lambda n:(n['distance'],n['speed']))
                quota=min(24,len(valid_group)) if not invalid_group else min(16,len(valid_group))
                for group,count in [(valid_group,quota),(invalid_group,24-quota)]:
                    count=min(count,len(group))
                    if count==1:layer.append(group[-1])
                    elif count>1:layer.extend(group[round(i*(len(group)-1)/(count-1))] for i in range(count))
        preferred=set()
        if abs(ego.lateral_position)>.05:
            for lid,path in paths.items():
                initial=self.pose(path,0);angle=math.radians(initial[2]);normal=(-math.cos(angle),math.sin(angle))
                offset=(ego.x-initial[0])*normal[0]+(ego.y-initial[1])*normal[1]
                observed_lateral=-ego.speed*math.sin(math.radians(ego.heading-initial[2]))
                if abs(observed_lateral)>.1 and observed_lateral*offset<0:preferred.add(lid)
        continuation=[n for n in valid if n['path'] in preferred]
        choices=continuation or [n for n in valid if n['layer']==5] or valid
        best=max(choices,key=lambda n:(n['layer'],n['distance']-(3 if n['path']!=ego.lane_id else 0)),default=None)
        selected=[]
        while best:
            selected.append(best)
            best=all_nodes.get(parents[best['id']])
        selected.reverse()
        trajectory=[{'x':ego.x,'y':ego.y,'time':now,'speed':ego.speed}]
        if selected:
            path=paths[selected[0]['path']];initial=self.pose(path,0)
            previous={'distance':0.,'speed':ego.speed,'layer':0}
            for state in selected:
                count=max(10,math.ceil((state['distance']-previous['distance'])/.75))
                for i in range(1,count+1):
                    fraction=i/count;elapsed=previous['layer']+fraction
                    distance=previous['distance']+previous['speed']*fraction+.5*(state['speed']-previous['speed'])*fraction**2
                    x,y,_,_=self.pose(path,distance)
                    u=min(1,elapsed/7.0);blend=u*u*(3-2*u)
                    if previous['speed']<.01 and state['speed']<.01:blend=previous.get('blend',0.)
                    trajectory.append({'x':x+(ego.x-initial[0])*(1-blend),'y':y+(ego.y-initial[1])*(1-blend),
                                       'time':now+elapsed,'speed':previous['speed']+(state['speed']-previous['speed'])*fraction})
                previous=state
        return {'time':now,'raw':raw,'feasible':valid,'trajectory':trajectory,
                'model':'5 s sampled road-aligned kinematic preview; signal schedule, speed limits and constant-speed traffic filtering',
                'raw_count':len(raw),'feasible_count':len(valid),'nominal_lateral_preview_duration':7.0,'executed_by':'SUMO'}
