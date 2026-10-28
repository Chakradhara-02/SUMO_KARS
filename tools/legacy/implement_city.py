from pathlib import Path
p=Path('kars/city.py');s=p.read_text()
a=s.index('def build_city_network():');b=s.index('\n\ndef city_route',a)
s=s[:a]+'''CITY_NETWORK_VERSION = 'metro_v2'


def city_position(x, y):
    # Irregular blocks preserve familiar destination IDs without a square lattice.
    return (x*180 + (28 if y in (1,3) else 0) + (14 if x==3 else 0),
            y*180 + (22 if x in (1,3) else 0))

for _point in CITY_POINTS:
    _x,_y=map(int,_point['id'][1:].split('_'))
    _point['x'],_point['y']=city_position(_x,_y)


def build_city_network():
    folder=ROOT/'sumo/network/city'
    folder.mkdir(parents=True,exist_ok=True)
    path=folder/(CITY_NETWORK_VERSION+'.net.xml')
    if path.exists():return path
    nodes=ET.Element('nodes');edges=ET.Element('edges');positions={}
    def node(name,x,y,z=0,signal=False):
        positions[name]=(x,y,z)
        ET.SubElement(nodes,'node',id=name,x=str(x),y=str(y),z=str(z),
                      radius='18' if signal else '24',type='traffic_light' if signal else 'priority')
    def street(a,b,lanes=2,speed=13.9,priority=2,curved=False):
        for start,end in ((a,b),(b,a)):
            u,v=positions[start],positions[end]
            shape=[]
            for i in range(13):
                t=i/12;bow=math.sin(math.pi*t)*12 if curved else 0
                dx,dy=v[0]-u[0],v[1]-u[1];length=math.hypot(dx,dy)
                shape.append(f'{u[0]+dx*t-dy/max(1,length)*bow},{u[1]+dy*t+dx/max(1,length)*bow},{u[2]+(v[2]-u[2])*t}')
            ET.SubElement(edges,'edge',id=start+'__'+end,**{'from':start,'to':end},
                          numLanes=str(lanes),speed=str(speed),priority=str(priority),shape=' '.join(shape))
    for x in range(5):
        for y in range(5):
            px,py=city_position(x,y)
            node(f'n{x}_{y}',px,py,7 if (x,y)==(2,2) else 0,0<x<4 and 0<y<4)
    for x in range(5):
        for y in range(5):
            for dx,dy in ((1,0),(0,1)):
                if x+dx>=5 or y+dy>=5:continue
                if (x,y,dx,dy) in ((1,1,0,1),(3,2,0,1),(2,3,1,0)):continue
                street(f'n{x}_{y}',f'n{x+dx}_{y+dy}',curved=(x+y)%3==1)
    # Eight outer interchanges and curved three-lane expressways.
    ring=[(-190,-120),(360,-240),(920,-100),(1030,360),(920,900),(360,1020),(-200,900),(-300,360)]
    for i,(x,y) in enumerate(ring):node(f'r{i}',x,y)
    for i in range(8):street(f'r{i}',f'r{(i+1)%8}',3,25.,5,True)
    for i,local in enumerate(('n0_0','n2_0','n4_0','n4_2','n4_4','n2_4','n0_4','n0_2')):
        street(f'r{i}',local,2,19.4,4,True)
    # The through-road passes underneath the seven-metre central junction.
    node('under_w',180,360);node('under_e',540,360)
    street('n0_2','under_w',2,19.4,4)
    street('under_w','under_e',2,22.2,5)
    street('under_e','n4_2',2,19.4,4)
    for name,root in [('metro.nodes.xml',nodes),('metro.edges.xml',edges)]:
        ET.ElementTree(root).write(folder/name,encoding='utf-8',xml_declaration=True)
    command=[binary('netconvert'),'--node-files',str(folder/'metro.nodes.xml'),
             '--edge-files',str(folder/'metro.edges.xml'),'--output-file',str(path),
             '--offset.disable-normalization','true','--no-turnarounds','true',
             '--tls.default-type','static','--lefthand','true','--junctions.corner-detail','12',
             '--junctions.internal-link-detail','16','--junctions.limit-turn-speed','5.5']
    result=subprocess.run(command,capture_output=True,text=True)
    if result.returncode:raise RuntimeError(result.stderr)
    return path
''' +s[b:]
s=s.replace('from .models import ROOT, Vehicle','from .models import ROOT, Vehicle\nfrom .city_routing import CityRouter')
s=s.replace('maxSpeedLat=\'0.9\',lcAccelLat=\'0.45\'',"maxSpeedLat='0.65',lcAccelLat='0.3',lcStrategic='2',lcSpeedGain='0.25',lcKeepRight='0',minGapLat='0.6'")
s=s.replace("'--lateral-resolution','0.8',","'--lateral-resolution','0.2','--default.action-step-length','0.2',")
s=s.replace('maximum_lateral_speed=.9,maximum_lateral_acceleration=.45','maximum_lateral_speed=.65,maximum_lateral_acceleration=.3')
s=s.replace("preview={};last_preview=-10","preview={};last_preview=-10;last_route=-10;alternatives=[];route_events=[]\n    router=CityRouter(build_city_network())")
s=s.replace("            if now-last_preview>=.4-1e-7 or not preview:\n                preview=reachability.forecast(con,ego,local,now)\n                last_preview=now",'''            if now>=3 and now-last_route>=8 and not ego.road_id.startswith(':') and abs(ego.lateral_position)<.05:
                lane_remaining=con.lane.getLength(ego.lane_id)-con.vehicle.getLanePosition('ego')
                if lane_remaining>45:
                    alternatives=router.alternatives(ego.road_id,trip['destination']['id'],con)
                    current=list(con.vehicle.getRoute('ego'))[max(0,con.vehicle.getRouteIndex('ego')):]
                    def cost(route):
                        return sum(max(con.edge.getTraveltime(e),con.lane.getLength(e+'_0')/13.9)+con.edge.getLastStepHaltingNumber(e)*1.5+con.lane.getLength(e+'_0')/30 for e in route)
                    if alternatives and alternatives[0]['edges']!=current and alternatives[0]['score']+4<cost(current)*.88:
                        con.vehicle.setRoute('ego',alternatives[0]['edges'])
                        route_events.append({'time':now,'reason':'Lower measured traffic and distance cost','edges':alternatives[0]['edges']})
                    actual=list(con.vehicle.getRoute('ego'))[max(0,con.vehicle.getRouteIndex('ego')):]
                    for alternative in alternatives:alternative['selected']=alternative['edges']==actual
                    last_route=now
            if now-last_preview>=.8-1e-7 or not preview:
                preview=reachability.forecast(con,ego,local,now)
                branches=[]
                for i,alternative in enumerate(alternatives):
                    if not alternative['edges'] or alternative['edges'][0]!=ego.road_id:continue
                    branch=reachability.forecast(con,ego,local,now,route_override=alternative['edges'])
                    branches.append({'id':i,**alternative,'feasible_count':branch['feasible_count'],
                                     'trajectory':branch['trajectory'],'feasible':branch['feasible'][::3]})
                preview['route_branches']=branches
                last_preview=now''')
