"""City routing and measured traffic on a irregular road network with grade-separated routes."""
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
from .city_routing import CityRouter
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
               tc.VAR_LENGTH,tc.VAR_WIDTH,tc.VAR_NEXT_TLS,tc.VAR_POSITION3D,tc.VAR_SIGNALS)

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
                length=data[tc.VAR_LENGTH],width=data[tc.VAR_WIDTH],lateral_position=data[tc.VAR_LANEPOSITION_LAT],z=data[tc.VAR_POSITION3D][2],signals=data.get(tc.VAR_SIGNALS,0)))
        return vehicles


CITY_NETWORK_VERSION = 'metro_flow_v9'


CITY_COLUMNS=(0,160,360,600,850)
CITY_ROWS=(0,180,400,640,850)
CITY_DISTRICTS=[
    {'name':'CIVIC CENTRE','x':260,'y':285,'color':'#e6dbcc'},
    {'name':'UNIVERSITY QUARTER','x':80,'y':745,'color':'#d0dfd0'},
    {'name':'TECH DISTRICT','x':725,'y':510,'color':'#d4e0e7'},
    {'name':'MARKET & TRANSIT','x':270,'y':85,'color':'#e5d9ca'},
    {'name':'RESIDENTIAL','x':725,'y':735,'color':'#e1ded5'},
]

def city_position(x,y):
    return CITY_COLUMNS[x],CITY_ROWS[y]

for _point in CITY_POINTS:
    _x,_y=map(int,_point['id'][1:].split('_'))
    _point['x'],_point['y']=city_position(_x,_y)
    _point['z']=7 if _y==2 and 1<=_x<=3 else 0


CITY_POINTS.append({'id':'city_mall','name':'City Mall','x':645,'y':261,'z':0})


