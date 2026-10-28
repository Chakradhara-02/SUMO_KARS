"""Bounded, road-aligned preview states; SUMO still executes city driving.

These sampled previews account for observed traffic, current signal schedules,
lane speed limits and adjacent-lane transition time. They are not a certificate
of continuous collision avoidance or the straight-road KARS planner.
"""
import math
import xml.etree.ElementTree as ET

import networkx as nx


def footprint_conflict(ego_center,ego_heading,ego_length,ego_width,other_center,other_heading,other_length,other_width,margin=.3):
    """Four separating axes avoid false overlaps at angled junctions."""
    eh=math.radians(ego_heading);oh=math.radians(other_heading)
    forward=(math.sin(eh),math.cos(eh));side=(-forward[1],forward[0])
    other_forward=(math.sin(oh),math.cos(oh));other_side=(-other_forward[1],other_forward[0])
    delta=(other_center[0]-ego_center[0],other_center[1]-ego_center[1])
    dot=lambda a,b:a[0]*b[0]+a[1]*b[1]
    for axis in (forward,side,other_forward,other_side):
        extent=(ego_length/2*abs(dot(axis,forward))+ego_width/2*abs(dot(axis,side))+
                other_length/2*abs(dot(axis,other_forward))+other_width/2*abs(dot(axis,other_side))+margin)
        if abs(dot(delta,axis))>=extent:return False
    return True


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
        self.lanes={lane.get('id'):{'shape':[[float(v) for v in p.split(',')[:2]] for p in lane.get('shape').split()],
                                  'speed':float(lane.get('speed')),'edge':edge.get('id')}
                    for edge in root.findall('edge') for lane in edge.findall('lane')}
        self.graph=nx.DiGraph();self.graph.add_nodes_from(self.lanes)
        self.elevations={lane.get('id'):[[float(v) for v in p.split(',')] for p in lane.get('shape').split()] for edge in root.findall('edge') for lane in edge.findall('lane')}
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

    def elevation(self,lane,x,y):
        points=self.elevations.get(lane,[]);nearest=project([p[:2] for p in points],x,y)
        if nearest is None:return 0.
        i=nearest[2];a,b=points[i:i+2];length=math.hypot(b[0]-a[0],b[1]-a[1]);t=math.hypot(nearest[3][0]-a[0],nearest[3][1]-a[1])/max(.001,length)
        return (a[2] if len(a)>2 else 0)*(1-t)+(b[2] if len(b)>2 else 0)*t

    @staticmethod
    def pose(path,distance):
        for segment in path:
            if distance<=segment['end']+1e-6:
                r=max(0,min(1,(distance-segment['begin'])/(segment['end']-segment['begin'])))
                a,b=segment['a'],segment['b'];heading=math.degrees(math.atan2(b[0]-a[0],b[1]-a[1]))%360
                return a[0]+r*(b[0]-a[0]),a[1]+r*(b[1]-a[1]),heading,segment['lane']
        return None

    def aligned_pose(self,path,distance,elapsed,ego,hold=None):
        """Use the road's local normal, including bends, for lateral convergence."""
        x,y,heading,lane=self.pose(path,distance)
        start=self.pose(path,0);angle=math.radians(start[2])
        offset=(ego.x-start[0])*(-math.cos(angle))+(ego.y-start[1])*math.sin(angle)
        u=min(1.,elapsed/7.);blend=u*u*(3-2*u) if hold is None else hold
        angle=math.radians(heading)
        x-=math.cos(angle)*offset*(1-blend);y+=math.sin(angle)*offset*(1-blend)
        return x,y,heading,lane,blend

    def forecast(self,connection,ego,vehicles,now,route_override=None,sensor_range=120.):
        route=connection.vehicle.getRoute('ego');index=max(0,connection.vehicle.getRouteIndex('ego'))
        remaining=list(route[index:index+4])
        if route_override is not None:remaining=list(route_override[:5])
        if ego.road_id.startswith(':'):remaining=list(route[index+1:index+5])
        candidates=[ego.lane_id] if ego.road_id.startswith(':') else [lid for lid,v in self.lanes.items() if v['edge']==ego.road_id]
        paths={lid:self.lane_path(lid,remaining,ego.x,ego.y) for lid in candidates}
        paths={lid:path for lid,path in paths.items() if path}
        nearby=[v for v in vehicles if v.vehicle_id!='ego' and math.hypot(v.x-ego.x,v.y-ego.y)<=sensor_range]
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
        raw=[];valid=[];all_nodes={};parents={};layer=[{'id':0,'distance':0.,'speed':ego.speed,'layer':0,'path':None,'valid':True,'cost':0.,'acceleration':ego.acceleration}];counter=1
        for step in range(1,6):
            next_layer=[];seen=set()
            for previous in layer:
                if not previous['valid']:continue
                for lid in ([previous['path']] if previous['path'] else paths):
                    path=paths[lid]
                    for acceleration in (-4.,0.,2.):
                        speed=max(0.,min(22.2,previous['speed']+acceleration))
                        distance=previous['distance']+.5*(previous['speed']+speed)
                        key=(lid,round(distance,1),round(speed,1),previous['valid'],acceleration)
                        if key in seen:continue
                        seen.add(key);pose=self.pose(path,distance)
                        if pose is None:continue
                        x,y,heading,lane=pose
                        if lid!=ego.lane_id and step<7.0 and self.lanes[lane]['edge']!=ego.road_id:continue
                        # Smoothly converge from the observed position to an adjacent lane.
                        hold=previous.get('blend',0.) if previous['speed']<.01 and speed<.01 else None
                        x,y,heading,lane,blend=self.aligned_pose(path,distance,step,ego,hold)
                        node={'id':counter,'x':x,'y':y,'heading':heading,'speed':speed,'layer':step,
                              'time':now+step,'distance':distance,'lane_id':lane,'path':lid,'blend':blend,'collision':False,'blocked_by':[]}
                        counter+=1;raw.append(node);all_nodes[node['id']]=node;parents[node['id']]=previous['id']
                        limit=min(s['speed'] for s in path if s['end']>=previous['distance'] and s['begin']<=distance)
                        reasons=[]
                        permitted=previous['valid']
                        if not permitted:reasons.append('Unsafe earlier transition')
                        if lid!=ego.lane_id and distance<5*min(step,7.0):
                            permitted=False;reasons.append('Insufficient forward motion for lane change')
                        if lid!=ego.lane_id and step<7.0 and self.lanes[lane]['edge']!=ego.road_id:permitted=False
                        if signal and previous['distance']<=signal[0]<distance:
                            delta=signal[0]-previous['distance'];a=speed-previous['speed'];v=previous['speed']
                            crossing=delta/max(v,1e-6) if abs(a)<1e-6 else (-v+math.sqrt(max(0,v*v+2*a*delta)))/a
                            if red_at(step-1+max(0,min(1,crossing))):
                                permitted=False;reasons.append('Red or amber signal at stop-line crossing')
                        # Check swept motion at 0.2 s intervals, including crossings.
                        for fraction in (.2,.4,.6,.8,1.):
                            elapsed=step-1+fraction
                            swept=previous['distance']+previous['speed']*fraction+.5*(speed-previous['speed'])*fraction**2
                            px,py,ph,swept_lane=self.pose(path,swept)
                            limit=self.lanes[swept_lane]['speed']
                            sv=previous['speed']+(speed-previous['speed'])*fraction
                            braking_observed_overspeed=(swept_lane==ego.lane_id and previous['speed']>limit and speed<previous['speed'])
                            if sv>limit+.01 and not braking_observed_overspeed:
                                permitted=False;reasons.append('Lane speed limit exceeded');break
                            px,py,ph,swept_lane,blend=self.aligned_pose(path,swept,elapsed,ego,hold)
                            direction=(math.sin(math.radians(ph)),math.cos(math.radians(ph)))
                            cx=px-ego.length/2*direction[0];cy=py-ego.length/2*direction[1]
                            for v in nearby:
                                if abs(v.z-self.elevation(swept_lane,px,py))>2.5:continue
                                rear=(v.x-ego.x)*math.sin(math.radians(ego.heading))+(v.y-ego.y)*math.cos(math.radians(ego.heading))
                                if lid==ego.lane_id and v.lane_id==ego.lane_id and rear < -ego.length:continue
                                angle=math.radians(v.heading);vx=v.x+(v.speed*elapsed-v.length/2)*math.sin(angle);vy=v.y+(v.speed*elapsed-v.length/2)*math.cos(angle)
                                dx,dy=vx-cx,vy-cy
                                margin=min(1.2,.3+max(0.,sv-v.speed)*.1)
                                if footprint_conflict((cx,cy),ph,ego.length,ego.width,(vx,vy),v.heading,v.length,v.width,margin):
                                    permitted=False;node['collision']=True;node['blocked_by'].append(v.vehicle_id)
                                    node['hazard_point']={'x':px,'y':py,'z':self.elevation(swept_lane,px,py),'time':now+elapsed}
                                    reasons.append('Blocked by nearby vehicle: '+v.vehicle_id);break
                            if not permitted:break
                        node['valid']=permitted
                        node['reasons']=list(dict.fromkeys(reasons))
                        actual_acceleration=speed-previous['speed']
                        node['acceleration']=actual_acceleration
                        node['cost']=previous.get('cost',0.)+.35*actual_acceleration**2+1.2*(actual_acceleration-previous.get('acceleration',ego.acceleration))**2
                        node['cost']+=.15*(max(0.,min(limit,13.9)-speed))**2
                        if previous['id']==0 and lid!=ego.lane_id:node['cost']+=8.
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
        best=max(choices,key=lambda n:(n['layer'],n['distance']-n['cost']),default=None)
        selected=[]
        while best:
            selected.append(best)
            best=all_nodes.get(parents[best['id']])
        selected.reverse()
        trajectory=[{'x':ego.x,'y':ego.y,'z':ego.z,'time':now,'speed':ego.speed}]
        if selected:
            path=paths[selected[0]['path']];initial=self.pose(path,0)
            previous={'distance':0.,'speed':ego.speed,'layer':0}
            for state in selected:
                count=max(10,math.ceil((state['distance']-previous['distance'])/.75))
                for i in range(1,count+1):
                    fraction=i/count;elapsed=previous['layer']+fraction
                    distance=previous['distance']+previous['speed']*fraction+.5*(state['speed']-previous['speed'])*fraction**2
                    hold=previous.get('blend',0.) if previous['speed']<.01 and state['speed']<.01 else None
                    x,y,_,trajectory_lane,_=self.aligned_pose(path,distance,elapsed,ego,hold)
                    trajectory.append({'x':x,'y':y,'z':self.elevation(trajectory_lane,x,y),'time':now+elapsed,
                                       'speed':previous['speed']+(state['speed']-previous['speed'])*fraction})
                previous=state
        for node in raw:node['z']=self.elevation(node['lane_id'],node['x'],node['y'])
        reference=paths.get(ego.lane_id,next(iter(paths.values()),[]))
        reference_points=[{'x':ego.x,'y':ego.y}]+[{'x':segment['b'][0],'y':segment['b'][1]} for segment in reference if segment['begin']<120]
        return {'reference_path':reference_points,'status':'feasible' if valid else 'waiting' if ego.speed<.1 else 'no_feasible_forecast','time':now,'raw':raw,'feasible':valid,'trajectory':trajectory,
                'model':'5 s sampled road-aligned kinematic preview; signal schedule, speed limits and constant-speed traffic filtering',
                'optimization':{'method':'bounded sampled trajectory search','objective':'progress, acceleration, jerk and lane continuity','selected_cost':selected[-1]['cost'] if selected else None},
                'display_radius':min(sensor_range,45.),'origin':{'x':ego.x,'y':ego.y},
                'unsafe':[n for n in raw if n['collision']],'restricted':[n for n in raw if not n['valid'] and not n['collision']],'raw_count':len(raw),'feasible_count':len(valid),'nominal_lateral_preview_duration':7.0,'executed_by':'SUMO'}
