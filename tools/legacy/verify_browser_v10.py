import asyncio,base64,json,subprocess,threading,time,urllib.request
from pathlib import Path
import websockets
from kars.console import RunManager,LocalServer,make_handler
from kars.models import ROOT
out=ROOT/'outputs/v10_browser_qa';out.mkdir(exist_ok=True)
import shutil
folder=out/'runs/completed_v8';folder.mkdir(parents=True,exist_ok=True)
for name in ['manifest.json','live.json','status.json','metrics.json']:shutil.copy2(ROOT/'outputs/v8_dense350'/name,folder/name)
shutil.copy2(ROOT/'outputs/v9_mall350/manifest.json',folder/'manifest.json')
(folder/'launch.json').write_text(json.dumps({'pid':0,'scenario':'city','algorithm':'city','started_at':0}))
manager=RunManager(out/'runs');server=LocalServer(('127.0.0.1',8786),make_handler(manager))
threading.Thread(target=server.serve_forever,daemon=True).start()
chrome=None;run=None
async def inspect():
 global chrome,run
 chrome=subprocess.Popen([r'C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe','--headless=new','--disable-background-networking','--disable-component-update','--disable-domain-reliability','--disable-sync','--metrics-recording-only','--disable-crash-reporter','--disable-breakpad','--no-sandbox','--disable-crashpad-for-testing','--disable-features=RendererCodeIntegrity','--remote-debugging-port=9262','--user-data-dir='+str(out/'browser-profile-roadster-v10b'),'--enable-unsafe-swiftshader','--use-angle=swiftshader','--no-first-run','--no-default-browser-check','--window-size=1600,1100','about:blank'],stdout=subprocess.DEVNULL,stderr=(out/'chrome.log').open('w'),creationflags=subprocess.CREATE_NO_WINDOW)
 for attempt in range(50):
  try:
   tabs=json.loads(urllib.request.urlopen('http://127.0.0.1:9262/json/list',timeout=1).read());break
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
  await command('Page.navigate',{'url':'http://127.0.0.1:8786/?view=city'})
  for _ in range(60):
   if await evaluate("!!document.querySelector('#city-start-run') && document.querySelector('#city-destination').options.length>0 && document.querySelector('#connection').textContent.includes('connected')"):break
   await asyncio.sleep(.3)
  for _ in range(40):
   if await evaluate("!!document.querySelector('[data-open]')"):break
   await asyncio.sleep(.25)
  await evaluate("document.querySelector('[data-open]').click()")
  await asyncio.sleep(.6)
  await evaluate("document.querySelector('#chase').click()")
  await asyncio.sleep(.6)
  for _ in range(80):
   if await evaluate("document.querySelector('#scene3d').dataset.egoModel==='tesla-roadster' && document.querySelector('.parking-showroom canvas')?.dataset.model==='tesla-roadster'"):break
   await asyncio.sleep(.3)
  assert await evaluate("document.querySelector('#scene3d').dataset.egoModel==='tesla-roadster'")
  assert await evaluate("document.querySelector('.parking-showroom canvas').dataset.model==='tesla-roadster'")
  report=await evaluate("JSON.stringify({signal:document.querySelector('#next-signal').textContent,indicator:document.querySelector('#indicator-reason').textContent,reachable:document.querySelector('#reachable-summary').textContent,webgl:!!document.querySelector('#scene3d').getContext('webgl2'),status:document.querySelector('#status').textContent,parking:document.querySelector('#parking-console').textContent})")
  print('BROWSER:',report.encode('ascii','backslashreplace').decode(),flush=True)
  await evaluate("document.querySelector('#fullscreen-toggle').click()")
  await asyncio.sleep(.6)
  assert await evaluate("!!document.querySelector('.parking-showroom canvas')")
  await evaluate("document.querySelector('[data-car-view=rotate]').click()")
  await asyncio.sleep(.3)
  assert await evaluate("document.querySelector('[data-car-view=rotate]').getAttribute('aria-pressed')==='true'")
  screenshot=await command('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False})
  (out/'live_scene.png').write_bytes(base64.b64decode(screenshot['data']))
  await evaluate("document.querySelector('[data-parking-panel=minimize]').click()")
  assert await evaluate("document.querySelector('#parking-console').getBoundingClientRect().height<100")
  await evaluate("document.querySelector('[data-parking-panel=close]').click()")
  assert await evaluate("getComputedStyle(document.querySelector('#parking-console')).display==='none'")
  await evaluate("document.querySelector('.parking-restore').click()")
  await asyncio.sleep(1)
  assert await evaluate("getComputedStyle(document.querySelector('#parking-console')).display!=='none'")

  print('Roadster loading, orbit and parking controls passed',flush=True)
  (out/'browser_report.json').write_text(json.dumps({'dom':json.loads(report),'exceptions':errors,'parking_panel_controls':{'minimize':True,'close':True,'restore':True},'roadster_loaded_in_driving_and_showroom':True,'showroom_orbit_control':True,'opening_panels':False},indent=2))
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
