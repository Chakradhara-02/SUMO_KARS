"""Headless browser check with a controlled nearby blocker; no live run changes."""
import asyncio,base64,json,math,subprocess,threading,time,urllib.request,tempfile
from pathlib import Path
import sys
sys.stdout.reconfigure(encoding="utf-8")
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import websockets
from kars.console import LocalServer,make_handler
out=ROOT/'artifacts/local_envelope_qa';out.mkdir(parents=True,exist_ok=True)
base=Path(tempfile.gettempdir())/'pytest-of-srini'
latest=max((p for p in base.glob('pytest-*') if p.name[7:].isdigit()),key=lambda p:int(p.name[7:]))
trace=next(latest.glob('test_native_selected_mall_slot*/trace.jsonl'))
frame=next(json.loads(line) for line in trace.open() if json.loads(line)['ego']['speed']>3)
e=dict(frame['ego']);e.update(speed=8,acceleration=0)
h=math.radians(e['heading']);f=(math.sin(h),math.cos(h));other={**e,'vehicle_id':'nearby_blocker','x':e['x']+f[0]*22,'y':e['y']+f[1]*22,'speed':0}
frame.update(ego=e,vehicles=[e,other],ego_trace=[],time=10)
frame['city']['parking']={'active':False};frame['city']['active_vehicles']=2
frame['city_reachability']={'trajectory':[{'x':e['x']+f[0]*i*5,'y':e['y']+f[1]*i*5,'z':e['z'],'time':10+i,'speed':5} for i in range(6)],'raw':[],'feasible':[],'raw_count':0,'feasible_count':0}
class Fixture:
 def runs(self):return [{'id':'fixture','manifest':{'scenario':'city','algorithm':'city','city_network':'metro_flow_v9.net.xml'},'status':{'state':'completed'},'alive':False,'metrics':{}}]
 def frame(self,*args):return frame
class LegacyHandler(make_handler(Fixture())):
 def do_GET(self):
  # Reproduce the old running dashboard: its whitelist cannot serve workers.
  if self.path.split('?')[0]=='/reachability.worker.bundle.js':
   self.send({'error':'Not found'},404)
  else:super().do_GET()
