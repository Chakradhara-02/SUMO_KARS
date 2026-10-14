"""City routing and measured traffic on a separate, bidirectional SUMO grid."""
import json
import math
import random
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import networkx as nx
import pandas as pd
import traci
import traci.constants as tc

from .models import ROOT, Vehicle
from .storage import atomic_json, read_json
from .sumo_setup import binary

CITY_POINTS=[{'id':f'n{x}_{y}','name':name,'x':x*180,'y':y*180} for x,y,name in [
    (0,0,'Southwest Bus Stand'),(2,0,'Market Bazaar'),(4,0,'Government Hospital'),
    (0,2,'Gandhi Nagar'),(2,2,'Central Chowk'),(4,2,'IT Park'),
    (0,4,'University'),(2,4,'Railway Station'),(4,4,'Airport Road')]]


class CityCollector:
    """Subscribe once, then read one batched TraCI update for dense traffic."""
    variables=(tc.VAR_POSITION,tc.VAR_SPEED,tc.VAR_ACCELERATION,tc.VAR_ANGLE,
               tc.VAR_LANE_ID,tc.VAR_LANE_INDEX,tc.VAR_ROAD_ID,tc.VAR_LANEPOSITION_LAT,
               tc.VAR_LENGTH,tc.VAR_WIDTH,tc.VAR_NEXT_TLS)

    def __init__(self,path):
        self.subscribed=set()
        self.limits={lane.get('id'):float(lane.get('speed')) for edge in ET.parse(path).getroot().findall('edge') for lane in edge.findall('lane')}

    def collect(self,connection,now):
        ids=set(connection.vehicle.getIDList())
        self.subscribed.intersection_update(ids)
        for vehicle_id in sorted(ids-self.subscribed):
            connection.vehicle.subscribe(vehicle_id,self.variables)
            self.subscribed.add(vehicle_id)
        values=connection.vehicle.getAllSubscriptionResults();vehicles=[]
        for vehicle_id in sorted(ids):
            data=values[vehicle_id];x,y=data[tc.VAR_POSITION];lane=data[tc.VAR_LANE_ID];tls=data[tc.VAR_NEXT_TLS]
            vehicles.append(Vehicle(vehicle_id,now,x,y,lane,data[tc.VAR_LANE_INDEX],data[tc.VAR_SPEED],
                data[tc.VAR_ACCELERATION],data[tc.VAR_ANGLE],data[tc.VAR_ROAD_ID],
                tls[0][0] if tls else '',tls[0][3] if tls else '',self.limits.get(lane,13.9),
                length=data[tc.VAR_LENGTH],width=data[tc.VAR_WIDTH],lateral_position=data[tc.VAR_LANEPOSITION_LAT]))
        return vehicles


def build_city_network():
    folder=ROOT/'sumo/network/city'
    folder.mkdir(parents=True,exist_ok=True)
    path=folder/'indian_city.net.xml'
    if path.exists():return path
    nodes=ET.Element('nodes');edges=ET.Element('edges')
    for x in range(5):
        for y in range(5):
            ET.SubElement(nodes,'node',id=f'n{x}_{y}',x=str(x*180),y=str(y*180),
                          type='traffic_light' if 0<x<4 and 0<y<4 else 'priority')
            for dx,dy in [(1,0),(0,1)]:
                if x+dx>=5 or y+dy>=5:continue
                a,b=f'n{x}_{y}',f'n{x+dx}_{y+dy}'
                for start,end in [(a,b),(b,a)]:
                    ET.SubElement(edges,'edge',id=start+'__'+end,**{'from':start,'to':end},
                                  numLanes='2',speed='13.9',priority='2')
    for name,root in [('nodes.nod.xml',nodes),('edges.edg.xml',edges)]:
        ET.ElementTree(root).write(folder/name,encoding='utf-8',xml_declaration=True)
    subprocess.run([binary('netconvert'),'--node-files',str(folder/'nodes.nod.xml'),
                    '--edge-files',str(folder/'edges.edg.xml'),'--output-file',str(path),
                    '--offset.disable-normalization','true','--no-turnarounds','true',
                    '--tls.default-type','static','--lefthand','true'],check=True,capture_output=True,text=True)
    return path


