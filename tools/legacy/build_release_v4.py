from pathlib import Path
import json,zipfile,subprocess,sys,ast
root=Path.cwd();output=root.parent/'SUMO_KARS_Straight_City_V4.zip'
files=[root/p for p in json.loads((root/'release_files.json').read_text())]+[root/'apply_to_git.py']
for path in files:
 if path.suffix=='.py':ast.parse(path.read_text(encoding='utf-8-sig'))
with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=7) as archive:
 for path in files:archive.write(path,Path('SUMO_KARS_Straight_City_V4')/path.relative_to(root))
with zipfile.ZipFile(output) as archive:
 assert archive.testzip() is None
 check=root.parent/'release_check_v4';check.mkdir(exist_ok=True)
 archive.extractall(check)
extracted=check/'SUMO_KARS_Straight_City_V4'
result=subprocess.run([sys.executable,'-B','launch_city.py','--check'],cwd=extracted,capture_output=True,text=True,timeout=30)
print(result.stdout);print(result.stderr);assert result.returncode==0
print('Archive verified:',output,'files:',len(files),'size:',output.stat().st_size)