server=LocalServer(('127.0.0.1',8798),LegacyHandler);threading.Thread(target=server.serve_forever,daemon=True).start()
process=None
async def verify():
 global process
 process=subprocess.Popen([r'C:\Program Files\Google\Chrome\Application\chrome.exe','--headless=new','--disable-background-networking','--disable-background-timer-throttling','--disable-renderer-backgrounding','--disable-backgrounding-occluded-windows','--no-first-run','--no-default-browser-check','--remote-debugging-port=9355','--user-data-dir='+str(out/'profile'),'--enable-unsafe-swiftshader','--use-angle=swiftshader','--window-size=1600,1000','about:blank'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
 for _ in range(40):
  try:tabs=json.load(urllib.request.urlopen('http://127.0.0.1:9355/json/list',timeout=1));break
  except OSError:await asyncio.sleep(.2)
 async with websockets.connect(tabs[0]['webSocketDebuggerUrl'],max_size=20000000) as ws:
  seq=0;errors=[]
  async def command(method,params=None):
   nonlocal seq
   seq+=1;current=seq;await ws.send(json.dumps({'id':current,'method':method,'params':params or {}}))
   while True:
    msg=json.loads(await asyncio.wait_for(ws.recv(),timeout=30))
    if msg.get('method')=='Runtime.exceptionThrown':errors.append(msg)
    if msg.get('id')==current:return msg.get('result',{})
  async def evaluate(code):
   result=await command('Runtime.evaluate',{'expression':code,'returnByValue':True,'awaitPromise':True})
   if result.get('exceptionDetails'):raise RuntimeError(result['exceptionDetails'])
   return result.get('result',{}).get('value')
  await command('Runtime.enable');await command('Page.enable');print('NAV',await command('Page.navigate',{'url':'http://127.0.0.1:8798/?view=city'}),flush=True)
  for _ in range(40):
   if await evaluate("!!document.querySelector('[data-open]')"):break
   await asyncio.sleep(.2)
  await evaluate("document.querySelector('[data-open]').click()")
  for _ in range(70):
   if await evaluate("document.querySelector('#hazard-notifications')?.textContent.includes('nearby_blocker')"):break
   await asyncio.sleep(.3)
  report=await evaluate("({text:document.querySelector('#hazard-notifications').textContent,hidden:document.querySelector('#hazard-notifications').hidden,summary:document.querySelector('#reachable-summary').textContent,drawCalls:document.querySelector('#scene3d').dataset.drawCalls,renderRatio:document.querySelector('#scene3d').dataset.renderRatio,jobs:document.querySelector('#scene3d').dataset.reachabilityJobs,workerMs:document.querySelector('#scene3d').dataset.reachabilityWorkerMs,model:document.querySelector('#scene3d').dataset.egoModel,points:document.querySelector('#scene3d').dataset.localSafePoints,blockedPoints:document.querySelector('#scene3d').dataset.localBlockedPoints})")
  await evaluate("document.querySelector('#chase').click();document.querySelector('.scene-panel').scrollIntoView({block:'start'})")
  await asyncio.sleep(1.5)
  shot=await command('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False});(out/'nearby_blocker.png').write_bytes(base64.b64decode(shot['data']))
  assert not report['hidden'] and 'nearby_blocker' in report['text'],report
  assert 'Online RS' in report['summary'],report
  assert int(report['points'])>0 and int(report['blockedPoints'])>0,report
  # Remove the blocker in the same fixture; the panel must disappear.
  frame['vehicles']=[e];frame['time']=11
  for _ in range(40):
   if await evaluate("document.querySelector('#hazard-notifications').hidden"):break
   await asyncio.sleep(.3)
  assert await evaluate("document.querySelector('#hazard-notifications').hidden")
  assert int(await evaluate("document.querySelector('#scene3d').dataset.offlinePoints"))>0
  await evaluate("document.querySelector('#offline-rs-toggle').click()")
  assert await evaluate("document.querySelector('#offline-rs-toggle').getAttribute('aria-pressed')==='false'")
  await evaluate("document.querySelector('#offline-rs-toggle').click()")
  e['speed']=-.8;e['gear']='R';frame['time']=12
  for _ in range(40):
   if await evaluate("document.querySelector('#scene3d').dataset.reachabilityDirections==='-1'"):break
   await asyncio.sleep(.2)
  print('REVERSE_STATE',json.dumps(await evaluate("({...document.querySelector('#scene3d').dataset,summary:document.querySelector('#reachable-summary').textContent,hidden:document.hidden})")),flush=True)
  assert await evaluate("document.querySelector('#scene3d').dataset.reachabilityDirections==='-1'")
  await asyncio.sleep(1)
  shot=await command('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False});(out/'reverse_offline_online.png').write_bytes(base64.b64decode(shot['data']))
  native_parking=next((json.loads(line) for line in trace.open() if json.loads(line).get('city',{}).get('parking',{}).get('stage')=='reversing' and 110<json.loads(line)['ego']['heading']<160),None)
  if native_parking:
   native_parking['time']=frame['time']+1
   frame.clear();frame.update(native_parking)
   for _ in range(40):
    if await evaluate("document.querySelector('#reachable-summary').textContent.startsWith('Parking RS')"):break
    await asyncio.sleep(.3)
   await asyncio.sleep(1)
   identity=await evaluate("({point:document.querySelector('#scene3d').dataset.selectedReachablePoint,branch:document.querySelector('#scene3d').dataset.selectedReachableBranch,summary:document.querySelector('#reachable-summary').textContent})")
   assert identity['point'].startswith(identity['branch']+':'),identity
   shot=await command('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False});(out/'parking_selected_endpoint.png').write_bytes(base64.b64decode(shot['data']))
   print('PARKING',json.dumps(identity),flush=True)
  timings=await evaluate("new Promise(resolve=>{const times=[];let last=performance.now();function next(now){times.push(now-last);last=now;if(times.length<60)requestAnimationFrame(next);else{times.sort((a,b)=>a-b);resolve({frames:times.length,median_ms:times[30],p95_ms:times[57],drawCalls:document.querySelector('#scene3d').dataset.drawCalls,renderRatio:document.querySelector('#scene3d').dataset.renderRatio,jobs:document.querySelector('#scene3d').dataset.reachabilityJobs});}}requestAnimationFrame(next);})")
  print('FRAME_TIMINGS',json.dumps(timings),flush=True)
  assert not errors,errors
  (out/'report.json').write_text(json.dumps({'blocked_scene':report,'clears_after_blocker_removed':True,'offline_toggle_verified':True,'reverse_directions_verified':True,'frame_timings':timings,'javascript_exceptions':errors},indent=2))
  print(json.dumps(report),flush=True)
try:asyncio.run(verify())
finally:
 if process and process.poll() is None:process.terminate()
 server.shutdown();server.server_close()