def city_route(start,destination):
    known={p['id'] for p in CITY_POINTS}
    if start not in known or destination not in known or start==destination:
        raise ValueError('Choose different valid city start and destination points')
    root=ET.parse(build_city_network()).getroot()
    edges={e.get('id'):e for e in root.findall('edge') if not e.get('id').startswith(':')}
    graph=nx.DiGraph()
    for edge in edges:graph.add_node(edge)
    for link in root.findall('connection'):
        a,b=link.get('from'),link.get('to')
        if a in edges and b in edges:
            graph.add_edge(a,b,weight=float(edges[b].find('lane').get('length')))
    best=None
    for a,e in edges.items():
        if e.get('from')!=start:continue
        for b,d in edges.items():
            if d.get('to')!=destination:continue
            try:
                route=nx.shortest_path(graph,a,b,weight='weight')
            except nx.NetworkXNoPath:continue
            length=sum(float(edges[item].find('lane').get('length')) for item in route)
            if best is None or length<best[0]:best=(length,route)
    if best is None:raise ValueError('No route connects these city points')
    shape=[]
    for edge in best[1]:
        shape.extend([[float(n) for n in p.split(',')] for p in edges[edge].find('lane').get('shape').split()])
    distance=sum(math.dist(a,b) for a,b in zip(shape,shape[1:]))
    return {'start':next(p for p in CITY_POINTS if p['id']==start),
            'destination':next(p for p in CITY_POINTS if p['id']==destination),
            'edges':best[1],'distance':distance,'shape':shape}


