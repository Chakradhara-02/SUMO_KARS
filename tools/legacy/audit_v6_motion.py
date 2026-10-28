from pathlib import Path
import json,math,xml.etree.ElementTree as ET
root=Path.cwd();net=ET.parse(root/'sumo/network/city/metro_protected_v6.net.xml').getroot();edges={e.get('id'):e for e in net.findall('edge')}
reports=[]
for name in ['v6_dense_seed1','v6_dense_seed2']:
 p=root/'outputs'/name;previous=None;changes=wrong=straight_wrong=0;turns={}
 if not (p/'trace.jsonl').exists():continue
 for line in (p/'trace.jsonl').open():
  try:f=json.loads(line)
  except ValueError:continue
  ego=f['ego']
  if previous and ego['road_id']==previous['road_id'] and not ego['road_id'].startswith(':'):
   points=[[float(v) for v in x.split(',')] for x in edges[ego['road_id']].find('lane').get('shape').split()];a,b=points[0],points[-1];dx,dy=b[0]-a[0],b[1]-a[1];dt=ego['timestamp']-previous['timestamp'];lat=(-dy*(ego['x']-previous['x'])+dx*(ego['y']-previous['y']))/max(.001,math.hypot(dx,dy))/max(.001,dt)
   if abs(lat)>.08 and ego['indicator_reason'].startswith('Changing lane'):
    changes+=1;wrong+=(ego['signals']&3)!=(2 if lat>0 else 1)
  if ego['indicator_reason']=='Continuing straight':straight_wrong+=bool(ego['signals']&3)
  if ego['road_id'].startswith(':'):turns[ego['indicator_reason']]=turns.get(ego['indicator_reason'],0)+1
  previous=ego
 print(name,'t=',f['time'],'lane-change frames',changes,'wrong',wrong,'straight wrong',straight_wrong,'junction labels',turns)

 reports.append({'run':name,'last_time':f['time'],'lane_change_frames_checked':changes,'wrong_lane_change_indications':wrong,'wrong_straight_indications':straight_wrong,'junction_frames':turns})
 assert wrong==0 and straight_wrong==0
assert sum(r['lane_change_frames_checked'] for r in reports)>0
(root/'outputs/v6_indicator_audit.json').write_text(json.dumps(reports,indent=2))
