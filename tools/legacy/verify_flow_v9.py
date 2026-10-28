import json,math
from pathlib import Path
import xml.etree.ElementTree as ET
from kars.city import CITY_POINTS,build_city_network,city_route
from kars.simulation import run_simulation
from kars.parking import footprint,overlaps

root=Path(__file__).parent;out=root/'outputs';net=ET.parse(build_city_network()).getroot()
access=[j for j in net.findall('junction') if j.get('id').startswith('access_')]
assert len(access)==10 and all(j.get('type')=='priority' for j in access)
assert len(net.findall('tlLogic'))==25
pairs=0
for a in CITY_POINTS:
 for b in CITY_POINTS:
  if a==b:continue
  assert city_route(a['id'],b['id'])['arrival_bay']['z']==0;pairs+=1
reports=[]
for name,start,end,traffic,slot in [('v9_mall350','n2_0','city_mall',350,'A8'),('v9_chowk_hospital','n2_2','n4_0',60,'A3')]:
 folder=out/name
 metrics=run_simulation('city','city',duration=1800,output=folder,make_plots=False,config_overrides={'city_vehicles':traffic,'city_start':start,'city_destination':end,'city_parking_slot':slot})
 assert metrics['parked_at_destination'] and metrics['collision_events']==0,metrics
 frames=[json.loads(l) for l in (folder/'trace.jsonl').open()]
 parking=[f for f in frames if f['city']['parking']['active']]
 bad=0
 for f in parking:
  lot=f['city']['trip']['parking_lot'];corners=footprint(f['ego'])
  assert all(lot['bounds'][0]<x<lot['bounds'][2] and lot['bounds'][1]<y<lot['bounds'][3] for x,y in corners)
  for s in lot['slots']:
   if s['occupied'] and overlaps(corners,footprint({'x':s['front_x'],'y':s['front_y'],'heading':180},width=1.8)):bad+=1
 assert bad==0
 assert all(f['city'].get('route_shape') for f in frames if not f['city']['parking']['active'])
 reports.append({'name':name,'metrics':metrics,'occupied_bay_overlaps':bad,'guidance_maintained':True,'route_switches':frames[-1]['city']['route_events']})
 print(name,'parked',metrics['final_time'],'route switches',len(reports[-1]['route_switches']),flush=True)
(out/'v9_native_validation.json').write_text(json.dumps({'pairs_connected':pairs,'priority_driveways':len(access),'signalized_junctions':25,'runs':reports},indent=2))
