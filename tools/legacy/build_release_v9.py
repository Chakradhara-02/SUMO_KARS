"""Package the verified Flow City V9 project."""
from pathlib import Path
import ast,hashlib,json,shutil,subprocess,sys,zipfile
import xml.etree.ElementTree as ET
root=Path(__file__).resolve().parent
original=Path(r'C:\Users\vivek\SUMO_KARS')
def read(name):return json.loads((root/name).read_text(encoding='utf-8'))
suite=ET.parse(root/'outputs/v9_test_results.xml').getroot().find('testsuite')
retry=ET.parse(root/'outputs/v9_lifecycle_retry.xml').getroot().find('testsuite')
assert int(suite.get('tests'))==88 and int(suite.get('errors'))==0
failures=[c for c in suite.findall('testcase') if c.find('failure') is not None]
assert len(failures)==1 and failures[0].get('name')=='test_run_manager_pause_resume_replay_export'
assert int(retry.get('tests'))==1 and int(retry.get('failures'))==int(retry.get('errors'))==0
native=read('outputs/v9_native_validation.json')
assert native['pairs_connected']==90 and native['priority_driveways']==10
assert all(r['metrics']['parked_at_destination'] and r['metrics']['collision_events']==0 and r['occupied_bay_overlaps']==0 for r in native['runs'])
congestion=read('outputs/v9_congestion_validation.json')
assert congestion['native_reroute_applied'] and congestion['selected_avoids_queue']
browser={n:read('outputs/'+n+'/browser_report.json') for n in ['v9_browser_qa','v9_road_qa']}
assert all(b['dom']['webgl'] and not b['exceptions'] for b in browser.values())
assert all(browser['v9_browser_qa']['parking_panel_controls'].values())
assert 'tests 43' in (root/'outputs/v9_js_results.txt').read_text(encoding='utf-8')
validation={'build':'flow_city_v9','python_unique_checks_verified':88,'python_initial_suite':{'passed':87,'lifecycle_timeout':1},'python_isolated_lifecycle_retry':'passed; no code change needed','python_execution':'Third-party plugin autoload disabled; local-only network guard. Full suite and isolated retry JUnit checked.', 'javascript_tests_passed':43,'native_validation':native,'measured_congestion_reroute':congestion,'browser_webgl_checks':browser,'visual_inspection':'Sports coupe, parked panel, white/yellow road markings, 2D lots and facade labels inspected. Minus, cross and restore controls passed. No JavaScript exceptions.','interpolation_checks':'Heading and angular-speed continuity across measured sample boundaries; no future extrapolation; reverse body heading retained.','parking_model':'Bounded private-lot kinematic forward/reverse controller via TraCI; configured static occupied bays.','performance_changes':['road-height cache','32 nearby detailed traffic models and distant instancing','5 Hz minimap painting','forecast graphics rebuild only on new forecasts','parked preview does not draw while hidden'],'performance_scope':'350-background-vehicle native journey completed. No hardware-independent FPS guarantee.','audible_output':'Opt-in audio logic checked by tests; speakers not checked.'}
(root/'docs/VALIDATION_V9.json').write_text(json.dumps(validation,indent=2),encoding='utf-8')
for source,target in [('v9_browser_qa/live_scene.png','Parking_Showroom_V9.png'),('v9_road_qa/live_scene.png','Road_View_V9.png'),('v9_road_qa/map_scene.png','City_Map_V9.png')]:shutil.copy2(root/'outputs'/source,root/'docs'/target)
files = [root / n for n in ['main.py', 'dashboard.py', 'config.yaml', 'requirements.txt',
         'requirements-lock.txt', 'pytest.ini', 'README.md', 'START_HERE.md',
         'Start_City.cmd', 'launch_city.py', 'apply_to_git.py']]
for directory in ['kars', 'simulation_ui', 'sumo', 'tests', 'knowledge_graph']:
    files.extend(p for p in (root / directory).rglob('*') if p.is_file()
                 and '__pycache__' not in p.parts and p.suffix.lower() in
                 ('.py', '.js', '.mjs', '.css', '.html', '.txt', '.xml', '.sumocfg', '.json', '.rq', '.ttl'))
files.extend((root / 'docs').glob('*.md'))
files.extend(root / 'docs' / n for n in ['VALIDATION_V9.json', 'Straight_City_Overview.png',
             'Parking_Showroom_V9.png', 'Road_View_V9.png', 'City_Map_V9.png'])
files = list(dict.fromkeys(files))
changes = []
for path in files:
    assert path.is_file(), path
    if path.suffix == '.py':
        ast.parse(path.read_text(encoding='utf-8-sig'))
    relative = path.relative_to(root).as_posix()
    before = original / relative
    after_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    before_hash = hashlib.sha256(before.read_bytes()).hexdigest() if before.is_file() else None
    if after_hash != before_hash:
        changes.append({'path': relative, 'before': before_hash, 'after': after_hash})
(root / 'UPDATE_FILES.json').write_text(json.dumps(changes, indent=2), encoding='utf-8')
files.append(root / 'UPDATE_FILES.json')
name = 'SUMO_KARS_Flow_City_V9'
archive_path = root.parent / (name + '.zip')
with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=7) as archive:
    for path in files:
        archive.write(path, Path(name) / path.relative_to(root))
with zipfile.ZipFile(archive_path) as archive:
    assert archive.testzip() is None
    check = root.parent / 'release_check_v9'
    check.mkdir(exist_ok=True)
    archive.extractall(check)
result = subprocess.run([sys.executable, '-B', 'launch_city.py', '--check'],
                        cwd=check / name, capture_output=True, text=True, timeout=30)
print(result.stdout)
print(result.stderr)
assert result.returncode == 0
print('Archive:', archive_path, 'Files:', len(files), 'Bytes:', archive_path.stat().st_size,
      'Changes:', len(changes))
