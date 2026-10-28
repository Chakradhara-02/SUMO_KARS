import json,math
from pathlib import Path
from kars.parking import footprint,overlaps
reports=[]
folders=[Path('outputs/v8_mall_smoke'),Path('outputs/v8_dense350'),Path('outputs/v8_ground_chowk')]+list(Path('outputs/v8_manual_api/runs').glob('*'))
for folder in folders:
 if not (folder/'trace.jsonl').exists():continue
 active=[];bad=0;maxstep=0;maxrate=0;prev=None
 for line in (folder/'trace.jsonl').open():
  f=json.loads(line);p=f['city'].get('parking',{})
  if not p.get('active'):continue
  ego=f['ego'];lot=f['city']['trip']['parking_lot'];corners=footprint(ego)
  for slot in lot['slots']:
   if slot['occupied'] and overlaps(corners,footprint({'x':slot['front_x'],'y':slot['front_y'],'heading':180},width=1.8)):bad+=1
  assert abs(ego['z'])<.05
  assert all(lot['bounds'][0]<x<lot['bounds'][2] and lot['bounds'][1]<y<lot['bounds'][3] for x,y in corners)
  if prev:
   dt=f['time']-prev['time'];maxstep=max(maxstep,math.hypot(ego['x']-prev['ego']['x'],ego['y']-prev['ego']['y'])/dt);maxrate=max(maxrate,abs((ego['heading']-prev['ego']['heading']+180)%360-180)/dt)
  active.append(f);prev=f
 assert active[-1]['city']['parking']['complete'] and bad==0
 assert any(f['ego']['speed']<-.1 for f in active) and any(f['ego']['speed']>.1 for f in active)
 reports.append({'run':folder.name,'slot':active[-1]['city']['parking']['slot_id'],'parking_frames':len(active),'occupied_vehicle_overlaps':bad,'maximum_observed_speed_mps':maxstep,'maximum_heading_rate_deg_s':maxrate,'ground_level':True,'complete':True})
Path('outputs/v8_parking_audit.json').write_text(json.dumps(reports,indent=2));print(json.dumps(reports,indent=2))
