from pathlib import Path
import ast,hashlib,json,subprocess,sys,zipfile
root=Path.cwd();original=Path(r'C:\Users\vivek\SUMO_KARS')
dense=[]
for name in ['v7_itpark_live','v7_flyover_live']:
 metrics=json.loads((root/'outputs'/name/'metrics.json').read_text())
 assert metrics['parked_at_destination'] and metrics['collision_events']==0
 dense.append(metrics)
validation={'build':'bridge_city_v7','python_tests_passed':79,'javascript_tests_passed':35,'named_destination_pairs_connected':72,'signalized_junctions':25,'protected_approaches':True,'green_phases_checked_against_SUMO_foe_matrix':True,'signal_stages_seconds':{'green':25,'amber':3,'all_red':6},'default_city_journey_limit_seconds':1800,'dense_live_runs':dense,'vehicle_footprint_audits':{name:json.loads((root/'outputs'/name).read_text()) for name in ['v7_itpark_overlap_audit.json','v7_flyover_overlap_audit.json']},'maximum_signal_heads_per_approach':3,'fullscreen_controls_tests':'native entry/exit and expanded-view Escape passed','desktop_visual_and_audio_check':'Not completed: browser processes failed in this execution session. Browser bundle built successfully.'}
assert all(a['nativeOverlaps']==0 and a['renderedOverlaps']==0 for a in validation['vehicle_footprint_audits'].values())
(root/'docs/VALIDATION_V7.json').write_text(json.dumps(validation,indent=2),encoding='utf-8')
files=[root/n for n in ['main.py','dashboard.py','config.yaml','requirements.txt','requirements-lock.txt','pytest.ini','README.md','START_HERE.md','Start_City.cmd','launch_city.py','apply_to_git.py']]
for directory in ['kars','simulation_ui','sumo','tests','knowledge_graph']:
 files.extend(p for p in (root/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix.lower() in ('.py','.js','.mjs','.css','.html','.txt','.xml','.sumocfg','.json','.rq','.ttl'))
files.extend(p for p in (root/'docs').glob('*.md'))
files.extend([root/'docs/VALIDATION_V7.json',root/'docs/Straight_City_Overview.png'])
files=list(dict.fromkeys(files));changes=[]
for path in files:
 assert path.is_file(),path
 if path.suffix=='.py':ast.parse(path.read_text(encoding='utf-8-sig'))
 relative=path.relative_to(root).as_posix();before=original/relative;after=hashlib.sha256(path.read_bytes()).hexdigest();previous=hashlib.sha256(before.read_bytes()).hexdigest() if before.is_file() else None
 if after!=previous:changes.append({'path':relative,'before':previous,'after':after})
(root/'UPDATE_FILES.json').write_text(json.dumps(changes,indent=2),encoding='utf-8');files.append(root/'UPDATE_FILES.json')
archive_path=root.parent/'SUMO_KARS_Bridge_City_V7.zip'
with zipfile.ZipFile(archive_path,'w',zipfile.ZIP_DEFLATED,compresslevel=7) as archive:
 for path in files:archive.write(path,Path('SUMO_KARS_Bridge_City_V7')/path.relative_to(root))
with zipfile.ZipFile(archive_path) as archive:
 assert archive.testzip() is None
 check=root.parent/'release_check_v7';check.mkdir(exist_ok=True);archive.extractall(check)
extracted=check/'SUMO_KARS_Bridge_City_V7'
result=subprocess.run([sys.executable,'-B','launch_city.py','--check'],cwd=extracted,capture_output=True,text=True,timeout=30)
print(result.stdout);print(result.stderr);assert result.returncode==0
print('Archive:',archive_path,'Files:',len(files),'Bytes:',archive_path.stat().st_size,'Changes:',len(changes))
