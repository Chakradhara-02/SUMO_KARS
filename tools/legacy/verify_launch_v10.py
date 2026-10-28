import json,subprocess,sys,time,urllib.request
from pathlib import Path
url='http://127.0.0.1:8784/api/version'
def version():
 with urllib.request.urlopen(url,timeout=2) as r:return json.load(r)
try:info=version()
except OSError:
 log=Path('outputs/v10_server.log').open('a')
 process=subprocess.Popen([sys.executable,'-u','launch_city.py','--no-browser'],cwd=Path.cwd(),stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 for _ in range(30):
  try:info=version();break
  except OSError:time.sleep(.3)
 else:raise RuntimeError('Launch did not become ready; inspect outputs/v10_server.log')
assert info.get('build')=='roadster_city_v10',info
print(json.dumps(info));print('Ready: http://127.0.0.1:8784/?view=city')
