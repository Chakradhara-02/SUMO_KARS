"""Build the Roadster release using recorded, scoped verification results."""
from pathlib import Path
import ast, hashlib, json, shutil, subprocess, sys, zipfile
import xml.etree.ElementTree as ET

root=Path(__file__).resolve().parent
original=Path(r'C:\Users\vivek\SUMO_KARS')
def read(name):return json.loads((root/name).read_text(encoding='utf-8'))
assert 'tests 47' in (root/'outputs/v10_js_results.txt').read_text(encoding='utf-8')
assert '10 passed, 1 deselected' in (root/'outputs/v10_asset_units.txt').read_text(encoding='utf-8')
suite=ET.parse(root/'outputs/v10_native_final.xml').getroot().find('testsuite')
assert int(suite.get('tests'))==1 and int(suite.get('failures'))==int(suite.get('errors'))==0
native=read('outputs/pytest_v10_native_final/test_native_selected_mall_slot0/metrics.json')
assert native['parked_at_destination'] and native['collision_events']==0 and native['parking_slot']=='A4'
browser={n:read('outputs/'+n+'/browser_report.json') for n in ['v10_browser_qa','v10_road_qa']}
assert all(b['dom']['webgl'] and not b['exceptions'] for b in browser.values())
assert browser['v10_browser_qa']['roadster_loaded_in_driving_and_showroom']
assert all(browser['v10_browser_qa']['parking_panel_controls'].values())
validation={'build':'roadster_city_v10','javascript_tests_passed':47,'python_units_passed':10,
 'native_parking_test_passed':True,'native_metrics':native,'browser_checks':browser,
 'browser_fixture_scope':'Parking preview uses a recorded V8 350-background journey with V9 lot geometry. Road preview uses the new V10 native journey. Both load the actual V10 GLBs. Browser captures are recorded-frame visual checks, not a live frame-rate benchmark.',
 'checks':'Wheel distance and reverse rotation; Ackermann inside/outside angle; position velocity and yaw-rate continuity on unequal sample intervals; measured reverse heading; both GLB structures, dimensions, pivots and triangle budgets; five bay paths and manual bay selection; native forward/reverse arrival and exact final pose; WebGL asset loading and parking controls.',
 'historical_results':'V9 full regression/network/rerouting checks are retained in VALIDATION_V9.json, not claimed as rerun for V10.',
 'limitations':['No hinged body panels in the supplied asset.','No hardware-independent frame-rate guarantee.','Speakers not checked.','Native SUMO can still brake sharply; visual interpolation is not a comfort or safety certification.'],
 'asset':read('simulation_ui/assets/roadster-info.json')}
(root/'docs/VALIDATION_V10.json').write_text(json.dumps(validation,indent=2),encoding='utf-8')
for source,target in [('v10_browser_qa/live_scene.png','Parking_Roadster_V10.png'),('v10_road_qa/live_scene.png','Road_Roadster_V10.png'),('v10_road_qa/map_scene.png','Map_Roadster_V10.png')]:shutil.copy2(root/'outputs'/source,root/'docs'/target)
files=[root/n for n in ['main.py','dashboard.py','config.yaml','requirements.txt','requirements-lock.txt','pytest.ini','README.md','START_HERE.md','Start_City.cmd','launch_city.py','apply_to_git.py']]
for directory in ['kars','simulation_ui','sumo','tests','knowledge_graph']:
 files.extend(p for p in (root/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix.lower() in ('.py','.js','.mjs','.css','.html','.txt','.xml','.sumocfg','.json','.rq','.ttl','.glb'))
files.extend((root/'docs').glob('*.md'))
files.extend(root/'docs'/n for n in ['VALIDATION_V9.json','VALIDATION_V10.json','Straight_City_Overview.png','Parking_Roadster_V10.png','Road_Roadster_V10.png','Map_Roadster_V10.png'])
files=list(dict.fromkeys(files));changes=[]
for path in files:
 assert path.is_file(),path
 if path.suffix=='.py':ast.parse(path.read_text(encoding='utf-8-sig'))
 relative=path.relative_to(root).as_posix();before=original/relative
 after_hash=hashlib.sha256(path.read_bytes()).hexdigest()
 before_hash=hashlib.sha256(before.read_bytes()).hexdigest() if before.is_file() else None
 if after_hash!=before_hash:changes.append({'path':relative,'before':before_hash,'after':after_hash})
(root/'UPDATE_FILES.json').write_text(json.dumps(changes,indent=2),encoding='utf-8');files.append(root/'UPDATE_FILES.json')
name='SUMO_KARS_Roadster_City_V10';archive_path=root.parent/(name+'.zip')
with zipfile.ZipFile(archive_path,'w',zipfile.ZIP_DEFLATED,compresslevel=7) as archive:
 for path in files:archive.write(path,Path(name)/path.relative_to(root))
with zipfile.ZipFile(archive_path) as archive:
 assert archive.testzip() is None
 check=root.parent/'release_check_v10';check.mkdir(exist_ok=True);archive.extractall(check)
result=subprocess.run([sys.executable,'-B','launch_city.py','--check'],cwd=check/name,capture_output=True,text=True,timeout=30)
print(result.stdout);print(result.stderr);assert result.returncode==0
print('Archive:',archive_path,'Files:',len(files),'Bytes:',archive_path.stat().st_size,'Changes:',len(changes))
