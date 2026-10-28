from pathlib import Path
import ast,hashlib,json
root=Path.cwd();target=Path(r'C:\Users\vivek\SUMO_KARS')
tree=ast.parse((root/'package_city.py').read_text())
files=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='files' for t in n.targets))
files+=['kars/storage.py','tests/test_snapshot_retries.py']
items=[]
for name in files:
 old=target/name
 items.append({'path':name,'expected':hashlib.sha256(old.read_bytes()).hexdigest() if old.exists() else None,'updated':hashlib.sha256((root/name).read_bytes()).hexdigest()})
script='''from pathlib import Path
import datetime, hashlib, json, shutil, subprocess, sys
SOURCE=Path(SOURCEVALUE)
TARGET=Path(r"C:\\Users\\vivek\\SUMO_KARS")
ITEMS=json.loads(PAYLOAD)
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    if not (TARGET/'main.py').exists():raise RuntimeError('Project folder is missing')
    for item in ITEMS:
        original=TARGET/item['path'];prepared=SOURCE/item['path']
        if not prepared.exists() or digest(prepared)!=item['updated']:raise RuntimeError('Prepared file changed: '+item['path'])
        if original.exists() and digest(original) not in (item['expected'],item['updated']):
            raise RuntimeError('Your file changed since preparation: '+item['path']+'. No files were replaced. Share this message so it can be merged.')
    backup=TARGET.parent/('SUMO_KARS_backup_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
    for item in ITEMS:
        destination=TARGET/item['path']
        if destination.exists():
            saved=backup/item['path'];saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(destination,saved)
        destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(SOURCE/item['path'],destination)
    assert 'sound-toggle' in (TARGET/'simulation_ui/index.html').read_text(encoding='utf-8')
    print('REPAIR INSTALLED: fixed wheels, measured indicators, sound button, Windows snapshot retries.',flush=True)
    print('Backup: '+str(backup),flush=True)
    print('Open http://127.0.0.1:8767 and start a NEW city run. Click Enable sound.',flush=True)
    return subprocess.call([sys.executable,'main.py','serve','--port','8767'],cwd=TARGET)
if __name__=='__main__':
    try:sys.exit(main())
    except Exception as error:
        print('UPDATE STOPPED: '+str(error),flush=True);sys.exit(1)
'''.replace('SOURCEVALUE',repr(str(root))).replace('PAYLOAD',repr(json.dumps(items)))
(root/'Apply_Repair.py').write_text(script,encoding='utf-8')
cmd='@echo off\r\n"C:\\Users\\vivek\\AppData\\Local\\Programs\\Python\\Python312\\python.exe" "'+str(root/'Apply_Repair.py')+'"\r\nif errorlevel 1 pause\r\n'
(root/'Repair_and_Start.cmd').write_text(cmd,encoding='ascii')
ast.parse(script)
print('Python-only installer prepared for',len(items),'files')