def run_city(output,config,seed,duration,gui,control_file):
    from .simulation import summarize
    from .control import collision_risk
    from .communication import Channel
    output=Path(output);rng=random.Random(seed)
    trip=city_route(config.get('city_start','n0_0'),config.get('city_destination','n4_4'))
    target=int(config.get('city_vehicles',180))
    if not 20<=target<=600:raise ValueError('City traffic must be between 20 and 600 vehicles')
    types=ET.Element('routes')
    for name,speed,length,width,shape,vclass in [('city_car',13.9,4.7,1.8,'passenger','passenger'),('city_bus',11,11,2.5,'bus','bus'),('city_truck',10,8,2.4,'truck','truck'),('city_auto',10,2.8,1.35,'passenger','passenger'),('city_bike',12,2.2,.75,'motorcycle','motorcycle')]:
        ET.SubElement(types,'vType',id=name,accel='2.2',decel='4.5',sigma='0.35',
                      length=str(length),width=str(width),maxSpeed=str(speed),guiShape=shape,vClass=vclass,minGap='2.5',
                      laneChangeModel='SL2015',maxSpeedLat='0.9',lcAccelLat='0.45',
                      lcMaxSpeedLatStanding='0',lcMaxSpeedLatFactor='0.15',latAlignment='center')
    routes=output/'traffic.rou.xml'
    ET.ElementTree(types).write(routes,encoding='utf-8',xml_declaration=True)
    label='city_'+str(time.time_ns())
    traci.start([binary('sumo-gui' if gui else 'sumo'),'--net-file',str(build_city_network()),
                 '--route-files',str(routes),'--step-length',str(config['simulation_dt']),
                 '--seed',str(seed),'--collision.check-junctions','true','--time-to-teleport','-1',
                 '--lateral-resolution','0.8',
                 '--tripinfo-output',str(output/'tripinfo.xml'),'--tripinfo-output.write-unfinished','true',
                 '--start','--quit-on-end'],label=label)
    con=traci.getConnection(label)
    con.route.add('city_ego_route',trip['edges'])
    con.vehicle.add('ego','city_ego_route',typeID='city_car',departLane='best',departPos='10',departSpeed='5')
    edge_ids=[e for e in con.edge.getIDList() if not e.startswith(':')]
    manifest=read_json(output/'manifest.json');manifest.update(city_trip=trip,traffic_target=target,
        city_network=build_city_network().name,traffic_side='left',lane_change_model='SL2015',
        maximum_lateral_speed=.9,maximum_lateral_acceleration=.45,lateral_speed_at_standstill=0,
        routing_engine='SUMO shortest routes + independent junction and car-following controls',sumo_version=con.getVersion()[1])
    atomic_json(output/'manifest.json',manifest)
    history=[];traffic=[];plans=[];timeline=[];counter=0;arrived=False;cancelled=False;collisions=0;peak=0
    from .city_reachability import CityReachability
    reachability=CityReachability(build_city_network())
    collector=CityCollector(build_city_network())
    preview={};last_preview=-10
    realtime=config['realtime_factor'];last=None;slow_actor=None;slow_released=False;now=0
    trace=(output/'trace.jsonl').open('w',encoding='utf-8')
    try:
        while con.simulation.getTime()<duration:
            command=read_json(control_file) if control_file else {}
            realtime=float(command.get('realtime_factor',realtime))
            if command.get('action')=='stop':cancelled=True;break
            if command.get('action')=='pause':
                atomic_json(output/'status.json',{'state':'paused','time':con.simulation.getTime()});time.sleep(.1);continue
            begin=time.perf_counter()
            population=con.vehicle.getIDCount()+len(con.simulation.getPendingVehicles())
            for _ in range(min(35,max(0,target+1-population))):
                for attempt in range(10):
                    a,b=rng.sample(edge_ids,2)
                    route=con.simulation.findRoute(a,b,vType='city_car')
                    if route.edges:break
                else:continue
                rid=f'city_route_{counter}'
                kind=rng.choices(['city_car','city_bus','city_truck','city_auto','city_bike'],[.6,.08,.07,.15,.1])[0]
                vid=f'{kind}_{counter}';counter+=1
                con.route.add(rid,route.edges)
                length=con.lane.getLength(a+'_0')
                con.vehicle.add(vid,rid,typeID=kind,departLane='best',departPos=str(rng.uniform(12,max(13,length-60))),departSpeed=str(rng.uniform(2,7)))
                con.vehicle.setColor(vid,rng.choice([(70,137,177,255),(204,135,75,255),(110,161,118,255),(164,135,189,255)]))
            con.simulationStep();now=con.simulation.getTime()
            collisions+=sum('ego' in (c.collider,c.victim) for c in con.simulation.getCollisions())
            if 'ego' in con.simulation.getArrivedIDList():arrived=True;break
            vehicles=collector.collect(con,now);ego=next((v for v in vehicles if v.vehicle_id=='ego'),None)
            if not ego:continue
            peak=max(peak,len(vehicles))
            if now>=15 and slow_actor is None:
                candidates=[v for v in vehicles if v.vehicle_id!='ego' and v.speed>5]
                if candidates:
                    slow_actor=candidates[0].vehicle_id;con.vehicle.slowDown(slow_actor,2,5)
                    timeline.append({'time':now,'kind':'braking','message':slow_actor+' slows in city traffic'})
            if now>=25 and slow_actor and not slow_released:
                if slow_actor in con.vehicle.getIDList():con.vehicle.setSpeed(slow_actor,-1)
                slow_released=True
            clearance,ttc=collision_risk(ego,[v for v in vehicles if v.road_id==ego.road_id])
            local=[v for v in vehicles if math.hypot(v.x-ego.x,v.y-ego.y)<=config['sensor_range']]
            if now-last_preview>=.4-1e-7 or not preview:
                preview=reachability.forecast(con,ego,local,now)
                last_preview=now
            record={**ego.record(),'distance':con.vehicle.getDistance('ego'),'clearance':clearance,'knowledge_age':0,
                    'emergency':0,'rule_violation':0,'planned':1,'planning_seconds':0.,'query_seconds':0.,'rs_seconds':0.,'cycle_seconds':time.perf_counter()-begin}
            history.append(record);traffic.extend(v.record() for v in vehicles)
            last={'time':now,'plan_time':now,'ego':ego.record(),'vehicles':[v.record() for v in vehicles],
                  'city_reachability':preview,'ego_trace':[[r['x'],r['y']] for r in history[-100:]],
                  'city':{'trip':trip,'traffic_target':target,'active_vehicles':len(vehicles),'total_spawned':counter,
                          'routing_engine':'SUMO city routing','remaining':max(0,trip['distance']-record['distance'])},
                  'signals':[{'id':t,'state':con.trafficlight.getRedYellowGreenState(t)} for t in con.trafficlight.getIDList()],
                  'clearance':clearance,'ttc':ttc,'age':0,'local_vehicles':len(local),'remote_vehicles':0,
                  'commands':{'command_lane':ego.lane,'command_speed':ego.speed},'constraints':[],
                  'planning_ms':0,'query_ms':0,'triples':0,'raw':[],'adjusted':[],'chain':[],
                  'emergency':False,'packets':{'received':0,'lost':0},'timeline':timeline,
                  'sensing':{'range':config['sensor_range'],'local_ids':[v.vehicle_id for v in local],'remote_ids':[],
                             'observations':[{'id':v.vehicle_id,'lane':v.lane_id,'x':v.x,'y':v.y,'speed':v.speed,'timestamp':now,'source':'onboard'} for v in local]},
                  'history':[{k:r[k] for k in ('timestamp','speed','acceleration','clearance','knowledge_age')} for r in history[-300:]]}
            atomic_json(output/'live.json',last);atomic_json(output/'status.json',{'state':'running','time':now})
            trace.write(json.dumps(last,allow_nan=False)+'\n');trace.flush()
            if realtime>0:time.sleep(max(0,config['simulation_dt']/realtime-(time.perf_counter()-begin)))
    finally:
        trace.close();con.close()
    pd.DataFrame(history).to_csv(output/'ego.csv',index=False);pd.DataFrame(traffic).to_csv(output/'traffic.csv',index=False)
    atomic_json(output/'plans.json',plans)
    metrics=summarize(pd.DataFrame(history),collisions,arrived,Channel(0,0,seed),config) if history else {'arrived':0,'collision_events':collisions,'average_speed':0,'travel_time':0}
    metrics.update(end_reason='cancelled' if cancelled else 'arrived' if arrived else 'duration_limit',
                   final_time=now,peak_vehicles=peak,total_spawned=counter)
    metrics['rule_violations']=None  # The straight-road rule counter does not apply to city movements.
    atomic_json(output/'metrics.json',metrics)
    return metrics
