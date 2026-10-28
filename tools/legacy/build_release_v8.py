"""Package the runnable V8 release and its recorded validation."""
from pathlib import Path
import ast
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parent
original = Path(r'C:\Users\vivek\SUMO_KARS')


def read(relative):
    return json.loads((root / relative).read_text(encoding='utf-8'))


native = {name: read('outputs/' + name + '/metrics.json') for name in
          ['v8_mall_smoke', 'v8_dense350', 'v8_ground_chowk']}
assert all(m['parked_at_destination'] and m['collision_events'] == 0 for m in native.values())
audit = read('outputs/v8_parking_audit.json')
assert len(audit) == 4 and all(a['occupied_vehicle_overlaps'] == 0 and a['ground_level'] and a['complete'] for a in audit)
manual = read('outputs/v8_manual_api/validation.json')
assert manual['manual_wait'] and manual['occupied_rejected'] and manual['parked']
test_suite = ET.parse(root / 'outputs/v8_test_results.xml').getroot().find('testsuite')
assert int(test_suite.get('tests')) == 88 and int(test_suite.get('failures')) == 0 and int(test_suite.get('errors')) == 0
browser = {name: read('outputs/' + name + '/browser_report.json') for name in
           ['v8_browser_qa', 'v8_reversing_qa', 'v8_underpass_qa']}
assert all(b['dom']['webgl'] and not b['exceptions'] for b in browser.values())
validation = {
    'build': 'parking_city_v8',
    'python_tests_passed': 88,
    'python_test_execution': 'pytest with third-party plugin autoload disabled; local JUnit result checked before packaging',
    'javascript_tests_passed': 39,
    'named_destination_pairs_connected': 90,
    'ground_parking_lots': 10,
    'slots_per_lot': 8,
    'available_slots_per_lot': 5,
    'parking_model': 'bounded private-lot kinematic forward/reverse controller through TraCI; static occupied bay obstacles',
    'native_runs': native,
    'manual_bay_api': manual,
    'parking_footprint_audits': audit,
    'interpolation_only_benchmark': read('outputs/v8_motion_benchmark.json'),
    'browser_webgl_checks': browser,
    'visual_checks': 'Completed parking, reversing and recorded underpass frames inspected in Brave WebGL; no JavaScript exceptions.',
    'audible_output': 'Opt-in audio logic tested; speakers not checked.',
    'performance_scope': '350-background-vehicle native journey completed; interpolation microbenchmarks cover up to 600. No whole-app FPS claim.',
    'signal_stages_seconds': {'green': 25, 'amber': 3, 'all_red': 6},
}
(root / 'docs/VALIDATION_V8.json').write_text(json.dumps(validation, indent=2), encoding='utf-8')
for source, target in [('v8_browser_qa', 'Parking_Complete_V8.png'),
                       ('v8_reversing_qa', 'Parking_Reverse_V8.png'),
                       ('v8_underpass_qa', 'Underpass_View_V8.png')]:
    shutil.copy2(root / 'outputs' / source / 'live_scene.png', root / 'docs' / target)

files = [root / n for n in ['main.py', 'dashboard.py', 'config.yaml', 'requirements.txt',
         'requirements-lock.txt', 'pytest.ini', 'README.md', 'START_HERE.md',
         'Start_City.cmd', 'launch_city.py', 'apply_to_git.py']]
for directory in ['kars', 'simulation_ui', 'sumo', 'tests', 'knowledge_graph']:
    files.extend(p for p in (root / directory).rglob('*') if p.is_file()
                 and '__pycache__' not in p.parts and p.suffix.lower() in
                 ('.py', '.js', '.mjs', '.css', '.html', '.txt', '.xml', '.sumocfg', '.json', '.rq', '.ttl'))
files.extend((root / 'docs').glob('*.md'))
files.extend(root / 'docs' / n for n in ['VALIDATION_V8.json', 'Straight_City_Overview.png',
             'Parking_Complete_V8.png', 'Parking_Reverse_V8.png', 'Underpass_View_V8.png'])
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
name = 'SUMO_KARS_Parking_City_V8'
archive_path = root.parent / (name + '.zip')
with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=7) as archive:
    for path in files:
        archive.write(path, Path(name) / path.relative_to(root))
with zipfile.ZipFile(archive_path) as archive:
    assert archive.testzip() is None
    check = root.parent / 'release_check_v8'
    check.mkdir(exist_ok=True)
    archive.extractall(check)
result = subprocess.run([sys.executable, '-B', 'launch_city.py', '--check'],
                        cwd=check / name, capture_output=True, text=True, timeout=30)
print(result.stdout)
print(result.stderr)
assert result.returncode == 0
print('Archive:', archive_path, 'Files:', len(files), 'Bytes:', archive_path.stat().st_size,
      'Changes:', len(changes))