def build_city_network():
    folder=ROOT/'sumo/network/city'
    folder.mkdir(parents=True,exist_ok=True)
    path=folder/(CITY_NETWORK_VERSION+'.net.xml')
    if path.exists():return path
    nodes=ET.Element('nodes');edges=ET.Element('edges');positions={}
    def node(name,x,y,z=0,signal=False,radius=None):
        positions[name]=(x,y,z)
        ET.SubElement(nodes,'node',id=name,x=str(x),y=str(y),z=str(z),
                      radius=str(radius) if radius is not None else '18' if signal else '24',type='traffic_light' if signal else 'priority')
    def street(a,b,lanes=2,speed=13.9,priority=2,curved=False):
        # External roads are exact straight segments. SUMO supplies smooth junction turns.
        for start,end in ((a,b),(b,a)):
            shape=' '.join(','.join(map(str,positions[n])) for n in (start,end))
            attrs={'from':start,'to':end,'numLanes':str(lanes),'speed':str(speed),
                   'priority':str(priority),'shape':shape,'name':
                   'Outer Expressway' if lanes==3 else 'Central Flyover' if positions[start][2]>0 or positions[end][2]>0 else 'City Avenue'}
            if not (start.startswith('r') or end.startswith('r')):attrs['disallow']='truck'
            ET.SubElement(edges,'edge',id=start+'__'+end,**attrs)
    for x in range(5):
        for y in range(5):
            px,py=city_position(x,y)
            node(f'n{x}_{y}',px,py,7 if y==2 and 1<=x<=3 else 0,True)
    for x in range(5):
        for y in range(5):
            for dx,dy in ((1,0),(0,1)):
                if x+dx>=5 or y+dy>=5:continue
                if (x,y,dx,dy) in ((1,1,0,1),(3,2,0,1),(2,3,1,0)):continue
                street(f'n{x}_{y}',f'n{x+dx}_{y+dy}',curved=False)
    # Eight outer interchanges and straight three-lane expressways.
    ring=[(-240,-240),(360,-240),(1100,-240),(1100,400),(1100,1100),(360,1100),(-240,1100),(-240,400)]
    for i,(x,y) in enumerate(ring):node(f'r{i}',x,y)
    for i in range(8):street(f'r{i}',f'r{(i+1)%8}',3,25.,5,True)
    for i,local in enumerate(('n0_0','n2_0','n4_0','n4_2','n4_4','n2_4','n0_4','n0_2')):
        street(f'r{i}',local,2,19.4,4,True)
    # The through-road passes underneath the seven-metre central junction.
    node('under_w',200,400);node('under_e',620,400)
    # Ground approaches leave the flyover alignment before the ramps descend.
    # Distinct roads must not share the same space outside a modelled junction.
    node('under_entry_w',90,340);node('under_entry_e',760,340)
    street('n0_2','under_entry_w',2,13.9,4)
    street('under_entry_w','under_w',2,13.9,4)
    street('under_w','under_e',2,22.2,5)
    street('under_e','under_entry_e',2,13.9,4)
    street('under_entry_e','n4_2',2,13.9,4)
    from .parking import parking_lot
    # Driveways join the nearest ground street between signalized junctions.
    # Split both directions at one priority T-junction; no parking traffic lights.
    def driveway(lot):
        target=(lot['x'],lot['y']+22);choices=[]
        for edge in list(edges):
            a,b=edge.get('from'),edge.get('to')
            if not (a.startswith('n') and b.startswith('n')):continue
            pa,pb=positions[a],positions[b]
            if pa[2] or pb[2]:continue
            dx,dy=pb[0]-pa[0],pb[1]-pa[1];length=math.hypot(dx,dy)
            t=max(25/length,min(1-25/length,((target[0]-pa[0])*dx+(target[1]-pa[1])*dy)/(length*length)))
            px,py=pa[0]+dx*t,pa[1]+dy*t
            choices.append((math.hypot(px-target[0],py-target[1]),a,b,px,py))
        _,a,b,px,py=min(choices);tap='access_'+lot['id'];node(tap,px,py,0,False,9)
        for edge in list(edges):
            start,end=edge.get('from'),edge.get('to')
            if {start,end}!={a,b}:continue
            attrs=dict(edge.attrib);edge.set('to',tap)
            edge.set('shape',' '.join(','.join(map(str,positions[n])) for n in (start,tap)))
            attrs.update(id=tap+'__'+end,**{'from':tap,'to':end},shape=' '.join(','.join(map(str,positions[n])) for n in (tap,end)))
            ET.SubElement(edges,'edge',**attrs)
        return tap
    for place in CITY_POINTS:
        lot=parking_lot(place);x,y=lot['x'],lot['y'];prefix='park_'+place['id']
        access=driveway(lot)
        nodes_for=[(prefix+'_gate',x,y+8),(prefix+'_aisle',x+14,y+8),('arrival_'+place['id'],x+60,y+8),
                   (prefix+'_turn',x+66,y+36),('city_mall' if place['id']=='city_mall' else prefix+'_exit',x,y+36)]
        for nid,px,py in nodes_for:node(nid,px,py,0,False,3)
        chain=[access]+[n[0] for n in nodes_for]+[access]
        for i,(a,b) in enumerate(zip(chain,chain[1:])):
            width=8 if a==prefix+'_aisle' else 4
            shape=' '.join(','.join(map(str,positions[n])) for n in (a,b))
            ET.SubElement(edges,'edge',id=a+'__'+b,**{'from':a,'to':b},numLanes='1',width=str(width),
              speed='2.78' if i in (1,2,3) else '5.56',priority='1',disallow='truck bus',
              name=place['name']+' parking access',shape=shape)
    for name,root in [('metro.nodes.xml',nodes),('metro.edges.xml',edges)]:
        ET.ElementTree(root).write(folder/name,encoding='utf-8',xml_declaration=True)
    command=[binary('netconvert'),'--node-files',str(folder/'metro.nodes.xml'),
             '--edge-files',str(folder/'metro.edges.xml'),'--output-file',str(path),
             '--offset.disable-normalization','true','--no-turnarounds','true',
             '--tls.default-type','static','--lefthand','true','--junctions.corner-detail','12',
             '--junctions.internal-link-detail','32','--junctions.limit-turn-speed','4.0']
    result=subprocess.run(command,capture_output=True,text=True)
    if result.returncode:raise RuntimeError(result.stderr)
    tree=ET.parse(path)
    from .city_infrastructure import protected_signal_programs
    protected_signal_programs(tree.getroot())
    tree.write(path,encoding='utf-8',xml_declaration=True)
    return path


