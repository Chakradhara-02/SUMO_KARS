import asyncio,base64,json,subprocess,threading,time,urllib.request
from pathlib import Path
import websockets
from kars.console import RunManager,LocalServer,make_handler
from kars.models import ROOT
out=ROOT/'outputs/v9_road_qa';out.mkdir(exist_ok=True)
import shutil
folder=out/'runs/completed_v8';folder.mkdir(parents=True,exist_ok=True)
for name in ['manifest.json','live.json','status.json','metrics.json']:shutil.copy2(ROOT/'outputs/v8_dense350'/name,folder/name)
shutil.copy2(ROOT/'outputs/pytest_v9_guarded/test_city_ego_arrives_at_selec0/manifest.json',folder/'manifest.json')
frames=[json.loads(l) for l in (ROOT/'outputs/pytest_v9_guarded/test_city_ego_arrives_at_selec0/trace.jsonl').open()]
frame=next(f for f in frames if f['time']>8 and f['ego']['speed']>5 and not f['ego']['road_id'].startswith(':') and f['city_reachability']['feasible_count']>0)
(folder/'live.json').write_text(json.dumps(frame))
(folder/'launch.json').write_text(json.dumps({'pid':0,'scenario':'city','algorithm':'city','started_at':0}))
manager=RunManager(out/'runs');server=LocalServer(('127.0.0.1',8781),make_handler(manager))
threading.Thread(target=server.serve_forever,daemon=True).start()
chrome=None;run=None
async def inspect():
 global chrome,run
 chrome=subprocess.Popen([r'C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe','--headless=new','--disable-background-networking','--disable-component-update','--disable-domain-reliability','--disable-sync','--metrics-recording-only','--disable-crash-reporter','--disable-breakpad','--no-sandbox','--disable-crashpad-for-testing','--disable-features=RendererCodeIntegrity','--remote-debugging-port=9252','--user-data-dir='+str(out/'browser-profile-road-v9'),'--enable-unsafe-swiftshader','--use-angle=swiftshader','--no-first-run','--no-default-browser-check','--window-size=1600,1100','about:blank'],stdout=subprocess.DEVNULL,stderr=(out/'chrome.log').open('w'),creationflags=subprocess.CREATE_NO_WINDOW)
 for attempt in range(50):
  try:
   tabs=json.loads(urllib.request.urlopen('http://127.0.0.1:9252/json/list',timeout=1).read());break
  except OSError:await asyncio.sleep(.2)
 else:raise RuntimeError('Headless browser did not start')
 async with websockets.connect(tabs[0]['webSocketDebuggerUrl'],max_size=20000000) as socket:
  sequence=0;errors=[]
  async def command(method,params=None):
   nonlocal sequence
   sequence+=1;number=sequence
   await socket.send(json.dumps({'id':number,'method':method,'params':params or {}}))
   while True:
    item=json.loads(await asyncio.wait_for(socket.recv(),timeout=15))
    if item.get('method')=='Runtime.exceptionThrown':errors.append(item)
    if item.get('id')==number:
     if 'error' in item:raise RuntimeError(item['error'])
     return item.get('result',{})
  async def evaluate(expression):
   result=await command('Runtime.evaluate',{'expression':expression,'returnByValue':True,'awaitPromise':True})
   if 'exceptionDetails' in result:raise RuntimeError(result['exceptionDetails'])
   return result.get('result',{}).get('value')
  print('Browser connected',flush=True);await command('Runtime.enable');await command('Page.enable')
  await command('Page.navigate',{'url':'http://127.0.0.1:8781/?view=city'})
  for _ in range(60):
   if await evaluate("!!document.querySelector('#city-start-run') && document.querySelector('#city-destination').options.length>0 && document.querySelector('#connection').textContent.includes('connected')"):break
   await asyncio.sleep(.3)
  for _ in range(40):
   if await evaluate("!!document.querySelector('[data-open]')"):break
   await asyncio.sleep(.25)
  await evaluate("document.querySelector('[data-open]').click()")
  await asyncio.sleep(3)
  await evaluate("document.querySelector('#chase').click()")
  await asyncio.sleep(3)
  report=await evaluate("JSON.stringify({signal:document.querySelector('#next-signal').textContent,indicator:document.querySelector('#indicator-reason').textContent,reachable:document.querySelector('#reachable-summary').textContent,webgl:!!document.querySelector('#scene3d').getContext('webgl2'),status:document.querySelector('#status').textContent,parking:document.querySelector('#parking-console').textContent})")
  print('BROWSER:',report.encode('ascii','backslashreplace').decode(),flush=True)
  await evaluate("document.querySelector('#fullscreen-toggle').click()")
  await asyncio.sleep(1)
  screenshot=await command('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False})
  (out/'live_scene.png').write_bytes(base64.b64decode(screenshot['data']))
  await evaluate("document.querySelector('#mode-2d').click()")
  await asyncio.sleep(1)
  screenshot=await command('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False})
  (out/'map_scene.png').write_bytes(base64.b64decode(screenshot['data']))
  (out/'browser_report.json').write_text(json.dumps({'dom':json.loads(report),'exceptions':errors},indent=2))
  assert not errors,errors
  assert json.loads(report)['webgl']
  # Browser closes in finally.
try:asyncio.run(inspect())
finally:
 if run:
  process=manager.processes.get(run)
  if process and process.poll() is None:
   manager.command(run,'stop')
   try:process.wait(timeout=20)
   except subprocess.TimeoutExpired:process.terminate()
 if chrome and chrome.poll() is None:chrome.terminate()
 server.shutdown();server.server_close()
