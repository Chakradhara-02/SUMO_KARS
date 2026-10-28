import asyncio,base64,json,subprocess,threading,time,urllib.request
from pathlib import Path
import websockets
from kars.console import RunManager,LocalServer,make_handler
from kars.models import ROOT
out=ROOT/'outputs/v5_browser_qa';out.mkdir(exist_ok=True)
manager=RunManager(out/'runs');server=LocalServer(('127.0.0.1',8770),make_handler(manager))
threading.Thread(target=server.serve_forever,daemon=True).start()
chrome=None;run=None
async def inspect():
 global chrome,run
 chrome=subprocess.Popen([r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe','--headless=new','--disable-crash-reporter','--disable-breakpad','--no-sandbox','--single-process','--no-zygote','--remote-debugging-port=9223','--user-data-dir='+str(out/'edge-single-profile'),'--enable-unsafe-swiftshader','--use-angle=swiftshader','--no-first-run','--no-default-browser-check','--window-size=1600,1100','about:blank'],stdout=subprocess.DEVNULL,stderr=(out/'chrome.log').open('w'),creationflags=subprocess.CREATE_NO_WINDOW)
 for attempt in range(50):
  try:
   tabs=json.loads(urllib.request.urlopen('http://127.0.0.1:9223/json/list',timeout=1).read());break
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
  await command('Runtime.enable');await command('Page.enable')
  await command('Page.navigate',{'url':'http://127.0.0.1:8770/?view=city'})
  for _ in range(60):
   if await evaluate("!!document.querySelector('#city-start-run') && document.querySelector('#connection').textContent.includes('connected')"):break
   await asyncio.sleep(.3)
  # Drive through the actual page controls with native DOM click handling.
  await evaluate("document.querySelector('#city-vehicles').value='20';document.querySelector('#city-destination').value='n2_0';document.querySelector('#city-start-run').click()")
  for _ in range(100):
   if manager.runs() and manager.frame(manager.runs()[0]['id']).get('ego'):break
   await asyncio.sleep(.2)
  run=manager.runs()[0]['id'];manager.command(run,'run',5)
  await evaluate("document.querySelector('#chase').click()")
  await asyncio.sleep(4)
  report=await evaluate("JSON.stringify({signal:document.querySelector('#next-signal').textContent,indicator:document.querySelector('#indicator-reason').textContent,reachable:document.querySelector('#reachable-summary').textContent,webgl:!!document.querySelector('#scene3d').getContext('webgl2'),status:document.querySelector('#status').textContent})")
  print('BROWSER:',report,flush=True)
  screenshot=await command('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False})
  (out/'live_scene.png').write_bytes(base64.b64decode(screenshot['data']))
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
