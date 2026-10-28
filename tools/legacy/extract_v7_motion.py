import json,sys
from pathlib import Path
p=Path(sys.argv[1]) if len(sys.argv)>1 else Path('outputs/runs/20261015_224837_682ac3')
out=[];last=-1;green=[]
keys=['vehicle_id','x','y','z','heading','speed','road_id','length','width','signals']
for line in (p/'trace.jsonl').open():
 f=json.loads(line)
 if f['time']-last<.499:continue
 last=f['time'];out.append({'at':last*1000,'frame':{'vehicles':[{k:v[k] for k in keys} for v in f['vehicles']]}})
 if f['ego']['speed']<.1 and str((f['city'].get('next_signal') or {}).get('color','')).lower()=='g':green.append({'t':last,'road':f['ego']['road_id'],'gap':f.get('clearance'),'distance':f['city']['next_signal']['distance']})
Path(sys.argv[2] if len(sys.argv)>2 else 'outputs/v7_saved_motion.json').write_text(json.dumps(out,separators=(',',':')))
print('Saved samples',len(out),'Stopped while next signal green',len(green),'examples',green[:8])
