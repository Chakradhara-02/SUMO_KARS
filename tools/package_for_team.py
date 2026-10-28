from pathlib import Path
import ast
import json
import zipfile

root = Path(__file__).resolve().parents[1]
archive_path = root / 'dist' / 'SUMO_KARS_Team_Project.zip'
archive_path.parent.mkdir(parents=True, exist_ok=True)
top = ['main.py', 'dashboard.py', 'config.yaml',
       'requirements.txt', 'requirements-lock.txt', 'pytest.ini', 'README.md',
       'START_HERE.md', 'Start_City.cmd', 'launch_city.py', 'tools/build_offline_reachability.py', 'tools/build_frontend.py']
files = [root / name for name in top if (root / name).is_file()]
extensions = {'.py', '.js', '.mjs', '.css', '.html', '.txt', '.md', '.xml',
              '.sumocfg', '.json', '.rq', '.ttl', '.glb', '.png', '.jpg', '.jpeg'}
for directory in ['kars', 'simulation_ui', 'sumo', 'tests', 'knowledge_graph', 'docs']:
    files.extend(p for p in (root / directory).rglob('*') if p.is_file()
                 and not any(part in {'__pycache__', '.pytest_cache', 'node_modules',
                                      '.git', 'outputs'} for part in p.relative_to(root).parts)
                 and p.suffix.lower() in extensions)
files = sorted(set(files))
for path in files:
    if path.suffix == '.py':
        ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path.relative_to(root)))
    assert path.name.lower() not in {'.env', 'credentials.json', 'id_rsa'}
assert root / 'simulation_ui/assets/roadster-drive.glb' in files
assert root / 'simulation_ui/assets/roadster-showroom.glb' in files
guide = r'''# SUMO KARS - Teammate setup

This archive contains Roadster City V10 source, browser assets, SUMO networks,
knowledge graph queries, tests and documentation. Extract the entire ZIP first.

## Windows PowerShell

Install Python 3.12. Open PowerShell in the extracted SUMO_KARS folder and run:

```powershell
py -3.12 -m venv sumo_env
.\sumo_env\Scripts\python.exe -m pip install -r requirements.txt
.\sumo_env\Scripts\python.exe launch_city.py --check
.\sumo_env\Scripts\python.exe launch_city.py
```

If `py` is unavailable but Python 3.12 is installed, use
`python -m venv sumo_env` for the first line. Activation is unnecessary.

Open http://127.0.0.1:8784/?view=city on the same computer. Keep the terminal
open. For later launches double-click Start_City.cmd or repeat the last command.

SUMO is installed through the eclipse-sumo dependency. For a separate SUMO
installation, set SUMO_HOME to its installation folder. First-time dependency
installation needs internet; the car assets are included locally.

Select the start, destination, traffic count and an empty bay, then start a new
journey. See START_HERE.md for controls and known limits. Recorded V10 checks
are in docs/VALIDATION_V10.json; earlier release reports are historical results.

## Development

Python checks: `.\sumo_env\Scripts\python.exe -m pytest -q`

JavaScript checks (Node.js needed): `node --test tests/*.test.mjs`

The browser uses app.bundle.js and reachability.worker.bundle.js. After editing
browser modules, rebuild both bundles (Node.js/npx is required):

```
python tools/build_frontend.py
```

Native simulation tests need SUMO and can take time. Extracting this ZIP does
not automatically rerun tests. The ZIP excludes virtual environments, Git
history, saved runs, browser profiles, temporary files and local logs. Each
teammate creates their own environment. Use the shared Git repository to
commit and exchange changes.
'''
with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=7) as archive:
    for path in files:
        archive.write(path, 'SUMO_KARS/' + path.relative_to(root).as_posix())
    archive.writestr('SUMO_KARS/TEAM_SETUP.md', guide)
with zipfile.ZipFile(archive_path) as archive:
    assert archive.testzip() is None
    for path in files:
        assert archive.read('SUMO_KARS/' + path.relative_to(root).as_posix()) == path.read_bytes()
    names = archive.namelist()
    assert all('/outputs/' not in n and '/sumo_env/' not in n and '/.git/' not in n for n in names)
    print(json.dumps({'zip': str(archive_path), 'files': len(names),
                      'size_mb': round(archive_path.stat().st_size / 1e6, 2),
                      'integrity': 'passed', 'source_matches': 'passed',
                      'setup_guide': 'SUMO_KARS/TEAM_SETUP.md'}))
