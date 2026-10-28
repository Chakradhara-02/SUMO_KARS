from pathlib import Path
p=Path('kars/city.py');s=p.read_text();s=s.replace("CITY_NETWORK_VERSION = 'metro_v3'", "CITY_NETWORK_VERSION = 'metro_straight_v4'")
a=s.index('def city_position');b=s.index('\nfor _point',a)
s=s[:a]+'''CITY_COLUMNS=(0,160,360,600,850)
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
''' +s[b:]
a=s.index('    def street(');b=s.index('    for x in range(5):',a)
s=s[:a]+'''    def street(a,b,lanes=2,speed=13.9,priority=2,curved=False):
        # External roads are exact straight segments. SUMO supplies smooth junction turns.
        for start,end in ((a,b),(b,a)):
            shape=' '.join(','.join(map(str,positions[n])) for n in (start,end))
            attrs={'from':start,'to':end,'numLanes':str(lanes),'speed':str(speed),
                   'priority':str(priority),'shape':shape,'name':
                   'Outer Expressway' if lanes==3 else 'Central Flyover' if positions[start][2]>0 or positions[end][2]>0 else 'City Avenue'}
            if not (start.startswith('r') or end.startswith('r')):attrs['disallow']='truck'
            ET.SubElement(edges,'edge',id=start+'__'+end,**attrs)
''' +s[b:]
s=s.replace("7 if (x,y)==(2,2) else 0", "7 if y==2 and 1<=x<=3 else 0")
s=s.replace('ring=[(-190,-120),(360,-240),(920,-100),(1030,360),(920,900),(360,1020),(-200,900),(-300,360)]','ring=[(-240,-240),(360,-240),(1100,-240),(1100,400),(1100,1100),(360,1100),(-240,1100),(-240,400)]')
s=s.replace("node('under_w',180,360);node('under_e',540,360)", "node('under_w',200,400);node('under_e',620,400)")
s=s.replace("'--route-files',str(routes),'--step-length',str(config['simulation_dt'])", "'--route-files',str(routes),'--step-length',str(min(.1,config['simulation_dt']))")
s=s.replace("                for attempt in range(10):\n                    a,b=rng.sample(edge_ids,2)\n                    route=con.simulation.findRoute(a,b,vType='city_car')", "                kind=rng.choices(['city_car','city_bus','city_truck','city_auto','city_bike'],[.65,.08,.05,.14,.08])[0]\n                pool=[e for e in edge_ids if e.startswith('r') and '__r' in e] if kind=='city_truck' else edge_ids\n                for attempt in range(10):\n                    a,b=rng.sample(pool,2)\n                    route=con.simulation.findRoute(a,b,vType=kind)")
s=s.replace("                kind=rng.choices(['city_car','city_bus','city_truck','city_auto','city_bike'],[.6,.08,.07,.15,.1])[0]\n",'')
s=s.replace("config['simulation_dt']/realtime", "min(.1,config['simulation_dt'])/realtime")
s=s.replace("    preview={};last_preview=-10;last_route=-10;alternatives=[];route_events=[]", "    preview={};last_preview=-10;last_route=-10;alternatives=[];route_events=[];last_publish=-10")
s=s.replace("            atomic_json(output/'live.json',last);atomic_json(output/'status.json',{'state':'running','time':now})", "            if now-last_publish>=.2-1e-8:\n                atomic_json(output/'live.json',last);atomic_json(output/'status.json',{'state':'running','time':now});last_publish=now")
p.write_text(s)
p=Path('kars/simulation.py');s=p.read_text().replace("city_network='metro_v3.net.xml'","city_network='metro_straight_v4.net.xml'");p.write_text(s)
p=Path('kars/console.py');s=p.read_text().replace("from .city import build_city_network, CITY_POINTS", "from .city import build_city_network, CITY_POINTS, CITY_DISTRICTS")
s=s.replace("'metro_v3.net.xml':'metro_v3.net.xml'", "'metro_v3.net.xml':'metro_v3.net.xml','metro_straight_v4.net.xml':'metro_straight_v4.net.xml'")
s=s.replace("if version=='metro_v3.net.xml' and not city_path.exists()", "if version=='metro_straight_v4.net.xml' and not city_path.exists()")
s=s.replace("'city':scenario=='city','points':CITY_POINTS if scenario=='city' else [],", "'city':scenario=='city','points':CITY_POINTS if scenario=='city' else [],\n            'districts':CITY_DISTRICTS if scenario=='city' else [],\n            'bounds':{'min_x':-300,'max_x':1160,'min_y':-300,'max_y':1160} if scenario=='city' else None,")
p.write_text(s)
