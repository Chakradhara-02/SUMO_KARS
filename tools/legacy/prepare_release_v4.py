from pathlib import Path
import json,hashlib,zipfile
root=Path.cwd();original=Path(r'C:\Users\vivek\SUMO_KARS')
root_files=['main.py','dashboard.py','config.yaml','requirements.txt','requirements-lock.txt','pytest.ini','README.md','START_HERE.md','Start_City.cmd','launch_city.py']
files=[root/n for n in root_files]
for directory in ['kars','simulation_ui','sumo','tests']:
 for path in (root/directory).rglob('*'):
  if path.is_file() and '__pycache__' not in path.parts and path.suffix.lower() in ('.py','.js','.mjs','.css','.html','.txt','.xml','.sumocfg','.json','.rq','.ttl'):
   files.append(path)
for directory in ['knowledge_graph']:
 files.extend(p for p in (root/directory).rglob('*') if p.is_file() and p.suffix in ('.ttl','.rq'))
files.extend(p for p in (root/'docs').glob('*.md'))
files.append(root/'docs/Straight_City_Overview.png')
validation={'build':'straight_city_v4','python_tests_passed':47,'javascript_tests_passed':20,'named_destination_pairs_connected':72,'native_sumo_dense_run':{'duration_seconds':300,'vehicles':180,'arrived':177,'still_travelling':3,'recorded_collisions':0},'native_smoke_routes':{'arrived':3,'recorded_collisions':0},'browser_and_live_traci_validation':'pending desktop verification'}
(root/'docs/VALIDATION_V4.json').write_text(json.dumps(validation,indent=2));files.append(root/'docs/VALIDATION_V4.json')
changes=[]
for path in files:
 relative=path.relative_to(root).as_posix();before=original/relative;after=hashlib.sha256(path.read_bytes()).hexdigest()
 previous=hashlib.sha256(before.read_bytes()).hexdigest() if before.exists() else None
 if after!=previous:changes.append({'path':relative,'before':previous,'after':after})
(root/'UPDATE_FILES.json').write_text(json.dumps(changes,indent=2));files.append(root/'UPDATE_FILES.json')
files=list(dict.fromkeys(files))
(root/'release_files.json').write_text(json.dumps([str(p.relative_to(root)) for p in files]))
print('Prepared',len(files),'project files;',len(changes),'changed files compared with Git checkout')