s=s.replace("'routing_engine':'SUMO city routing','remaining'","'routing_engine':'Traffic-aware alternative routes', 'alternatives':alternatives,'route_events':route_events,'remaining'")
p.write_text(s)
# Preserve measured elevation in every actor record.
p=Path('kars/models.py');s=p.read_text().replace('    lateral_position: float = 0.0','    lateral_position: float = 0.0\n    z: float = 0.0');p.write_text(s)
p=Path('kars/city.py');s=p.read_text().replace('tc.VAR_LENGTH,tc.VAR_WIDTH,tc.VAR_NEXT_TLS)','tc.VAR_LENGTH,tc.VAR_WIDTH,tc.VAR_NEXT_TLS,tc.VAR_POSITION3D)');s=s.replace('lateral_position=data[tc.VAR_LANEPOSITION_LAT]))','lateral_position=data[tc.VAR_LANEPOSITION_LAT],z=data[tc.VAR_POSITION3D][2]))');p.write_text(s)
p=Path('kars/city_reachability.py');s=p.read_text().replace('def forecast(self,connection,ego,vehicles,now):','def forecast(self,connection,ego,vehicles,now,route_override=None):').replace("        remaining=list(route[index:index+4])","        remaining=list(route[index:index+4])\n        if route_override is not None:remaining=list(route_override[:5])")
s=s.replace("                                if v.vehicle_id=='ego':continue","                                if v.vehicle_id=='ego' or abs(v.z-ego.z)>3:continue")
p.write_text(s)