def city_route(start,destination,parking_slot=None):
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
            if d.get('to')!='arrival_'+destination:continue
            try:
                route=nx.shortest_path(graph,a,b,weight='weight')
            except nx.NetworkXNoPath:continue
            length=sum(float(edges[item].find('lane').get('length')) for item in route)
            if best is None or length<best[0]:best=(length,route)
    if best is None:raise ValueError('No route connects these city points')
    shape=[]
    for edge in best[1]:
        shape.extend([[float(n) for n in p.split(',')] for p in edges[edge].find('lane').get('shape').split()])
    from .parking import parking_lot,choose_slot,slot_bay
    lot=parking_lot(next(p for p in CITY_POINTS if p['id']==destination))
    selected=parking_slot or next(s['id'] for s in lot['slots'] if not s['occupied'])
    bay=slot_bay(lot,choose_slot(lot,selected))
    distance=sum(math.hypot(a[0]-b[0],a[1]-b[1]) for a,b in zip(shape,shape[1:]))
    return {'start':next(p for p in CITY_POINTS if p['id']==start),
            'destination':{**next(p for p in CITY_POINTS if p['id']==destination),'x':bay['x'],'y':bay['y'],'z':bay['z']},
            'edges':best[1],'distance':distance,'shape':shape,'arrival_bay':bay,'parking_lot':lot}


