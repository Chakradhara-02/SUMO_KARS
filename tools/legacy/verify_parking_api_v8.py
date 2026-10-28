import json,time,threading,urllib.request,urllib.error,gzip
from pathlib import Path
from kars.console import RunManager,LocalServer,make_handler
root=Path('outputs/v8_manual_api');root.mkdir(exist_ok=True);manager=RunManager(root/'runs');server=LocalServer(('127.0.0.1',0),make_handler(manager));threading.Thread(target=server.serve_forever,daemon=True).start();base='http://127.0.0.1:'+str(server.server_address[1])
def api(path,data=None):
 req=urllib.request.Request(base+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'})
 return json.load(urllib.request.urlopen(req,timeout=5))
run=None
try:
 req=urllib.request.Request(base+'/api/network?scenario=city',headers={'Accept-Encoding':'gzip'})
 with urllib.request.urlopen(req,timeout=10) as response:
  assert response.headers.get('Content-Encoding')=='gzip';network=json.loads(gzip.decompress(response.read()));assert any(p['name']=='City Mall' for p in network['points'])
 run=api('/api/run',{'scenario':'city','city_start':'n4_0','city_destination':'city_mall','city_vehicles':20,'duration':800,'realtime':0})['id']
 deadline=time.monotonic()+180
 while time.monotonic()<deadline:
  frame=api('/api/frame?id='+run)
  if frame.get('city',{}).get('parking',{}).get('stage')=='waiting_selection':break
  time.sleep(.12)
 else:raise AssertionError('Did not reach manual bay selection')
 pose=frame['ego'];time.sleep(.5);waiting=api('/api/frame?id='+run);assert abs(waiting['ego']['x']-pose['x'])<.01
 try:api('/api/parking-slot',{'id':run,'slot_id':'A2'})
 except urllib.error.HTTPError as error:assert error.code==400
 else:raise AssertionError('Occupied bay accepted')
 print('Selection wait stable; occupied bay rejected',flush=True)
 assert api('/api/parking-slot',{'id':run,'slot_id':'A6'})['accepted']
 while time.monotonic()<deadline:
  frame=api('/api/frame?id='+run)
  if frame.get('city',{}).get('parked'):break
  time.sleep(.1)
 else:raise AssertionError('Selected bay not reached')
 assert frame['city']['parking']['slot_id']=='A6' and frame['city']['parking']['gear']=='P'
 print('Manual selection A6 parked at',frame['ego']['x'],frame['ego']['y'],flush=True)
 (root/'validation.json').write_text(json.dumps({'gzip_network':True,'manual_wait':True,'occupied_rejected':True,'selected_slot':'A6','parked':True,'pose':frame['ego']},indent=2))
finally:
 if run:
  process=manager.processes.get(run)
  if process and process.poll() is None:
   manager.command(run,'stop');process.wait(timeout=20)
 server.shutdown();server.server_close()