def run_city(output,config,seed,duration,gui,control_file):
    from .simulation import summarize
    from .city_safety import city_collision_risk
    from .communication import Channel
    from .city_infrastructure import EgoSignalPriority,SignalClock,indicator_intent,road_lateral_speed,city_motion_context
    from .parking import ParkingController,choose_slot,slot_bay
    config={**config,'simulation_dt':min(.1,config['simulation_dt'])}
    output=Path(output);rng=random.Random(seed)
    trip=city_route(config.get('city_start','n0_0'),config.get('city_destination','n4_4'),config.get('city_parking_slot'))
    target=int(config.get('city_vehicles',180))
    if not 20<=target<=600:raise ValueError('City traffic must be between 20 and 600 vehicles')
    types=ET.Element('routes')
    for name,speed,length,width,shape,vclass in [('city_car',22.2,4.7,1.8,'passenger','passenger'),('city_bus',18,11,2.5,'bus','bus'),('city_truck',16,8,2.4,'truck','truck'),('city_auto',10,2.8,1.35,'passenger','passenger'),('city_bike',18,2.2,.75,'motorcycle','motorcycle')]:
        ET.SubElement(types,'vType',id=name,accel='2.2',decel='4.5',sigma='0.35',
                      length=str(length),width=str(width),maxSpeed=str(speed),guiShape=shape,vClass=vclass,minGap='2.5',
                      laneChangeModel='SL2015',maxSpeedLat='0.65',lcAccelLat='0.3',lcStrategic='2',lcSpeedGain='0.25',lcKeepRight='0',minGapLat='0.6',
                      lcMaxSpeedLatStanding='0',lcMaxSpeedLatFactor='0.15',latAlignment='center')
    ego_type=dict(types.find("vType[@id='city_car']").attrib)
    ego_type.update(id='city_ego',width='2.05',sigma='0',accel='1.6',decel='3.5',emergencyDecel='5.5',tau='1.2')
    ET.SubElement(types,'vType',**ego_type)
    routes=output/'traffic.rou.xml'
    ET.ElementTree(types).write(routes,encoding='utf-8',xml_declaration=True)
    bay=trip['arrival_bay'];lot=trip['parking_lot']
    initial_slot=config.get('city_parking_slot') or (None if lot['id']=='city_mall' else bay['slot_id'])
    parking=ParkingController(lot,initial_slot)
    label='city_'+str(time.time_ns())
    traci.start([binary('sumo-gui' if gui else 'sumo'),'--net-file',str(build_city_network()),
                 '--route-files',str(routes),
                 '--stop-output',str(output/'stops.xml'),'--step-length',str(min(.1,config['simulation_dt'])),
                 '--seed',str(seed),'--collision.check-junctions','true','--time-to-teleport','-1',
                 '--lateral-resolution','0.2','--default.action-step-length','0.2',
                 '--tripinfo-output',str(output/'tripinfo.xml'),'--tripinfo-output.write-unfinished','true',
                 '--start','--quit-on-end'],label=label)
    con=traci.getConnection(label)
    con.route.add('city_ego_route',trip['edges'])
    con.vehicle.add('ego','city_ego_route',typeID='city_ego',departLane='best',departPos='10',departSpeed='5')
    con.vehicle.setStop('ego',lot['edge'],pos=3.,duration=100000.0)
    clock=SignalClock(con);signal_priority=EgoSignalPriority();signal_frames=[];parked_since=None
    edge_ids=[e for e in con.edge.getIDList() if not e.startswith(':') and 'arrival_' not in e and 'park_' not in e and 'city_mall' not in e]
    manifest=read_json(output/'manifest.json');manifest.update(city_trip=trip,traffic_target=target,config=config,
        city_network=build_city_network().name,traffic_side='left',lane_change_model='SL2015',
        maximum_lateral_speed=.65,maximum_lateral_acceleration=.3,lateral_speed_at_standstill=0,
        routing_engine='Measured traffic + distance alternative routing; SUMO junction and following controls',sumo_version=con.getVersion()[1])
    atomic_json(output/'manifest.json',manifest)
    history=[];traffic=[];plans=[];timeline=[];counter=0;arrived=False;cancelled=False;collisions=0;peak=0
    from .city_reachability import CityReachability
    reachability=CityReachability(build_city_network())
    collector=CityCollector(build_city_network())
    preview={};last_preview=-10;last_route=-10;alternatives=[];route_events=[];last_publish=-10
    router=CityRouter(build_city_network())
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
            requested=command.get('parking_slot')
            if requested and requested!=parking.slot_id and (not parking.active or parking.stage=='waiting_selection'):
                parking.select(requested);bay=slot_bay(lot,choose_slot(lot,requested));trip['arrival_bay']=bay;trip['destination'].update(x=bay['x'],y=bay['y'],z=0.)
            if parking.active:
                pose=parking.step(config['simulation_dt']);con.vehicle.setSpeed('ego',0)
                con.vehicle.moveToXY('ego',lot['edge'],0,pose['x'],pose['y'],angle=pose['heading'],keepRoute=2,matchThreshold=150.)
            population=con.vehicle.getIDCount()+len(con.simulation.getPendingVehicles())
            for _ in range(min(35,max(0,target+1-population))):
                kind=rng.choices(['city_car','city_bus','city_truck','city_auto','city_bike'],[.65,.08,.05,.14,.08])[0]
                pool=[e for e in edge_ids if e.startswith('r') and '__r' in e] if kind=='city_truck' else edge_ids
                for attempt in range(10):
                    a,b=rng.sample(pool,2)
                    route=con.simulation.findRoute(a,b,vType=kind)
                    if route.edges:break
                else:continue
                rid=f'city_route_{counter}'
                vid=f'{kind}_{counter}';counter+=1
                con.route.add(rid,route.edges)
                length=con.lane.getLength(a+'_0')
                con.vehicle.add(vid,rid,typeID=kind,departLane='best',departPos=str(rng.uniform(min(12,length*.15),max(min(13,length*.25),length-60))),departSpeed=str(rng.uniform(2,7)))
                con.vehicle.setColor(vid,rng.choice([(70,137,177,255),(204,135,75,255),(110,161,118,255),(164,135,189,255)]))
            clock.programs.update(signal_priority.update(con,con.simulation.getTime()))
            con.simulationStep();now=con.simulation.getTime()
            collisions+=sum('ego' in (c.collider,c.victim) for c in con.simulation.getCollisions())
            if 'ego' in con.simulation.getArrivedIDList():raise RuntimeError('Ego left the route before reaching its curbside parking bay')
            vehicles=collector.collect(con,now);ego=next((v for v in vehicles if v.vehicle_id=='ego'),None)
            if not ego:continue
            # Apply requests at the newly measured position before publishing countdowns.
            priority_changes=signal_priority.update(con,now)
            if priority_changes:
                clock.programs.update(priority_changes);signal_frames=clock.sample(con,now)
            if not parking.active and ego.road_id==lot['edge'] and con.vehicle.isStopped('ego'):
                parking.start({'x':ego.x,'y':ego.y,'heading':ego.heading,'z':0.});con.vehicle.resume('ego');con.vehicle.setSpeed('ego',0)
            if parking.active:
                ego.speed=(parking.pose or {}).get('speed',0.) if not parking.done else 0.
                ego.acceleration=(ego.speed-last['ego']['speed'])/config['simulation_dt'] if last else 0.
            parked=parking.done
            if parked and parked_since is None:parked_since=now
            arrived=parked_since is not None
            peak=max(peak,len(vehicles))
            if now>=15 and slow_actor is None:
                candidates=[v for v in vehicles if v.vehicle_id!='ego' and v.speed>5]
                if candidates:
                    slow_actor=candidates[0].vehicle_id;con.vehicle.slowDown(slow_actor,2,5)
                    timeline.append({'time':now,'kind':'braking','message':slow_actor+' slows in city traffic'})
            if now>=25 and slow_actor and not slow_released:
                if slow_actor in con.vehicle.getIDList():con.vehicle.setSpeed(slow_actor,-1)
                slow_released=True
            clearance,ttc=city_collision_risk(ego,[v for v in vehicles if v.road_id==ego.road_id])
            local=[v for v in vehicles if math.hypot(v.x-ego.x,v.y-ego.y)<=config['sensor_range']]
            if not parking.active and not arrived and now>=3 and now-last_route>=8 and not ego.road_id.startswith(':') and abs(ego.lateral_position)<.05:
                lane_remaining=con.lane.getLength(ego.lane_id)-con.vehicle.getLanePosition('ego')
                if lane_remaining>45:
                    alternatives=router.alternatives(ego.road_id,trip['destination']['id'],con)
                    for candidate in alternatives:
                        forecast=reachability.forecast(con,ego,local,now,sensor_range=config['sensor_range'],route_override=candidate['edges'])
                        candidate['feasible_count']=forecast['feasible_count']
                        candidate['reachable']=any(n['layer']>=3 for n in forecast['feasible'])
                    eligible=[r for r in alternatives if r['reachable']]
                    best_route=eligible[0] if eligible else None
                    current=list(con.vehicle.getRoute('ego'))[max(0,con.vehicle.getRouteIndex('ego')):]
                    if best_route and best_route['edges']!=current and best_route['score']+4<router.score(current)*.88:
                        con.vehicle.setRoute('ego',best_route['edges'])
                        route_events.append({'time':now,'reason':'Lower traffic, junction delay and distance cost','edges':best_route['edges']})
                    actual=list(con.vehicle.getRoute('ego'))[max(0,con.vehicle.getRouteIndex('ego')):]
                    for alternative in alternatives:alternative['selected']=alternative['edges']==actual
                    last_route=now
            if now-last_preview>=(.4 if target>300 else .3)-1e-7 or not preview or preview.get('lane_id')!=ego.lane_id:
                preview=reachability.forecast(con,ego,local,now,sensor_range=config['sensor_range']) if not parking.active else {}
                branches=[]
                for i,alternative in enumerate([] if parking.active else alternatives):
                    if not alternative['edges'] or alternative['edges'][0]!=ego.road_id:continue
                    branch=preview if alternative.get('selected') else reachability.forecast(con,ego,local,now,sensor_range=config['sensor_range'],route_override=alternative['edges'])
                    branches.append({'id':i,**alternative,'feasible_count':branch['feasible_count'],
                                     'trajectory':branch['trajectory'],'feasible':branch['feasible'][::3]})
                preview['route_branches']=branches
                preview['lane_id']=ego.lane_id
                if parking.active:
                    samples=[{'x':ego.x,'y':ego.y,'z':ego.z,'speed':0.,'layer':i,'time':now+i,'valid':True} for i in range(1,6)]
                    preview.update(raw=samples,feasible=samples,raw_count=5,feasible_count=5,trajectory=[],reference_path=[],status='parked' if parked else 'parking')
                last_preview=now
            actual_route=list(con.vehicle.getRoute('ego'))[max(0,con.vehicle.getRouteIndex('ego')):]
            navigation=router.journey(actual_route,con.vehicle.getLanePosition('ego') if not ego.road_id.startswith(':') else 0)
            navigation['route_shape']=router.guidance(actual_route,ego) if not parking.active else []
            if ego.road_id.startswith(':'):navigation['instruction']='Completing junction manoeuvre'
            direction=router.directions.get(tuple(actual_route[:2]),'s')
            if ego.road_id.startswith(':'):
                direction=last.get('city',{}).get('maneuver_direction','s') if last else 's'
                navigation['junction_distance']=0.
            lateral_speed=road_lateral_speed(last['ego'] if last else None,ego,reachability.lanes.get(ego.lane_id,{}).get('shape',[]))
            park_approach=parking.active
            ego.signals,ego.indicator_reason=indicator_intent(ego.signals,direction,navigation['junction_distance'],
                lateral_speed,park_approach,parked)
            if parking.active and not parked:ego.indicator_reason={'waiting_selection':'Choose an empty parking bay','positioning':'Positioning for reverse parking','reversing':'Reversing into selected bay','aligning':'Aligning inside the bay'}.get(parking.stage,'Automatic parking')
            if now-last_publish>=.2-1e-8:signal_frames=clock.sample(con,now)
            upcoming=con.vehicle.getNextTLS('ego')
            next_signal=None
            if upcoming:
                tid,link,distance,color=upcoming[0]
                snapshot=next((item for item in signal_frames if item['id']==tid),{})
                counts=snapshot.get('countdowns',[])
                next_signal={'id':tid,'distance':distance,'color':color,'seconds':counts[link] if link<len(counts) else None}
            motion_context=city_motion_context(ego,parked,next_signal,con.vehicle.getLeader('ego',80),
                con.vehicle.getNextLinks('ego') if ego.speed<.3 else ())
            if parking.active:
                motion_context={'state':parking.stage,'message':('Vehicle secured in the selected bay' if parked else ego.indicator_reason)}
                left=sum(math.hypot(b['x']-a['x'],b['y']-a['y']) for a,b in zip(parking.path[parking.index:],parking.path[parking.index+1:]))
                navigation.update(remaining=left,eta=left/.85+parking.pause,instruction=ego.indicator_reason)
            if parking.active:navigation.update(instruction=ego.indicator_reason)
            if parked:navigation.update(remaining=0.,eta=0.,instruction='Parked in selected destination bay',junction_distance=0.)
            distance=con.vehicle.getDistance('ego') if not parking.active or not history else history[-1]['distance']+math.hypot(ego.x-history[-1]['x'],ego.y-history[-1]['y'])
            record={**ego.record(),'distance':distance,'clearance':clearance,'knowledge_age':0,
                    'emergency':0,'rule_violation':0,'planned':1,'planning_seconds':0.,'query_seconds':0.,'rs_seconds':0.,'cycle_seconds':time.perf_counter()-begin}
            history.append(record)
            if now-last_publish>=.2-1e-8:traffic.extend(v.record() for v in vehicles)
            records=[{**v.record(),**({'model':'roadster','wheelbase':2.874531,'rear_axle_offset':3.909701} if v.vehicle_id=='ego' else {})} for v in vehicles]
            last={'time':now,'plan_time':last_preview,'ego':next(r for r in records if r['vehicle_id']=='ego'),'vehicles':records,
                  'city_reachability':preview,'ego_trace':[[r['x'],r['y'],r['z']] for r in history[-100:]],
                  'city':{'trip':trip,'traffic_target':target,'active_vehicles':len(vehicles),'total_spawned':counter,
                          'routing_engine':'Traffic-aware alternative routes', 'alternatives':alternatives,'route_events':route_events,'arrival_bay':bay,'parked':parked,'arrived':arrived,'next_signal':next_signal,'maneuver_direction':direction,'motion_context':motion_context,'parking':parking.snapshot(),**navigation},
                  'signals':signal_frames,
                  'clearance':clearance,'ttc':ttc,'age':0,'local_vehicles':len(local),'remote_vehicles':0,
                  'commands':{'command_lane':ego.lane,'command_speed':ego.speed},'constraints':[],
                  'planning_ms':0,'query_ms':0,'triples':0,'raw':[],'adjusted':[],'chain':[],
                  'emergency':False,'packets':{'received':0,'lost':0},'timeline':timeline,
                  'sensing':{'range':config['sensor_range'],'local_ids':[v.vehicle_id for v in local],'remote_ids':[],
                             'observations':[{'id':v.vehicle_id,'lane':v.lane_id,'x':v.x,'y':v.y,'speed':v.speed,'timestamp':now,'source':'onboard'} for v in local]},
                  'history':[{k:r[k] for k in ('timestamp','speed','acceleration','clearance','knowledge_age')} for r in history[-300:]]}
            if now-last_publish>=.2-1e-8:
                atomic_json(output/'live.json',last);atomic_json(output/'status.json',{'state':'running','time':now});last_publish=now
                trace.write(json.dumps(last,allow_nan=False)+'\n');trace.flush()
            if parked_since is not None and now-parked_since>=8:break
            if realtime>0:time.sleep(max(0,min(.1,config['simulation_dt'])/realtime-(time.perf_counter()-begin)))
    finally:
        trace.close();con.close()
    pd.DataFrame(history).to_csv(output/'ego.csv',index=False);pd.DataFrame(traffic).to_csv(output/'traffic.csv',index=False)
    atomic_json(output/'plans.json',plans)
    metrics=summarize(pd.DataFrame(history),collisions,arrived,Channel(0,0,seed),config) if history else {'arrived':0,'collision_events':collisions,'average_speed':0,'travel_time':0}
    metrics.update(end_reason='cancelled' if cancelled else 'arrived' if arrived else 'duration_limit',
                   final_time=now,peak_vehicles=peak,total_spawned=counter,parked_at_destination=arrived,arrival_bay=bay,parking_slot=parking.slot_id,parking_model='bounded private-lot kinematic forward/reverse controller')
    metrics['rule_violations']=None  # The straight-road rule counter does not apply to city movements.
    atomic_json(output/'metrics.json',metrics)
    return metrics
