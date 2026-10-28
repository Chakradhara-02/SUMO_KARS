import {ReachabilityRuntime} from './reachability-runtime.js';
import {createReachabilityWorker} from './reachability-worker-factory.js';
import {motionMarker} from './offline-reachability.js';
let showOfflineReachable=true;
import {localHazardMessages,visibleUnsafeStates} from './local-reachability.js';
import {installParkingUI} from './parking-ui.js';
import {installFullscreen} from './fullscreen.js';
import {renderSignalHud,cityJourneyStatus} from './signal-hud.js';
import {DriverAudio,assistance,turnSignals} from './driver-assist.js';
import {plannerProfiles, matchingRuns, comparisonKey} from './planners.js';
import {SimulationScene} from './scene3d.js';
import {interpolateActors} from './motion.js';
import {buildKnowledgeDiagram,diagramSVG} from './knowledge-graph.js';
import {signalLayout,signalAspect,signalSeconds,crossingLayout} from './signal-layout.js';
import {drawCityLots} from './city-scenery.js';
import {cityTrajectoryPoints,reachableClasses,unsafeLabels,frameReachability,hazardMessages} from './city-overlays.js';
'use strict';
const $=id=>document.getElementById(id), fmt=(v,n=1)=>Number.isFinite(v)?v.toFixed(n):'—';
const escapeHTML=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let selected=null,runs=[],frame={},previousFrame={},receivedAt=0,network={},scenarioInfo={},follow=true,showLayers=true,zoom=1,camera={x:70,y:-4.8},replay=false,replayPlaying=false,replayTime=0,requestVersion=0,chosenVehicle=null,pollBusy=false;
const driverAudio=new DriverAudio();
installFullscreen(document.querySelector('.scene-panel'),$('fullscreen-toggle'),document,()=>window.dispatchEvent(new Event('resize')));
let parameters={scenario:'demo',algorithm:'kars',duration:200,seed:1,density:9,sensor_range:120,delay:0,loss:0,jitter:0,realtime:1,gui:false,outage:false};
let toastTimer,drag=null,hitActors=[],scene3D=null,sceneMode="3d",comparisonAnchor=null,comparisonSignature="",frameFetchFailed=false;
let motionSamples=[],showReachable=true,showSensors=true;
let selectedGraphNode='ego';
let cityPreview=false,cityTrip=null,networkKind='road',routeVersion=0;
let displayedCityRun=null;
let networkSignals=[];
const renderParking=installParkingUI({document,onSelect:async slot=>{if(selected&&currentRun()?.alive)await api('/api/parking-slot',{id:selected,slot_id:slot});parameters.city_parking_slot=slot;scene3D?.setParkingSlot(slot);renderParking(frame,cityTrip,slot);}});
function toast(message){$('toast').textContent=message;$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').hidden=true,4500);}
async function api(path,data){const res=await fetch(path,data?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}:{});const value=await res.json();if(!res.ok)throw new Error(value.error||'Request failed');return value;}
function view(name){for(const key of ['live','runs','planners','compare'])$(key+'-view').hidden=key!==name;document.querySelectorAll('.nav').forEach(n=>n.classList.toggle('active',n.dataset.view===name));document.querySelector('h1').textContent=({live:network.city?'City map':'Traffic simulation',runs:'Run library',planners:'Planner methods',compare:'Planner comparison'})[name];if(name==='compare')renderComparison();if(name==='planners')renderPlannerCards();}
document.querySelectorAll('.nav').forEach(n=>n.onclick=()=>n.dataset.view==='city'?enterCity():n.dataset.view==='live'&&network.city?exitCity():view(n.dataset.view));
async function exitCity(){
 cityPreview=false;parameters={...parameters,scenario:'demo',algorithm:'kars'};
 selected=runs.find(r=>r.manifest.scenario!=='city'&&plannerProfiles[r.manifest.algorithm])?.id||null;
 frame={};motionSamples=[];replay=false;replayPlaying=false;requestVersion++;
 await loadNetwork('road');view('live');follow=true;zoom=1;scene3D?.setCamera('chase');await poll();
}
async function loadNetwork(kind){
 const next=kind==='city'?'city':'road';
 const legacy=next==='city'&&currentRun()&&!currentRun().manifest.city_network;
 const version=next==='city'&&!cityPreview?(legacy?'legacy':currentRun()?.manifest.city_network):null;
 const key=next+(version?'-'+version:'');if(key===networkKind)return;
 network=await api('/api/network'+(next==='city'?'?scenario=city'+(version?'&version='+encodeURIComponent(version):''):''));networkKind=key;networkSignals=signalLayout(network);
 scene3D?.setNetwork(network);scene3D?.setTrip(next==='city'?cityTrip:null);if(next==='city'){showSensors=false;scene3D?.setSensors(false);$('sensor-toggle').classList.remove('selected');}
 document.body.classList.toggle('city-mode',next==='city');
 $('layers').textContent=next==='city'?'Route overlay':'Path & restrictions';
 document.querySelector('.page-footer').innerHTML=next==='city'?'City routing · signalized intersections · independent SUMO traffic controls <span>All displayed motion comes from TraCI. City mode uses SUMO routing.</span>':'Lane-level reachable-set planning · continuous SUMO lane changes · independent SUMO safety enabled <span>All displayed motion and metrics come from TraCI.</span>';
 document.querySelector('.map-legend').innerHTML=next==='city'?'<i class="ego-key"></i>Ego<i class="traffic-key"></i>City traffic<i style="background:#b9a9e3"></i>Offline projection<i style="background:#98a9b4"></i>Online paths<i class="plan-key"></i>Optimized prediction<i class="feasible-key"></i>Feasible positions <i style="background:#eb8792"></i>Blocked positions<i class="obstacle-key"></i>Measured trail':'<i class="ego-key"></i>Ego<i class="traffic-key"></i>Traffic<i class="obstacle-key"></i>Obstruction<i class="plan-key"></i>Planned path<i class="feasible-key"></i>Feasible positions <i style="background:#eb8792"></i>Blocked positions';
 $('city-controls').hidden=next!=='city';$('reachable-summary').hidden=next!=='city';$('reachable-toggle').hidden=false;$('offline-rs-toggle').hidden=next!=='city';$('reachable-toggle').textContent=next==='city'?'Reachable points':'Reachable regions';
 $('scene-title').textContent=next==='city'?'Straight-road city · driving visualization':'Driving visualization';if(next==='city')document.querySelector('.city-heading p').textContent=network.left_hand?'Straight avenues · central underpass · outer expressway · traffic-aware routes':'Archived city network · start a new run for Indian-style roads';
 if(next==='city'){
  for(const id of ['city-start','city-destination'])$(id).innerHTML=network.points.map(p=>`<option value="${escapeHTML(p.id)}">${escapeHTML(p.name)}</option>`).join('');
  $('city-start').value=parameters.city_start||'n0_0';$('city-destination').value=parameters.city_destination||'n4_4';
 }
}
async function previewCityRoute(){
 const version=++routeVersion;
 if(parameters.city_destination!==$('city-destination').value)parameters.city_parking_slot=null;parameters.city_start=$('city-start').value;parameters.city_destination=$('city-destination').value;
 parameters.city_vehicles=Number($('city-vehicles').value);
 $('city-traffic-count').textContent=parameters.city_vehicles+' traffic vehicles';
 if(parameters.city_start===parameters.city_destination){$('city-route-summary').textContent='Choose a destination different from the starting point.';cityTrip=null;scene3D?.setTrip(null);return;}
 try{const trip=await api('/api/city-route?start='+encodeURIComponent(parameters.city_start)+'&destination='+encodeURIComponent(parameters.city_destination));if(version!==routeVersion)return;cityTrip=trip;renderParking(frame,trip,parameters.city_parking_slot);scene3D?.setTrip(trip);scene3D?.setParkingSlot(parameters.city_parking_slot||(trip.destination.id==='city_mall'?null:trip.arrival_bay.slot_id));$('city-route-summary').textContent=`START: ${trip.start.name} → DESTINATION: ${trip.destination.name} · ${(trip.distance/1000).toFixed(2)} km · ${trip.edges.length} street segments`;}
 catch(error){$('city-route-summary').textContent=error.message;cityTrip=null;}
}
async function enterCity(){
 const active=runs.find(r=>r.alive&&r.manifest.scenario==='city');
 if(active){cityPreview=false;chooseRun(active.id);await loadNetwork('city');await pollFrame();return;}
 try{cityPreview=true;displayedCityRun=null;selected=null;frame={};motionSamples=[];replay=false;replayPlaying=false;requestVersion++;parameters={...parameters,scenario:'city',algorithm:'city',duration:1800,city_start:parameters.city_start||'n0_0',city_destination:parameters.city_destination||'n4_4',city_vehicles:parameters.city_vehicles||180};
  view('live');await loadNetwork('city');await previewCityRoute();follow=false;zoom=.12;camera={x:430,y:430};scene3D?.setCamera('overview');setCameraButtons('overview');renderFrame();$('scene-empty').hidden=true;$('subtitle').textContent='Select a start and destination, then drive through measured city traffic.';document.querySelector('h1').textContent='City map';document.querySelectorAll('.nav').forEach(n=>n.classList.toggle('active',n.dataset.view==='city'));
 }catch(error){toast(error.message);}
}
const reachabilityRuntime=new ReachabilityRuntime({createWorker:createReachabilityWorker});
function predictionFor(actors){
 const prediction=reachabilityRuntime.sample(frame,actors,network,{runKey:selected||'preview',includeOffline:showReachable&&showOfflineReachable,includeCandidates:showReachable,enabled:(showLayers||showReachable)&&!$('live-view').hidden&&!document.hidden});
 const canvas=$('scene3d');canvas.dataset.reachabilityJobs=String(reachabilityRuntime.stats.submitted);canvas.dataset.reachabilityWorkerMs=reachabilityRuntime.stats.computeMs.toFixed(2);canvas.dataset.reachabilityStatus=prediction.pendingReason||'ready';canvas.dataset.reachabilityDropped=String(reachabilityRuntime.stats.dropped);canvas.dataset.reachabilityError=reachabilityRuntime.stats.lastError||'';
 return prediction;
}
function drawCityRoute(ctx,X,Y,scale,ego,actors){
 const trip=frame.city?.trip||cityTrip;
 if(trip&&showLayers){ctx.beginPath();trip.shape.forEach((p,i)=>(i?ctx.lineTo.bind(ctx):ctx.moveTo.bind(ctx))(X(p[0]),Y(p[1])));ctx.strokeStyle='#7895a888';ctx.lineWidth=Math.max(1,1.2*scale);ctx.stroke();}
 const candidates=predictionFor(actors);
 if(showReachable){const classes=candidates;renderLocalHazards(classes);
 for(const [samples,color]of [[showOfflineReachable?classes.offline:[],'#b9a9e380'],[classes.safe,'#8bd3aa'],[visibleUnsafeStates(classes,showOfflineReachable),'#eb8792']])for(const raw of samples){const p=motionMarker(raw,ego);if(p.time<frame.time)continue;ctx.fillStyle=color;ctx.beginPath();ctx.arc(X(p.x),Y(p.y),Math.max(2,.25*scale),0,Math.PI*2);ctx.fill();}
 }
 if(showLayers){
  const path=candidates.displaySelected||[];
  const direction=(ego?.speed||0)<-.05||frame.city?.parking?.gear==='R'?-1:1;
  const endpoint=candidates.selectedEndpoint;if(endpoint){const p=motionMarker(endpoint,ego,endpoint.direction);ctx.fillStyle='#2787ff';ctx.beginPath();ctx.arc(X(p.x),Y(p.y),6,0,Math.PI*2);ctx.fill();}
  const visiblePath=path.map(p=>motionMarker({...p,heading:p.heading??ego.heading},ego,p.direction??direction));
  for(const branch of candidates.branches){ctx.beginPath();branch.points.forEach((raw,i)=>{const p=motionMarker(raw,ego,branch.direction);(i?ctx.lineTo.bind(ctx):ctx.moveTo.bind(ctx))(X(p.x),Y(p.y));});ctx.strokeStyle='#98a9b466';ctx.lineWidth=1;ctx.stroke();}
  for(const [points,color,width]of [[(frame.ego_trace||[]).map(p=>({x:p[0],y:p[1]})),'#d98b36',2],[visiblePath,'#2787ff',3]]){
   if(!points.length)continue;ctx.beginPath();points.forEach((p,i)=>(i?ctx.lineTo.bind(ctx):ctx.moveTo.bind(ctx))(X(p.x),Y(p.y)));ctx.strokeStyle=color;ctx.lineWidth=width;ctx.stroke();
  }
 }
 for(const p of network.points||[]){
  const start=trip?.start.id===p.id,destination=trip?.destination.id===p.id;
  ctx.fillStyle=start?'#129b7c':destination?'#e18945':'#7996a8';ctx.beginPath();ctx.arc(X(p.x),Y(p.y),start||destination?7:4,0,Math.PI*2);ctx.fill();
  ctx.font=(start||destination?'600 ':'')+'10px Segoe UI';ctx.textAlign='center';ctx.fillStyle='#25485a';ctx.fillText((start?'START · ':destination?'DESTINATION · ':'')+p.name,X(p.x),Y(p.y)-12);
 }
}
function drawCityMinimap(actors){
 const {ctx,w,h}=canvasSetup($('minimap'));const bounds=network.bounds||{min_x:0,max_x:720,min_y:0,max_y:720},spanX=bounds.max_x-bounds.min_x,spanY=bounds.max_y-bounds.min_y,scale=Math.min((w-16)/spanX,(h-12)/spanY),X=x=>(w-spanX*scale)/2+(x-bounds.min_x)*scale,Y=y=>(h+spanY*scale)/2-(y-bounds.min_y)*scale;
 ctx.fillStyle='#eef3ed';ctx.fillRect(0,0,w,h);ctx.strokeStyle='#acbab7';ctx.lineWidth=1;
 for(const lane of network.lanes||[]){if(lane.internal)continue;ctx.beginPath();lane.shape.forEach((p,i)=>(i?ctx.lineTo.bind(ctx):ctx.moveTo.bind(ctx))(X(p[0]),Y(p[1])));ctx.stroke();}
 const trip=frame.city?.trip||cityTrip;if(trip){ctx.beginPath();trip.shape.forEach((p,i)=>(i?ctx.lineTo.bind(ctx):ctx.moveTo.bind(ctx))(X(p[0]),Y(p[1])));ctx.strokeStyle='#2787ff';ctx.lineWidth=2;ctx.stroke();}
 for(const a of actors){ctx.fillStyle=a.vehicle_id==='ego'?'#078f76':'#9baca7';ctx.beginPath();ctx.arc(X(a.x),Y(a.y),a.vehicle_id==='ego'?3:1,0,Math.PI*2);ctx.fill();}
}
$('city-start').onchange=previewCityRoute;$('city-destination').onchange=previewCityRoute;$('city-vehicles').onchange=previewCityRoute;
$('city-start-run').onclick=()=>{if(!cityTrip||!$('city-vehicles').reportValidity())return;parameters={...parameters,scenario:'city',algorithm:'city',city_start:$('city-start').value,city_destination:$('city-destination').value,city_vehicles:Number($('city-vehicles').value)};startRun();};
function currentRun(){return runs.find(r=>r.id===selected);}
function readParameters(){const data=new FormData($('configuration')),p={};for(const [key,value]of data)p[key]=value;for(const key of ['duration','seed','density','sensor_range','delay','loss','jitter','realtime'])p[key]=Number(p[key]);p.gui=data.has('gui');p.outage=data.has('outage');if(p.scenario==='city')Object.assign(p,{algorithm:'city',city_start:parameters.city_start||'n0_0',city_destination:parameters.city_destination||'n4_4',city_vehicles:Number($('city-vehicles').value)||180,city_parking_slot:parameters.city_parking_slot});return p;}
function scenarioDescription(){const key=$('scenario').value;$('scenario-description').textContent=scenarioInfo[key]?.description||'';}
$('scenario').onchange=()=>{if($('scenario').value==='city'){$('configuration').elements.algorithm.value='city';enterCity();}else if($('configuration').elements.algorithm.value==='city')$('configuration').elements.algorithm.value='kars';scenarioDescription();const f=$('configuration');f.elements.delay.value=$('scenario').value==='iot_delay'?1:0;f.elements.loss.value=$('scenario').value==='iot_delay'?.15:0;};
$('settings-button').onclick=()=>{if(network.city){$('scenario').value='city';$('configuration').elements.algorithm.value='city';$('configuration').elements.duration.value=parameters.duration;}else{$('scenario').value=parameters.scenario;}$('settings').showModal();scenarioDescription();};$('close-settings').onclick=()=>$('settings').close();$('settings').onclick=e=>{if(e.target===$('settings'))$('settings').close();};
$('save-settings').onclick=()=>{if(!$('configuration').reportValidity())return;parameters=readParameters();$('settings').close();toast('Simulation settings saved');};
$('configuration').onsubmit=e=>{e.preventDefault();parameters=readParameters();$('settings').close();startRun();};
async function startRun(){try{$('start').disabled=true;const result=await api('/api/run',parameters);selected=result.id;cityPreview=false;await loadNetwork(parameters.scenario);frame={};previousFrame={};motionSamples=[];replay=false;replayPlaying=false;zoom=network.city?.12:1;follow=!network.city;if(network.city){camera={x:430,y:430};scene3D?.setCamera('overview');}requestVersion++;renderFrame();view('live');$('speed').value=String(parameters.realtime);toast('SUMO is starting');await pollRuns();}catch(e){toast(e.message);}finally{$('start').disabled=!!runs.some(r=>r.alive);}}
$('start').onclick=startRun;
async function command(action,speed){if(!selected)return;try{await api('/api/control',{id:selected,action,speed});await pollRuns();}catch(e){toast(e.message);}}
$('pause').onclick=()=>{if(replay){replayPlaying=!replayPlaying;updateTransport();}else command(currentRun()?.status.state==='paused'?'run':'pause');};$('stop').onclick=()=>command('stop');
$('speed').onchange=()=>{parameters.realtime=Number($('speed').value);if(currentRun()?.alive)command(currentRun().status.state==='paused'?'pause':'run',parameters.realtime);};
$('export').onclick=()=>{if(selected)window.location.assign('/api/export?id='+encodeURIComponent(selected));};
$('follow').onclick=()=>{follow=true;zoom=1;setCameraPreset('follow');};
$('overview').onclick=()=>{follow=false;zoom=network.city?.20:.24;camera=network.city?{x:360,y:360}:{x:500,y:0};setCameraPreset('overview');};
$('layers').onclick=()=>{showLayers=!showLayers;$('layers').classList.toggle('selected',showLayers);scene3D?.setLayers(showLayers);};
$('chart-mode').onchange=drawCharts;
$('chase').onclick=()=>setCameraPreset('chase');
$('mode-3d').onclick=()=>setSceneMode('3d');

$('mode-2d').onclick=()=>setSceneMode('2d');

$('comparison-anchor').onchange=()=>{comparisonAnchor=$('comparison-anchor').value;renderComparison(true);};
$('replay-play').onclick=()=>{replay=true;replayPlaying=!replayPlaying;motionSamples=[];if(replayPlaying&&replayTime>=Number($('scrubber').max))replayTime=.2;updateTransport();};
$('replay-end').onclick=()=>{replay=false;replayPlaying=false;requestVersion++;pollFrame();updateTransport();};
$('scrubber').oninput=()=>{replay=true;replayPlaying=false;replayTime=Number($('scrubber').value);motionSamples=[];pollFrame();updateTransport();};
function updateTransport(){const r=currentRun(),alive=!!r?.alive,state=r?.status.state||'ready';$('start').disabled=runs.some(v=>v.alive);$('city-start-run').disabled=runs.some(v=>v.alive);for(const id of ['city-start','city-destination','city-vehicles'])$(id).disabled=!!r?.alive&&r.manifest.scenario==='city';$('pause').disabled=!alive;$('stop').disabled=!alive;$('pause').textContent=state==='paused'?'▶ Resume':'Ⅱ Pause';$('export').disabled=!r||alive;$('replay-bar').hidden=!r||alive||!frame.time;$('replay-play').textContent=replayPlaying?'Ⅱ Pause replay':'▶ Replay';if(r&&!alive)$('scrubber').max=String(frame.time&& !replay ? frame.time : r.status.time||200);if(!replay&&frame.time)$('scrubber').value=String(frame.time);$('replay-time').textContent=fmt(replay?replayTime:frame.time)+' s';}
function chooseRun(id){cityPreview=false;selected=id;frame={};previousFrame={};motionSamples=[];replay=false;replayPlaying=false;chosenVehicle=null;requestVersion++;follow=true;zoom=1;renderFrame();view('live');pollFrame();updateTransport();}
function drawRunList(){if(!runs.length){$('run-list').innerHTML='<div class="panel" style="padding:35px;color:#8c9d91">No saved runs yet. Start a traffic simulation to record its frames and metrics.</div>';return;}$('run-list').innerHTML=runs.map(r=>{const m=r.metrics,p=r.manifest;return `<article class="run-card"><div><h3>${escapeHTML(scenarioInfo[p.scenario]?.title||p.scenario)} <span class="small-tag">${escapeHTML(r.status.state)}</span></h3><p>${escapeHTML(r.id)}<br>${escapeHTML(p.algorithm)} · seed ${escapeHTML(p.seed??p.parameters?.seed)} · ${new Date((p.started_at||0)*1000).toLocaleString()}</p></div><div class="run-values"><div><small>Arrived</small><b>${m.arrived===undefined?'—':m.arrived?'Yes':'No'}</b></div><div><small>Collisions</small><b>${m.collision_events??'—'}</b></div><div><small>Mean speed</small><b>${Number.isFinite(m.average_speed)?fmt(m.average_speed*3.6)+' km/h':'—'}</b></div><div><small>Travel time</small><b>${fmt(m.travel_time)} s</b></div></div><button class="button outline" data-open="${escapeHTML(r.id)}">${r.alive?'Open live view':'Inspect & replay'} ↗</button></article>`;}).join('');document.querySelectorAll('[data-open]').forEach(b=>b.onclick=()=>chooseRun(b.dataset.open));}
async function pollRuns(){runs=await api('/api/runs');$('run-count').textContent=runs.length;if(!selected&&!cityPreview&&runs.length)selected=(runs.find(r=>plannerProfiles[r.manifest.algorithm])||runs[0]).id;drawRunList();const r=currentRun(),state=r?.status.state||'ready';$('status').className='badge '+state;$('status').textContent=r?.manifest.scenario==='city'&&r?.status.end_reason==='duration_limit'?'JOURNEY LIMIT REACHED':state.toUpperCase();if(r){const p=r.manifest;await loadNetwork(p.scenario);if(p.scenario==='city'&&p.city_trip&&displayedCityRun!==r.id){displayedCityRun=r.id;cityTrip=p.city_trip;$('city-start').value=cityTrip.start.id;$('city-destination').value=cityTrip.destination.id;$('city-vehicles').value=p.traffic_target||180;scene3D?.setTrip(cityTrip);$('city-route-summary').textContent=`START: ${cityTrip.start.name} → DESTINATION: ${cityTrip.destination.name} · ${(cityTrip.distance/1000).toFixed(2)} km`;}$('session-info').innerHTML=`<strong>${escapeHTML(scenarioInfo[p.scenario]?.title||p.scenario)}</strong>${escapeHTML(p.algorithm)}<br>${escapeHTML(r.id)}<br>Seed ${escapeHTML(p.seed??p.parameters?.seed)}`;$('subtitle').textContent=scenarioInfo[p.scenario]?.description||'Recorded simulation';$('planner-name').textContent=({kars_delay:'KARS + age (legacy)',kars:'KARS',astar:'A*',rs:'Basic RS (legacy)'})[p.algorithm]||p.algorithm;$('run-id').textContent=r.id;}if(!$('compare-view').hidden)renderComparison();updateTransport();}
async function pollFrame(){if(!selected)return;const version=++requestVersion,runId=selected;try{const data=await api('/api/frame?id='+encodeURIComponent(runId)+(replay?'&time='+replayTime.toFixed(2):''));if(version!==requestVersion||selected!==runId)return;if(data.time!==frame.time){previousFrame=frame;frame=data;receivedAt=performance.now();motionSamples.push({at:receivedAt,frame:data});motionSamples=motionSamples.slice(-8);}else frame=data;frameFetchFailed=false;renderFrame();}catch(e){frameFetchFailed=true;} }
function renderFrame(){if(!frame.ego){clearFrameDisplay();return;}const e=frame.ego;$('metric-time').textContent=fmt(frame.time);$('metric-speed').textContent=fmt(Math.abs(e.speed)*3.6);$('metric-acceleration').textContent=fmt(e.acceleration,2)+' m/s² acceleration';$('metric-gap').textContent=fmt(frame.clearance);$('metric-ttc').textContent=Number.isFinite(frame.ttc)?fmt(frame.ttc)+' s time to collision':'No closing vehicle';$('metric-age').textContent=fmt(frame.age);$('metric-packets').textContent=`${frame.packets?.received??'—'} received · ${frame.packets?.lost??'—'} lost`;$('actor-count').textContent=(frame.vehicles?.length||0)+' actors';$('triples').textContent=['rs','astar'].includes(currentRun()?.manifest.algorithm)?'Not used':frame.triples??0;$('pruned').textContent=frame.removed_edges??0;$('planning-ms').textContent=fmt(frame.planning_ms)+' ms';$('selected-lane').textContent=frame.selected_lane===null||frame.selected_lane===undefined?'—':frame.selected_lane;$('sensor-count').textContent=`${frame.local_vehicles??0} / ${frame.remote_vehicles??0}`;$('query-ms').textContent=fmt(frame.query_ms,2)+' ms';$('safety-banner').textContent=frame.city?(frame.city?.parked?'PARKED AT DESTINATION':currentRun()?.metrics.arrived?'DESTINATION REACHED':'CITY ROUTE · SUMO TRAFFIC CONTROL'):frame.emergency?(e.speed<.1?'WAITING · BLOCKED':'BRAKING · TAP FOR REASON'):frame.controlled_stop?'CAUTION · SHORT HORIZON':'PLANNING · ROUTE AVAILABLE';$('safety-banner').title=frame.emergency_reason||frame.control_reason||'Constraint-valid path available';$('safety-banner').dataset.help='braking';$('safety-banner').classList.toggle('danger',!!frame.emergency);
 const unique=new Map();for(const c of frame.constraints||[]){if(c.finish<frame.time||c.begin>frame.time+5||c.end<e.x||c.start>e.x+130||((frame.vehicles||[]).some(v=>v.vehicle_id===c.source)))continue;unique.set(c.source,c);}const constraints=[...unique.values()];$('constraint-count').textContent=constraints.length;$('constraints').innerHTML=constraints.length?constraints.map(c=>`<div class="restriction"><div><b>${escapeHTML(c.source)}</b><small>${fmt(c.start,0)}–${fmt(c.end,0)} m · ${c.lane<0?'all lanes':'lane '+c.lane}${c.kind.includes('speed')?' · '+fmt(c.speed,0)+' m/s':''}</small></div></div>`).join(''):'<div class="empty-small">No nearby infrastructure restrictions.</div>';
 $('candidates').innerHTML=(frame.candidates||[]).map(c=>`<div class="candidate ${c.lane===frame.selected_lane?'chosen':''}"><span>Lane ${c.lane}${c.lane===frame.selected_lane?' · selected':''}</span><span>Cost ${fmt(c.cost,2)}</span></div>`).join('')||'No feasible corridor';if(frame.city){$('candidates').innerHTML=(frame.city.alternatives||[]).map((r,i)=>`<div class="candidate ${r.selected?'chosen':''}"><span>Route ${i+1}${r.selected?' · executing':''}</span><span>${(r.distance/1000).toFixed(2)} km · ${Math.round(r.eta)} s · ${r.traffic} vehicles</span></div>`).join('')||'Measuring route alternatives…';}if(chosenVehicle){const actor=(frame.vehicles||[]).find(v=>v.vehicle_id===chosenVehicle);$('vehicle-detail').textContent=actor?JSON.stringify(actor,null,2):'Actor is no longer in this frame.';}renderDriving();renderDiagnostics();renderKnowledgeWorkspace();scene3D?.setFrame(frame,selected);$('scene-empty').hidden=!!frame.ego;drawCharts();updateTransport();}
function clearFrameDisplay(){renderDriving();renderKnowledgeWorkspace();for(const id of ['metric-time','metric-speed','metric-gap','metric-age','planning-ms','query-ms','selected-lane'])$(id).textContent='—';$('metric-acceleration').textContent='Awaiting measured motion';$('metric-ttc').textContent='Awaiting clearance';$('metric-packets').textContent='Awaiting packet data';$('actor-count').textContent='0 actors';$('triples').textContent='0';$('pruned').textContent='0';$('sensor-count').textContent='0 / 0';$('plan-diagnostics').innerHTML='<div class="empty-small">Awaiting planner diagnostics.</div>';$('constraints').innerHTML='';$('constraint-count').textContent='0';$('candidates').innerHTML='';$('scene-empty').hidden=!!network.city;$('safety-banner').textContent=network.city?'CITY ROUTE · READY':'AWAITING PLANNER';$('safety-banner').classList.remove('danger');scene3D?.setFrame({},selected);drawCharts();}
function canvasSetup(canvas){const box=canvas.getBoundingClientRect(),ratio=window.devicePixelRatio||1,w=Math.max(1,box.width),h=Math.max(1,box.height);if(canvas.width!==Math.round(w*ratio)||canvas.height!==Math.round(h*ratio)){canvas.width=Math.round(w*ratio);canvas.height=Math.round(h*ratio);}const ctx=canvas.getContext('2d');ctx.setTransform(ratio,0,0,ratio,0,0);ctx.clearRect(0,0,w,h);return{ctx,w,h};}
function roundRect(ctx,x,y,w,h,r){ctx.beginPath();ctx.roundRect(x,y,w,h,r);}
function drawCharts(){drawTelemetry();}
function axes(ctx,w,h,xmin,xmax,ymin,ymax,xlabel,ylabel){const left=38,right=w-17,top=17,bottom=h-25,x=v=>left+(v-xmin)/(xmax-xmin||1)*(right-left),y=v=>bottom-(v-ymin)/(ymax-ymin||1)*(bottom-top);ctx.font='8px Segoe UI';ctx.textAlign='right';ctx.fillStyle='#9daea3';ctx.strokeStyle='#edf2ed';ctx.lineWidth=1;for(let i=0;i<=3;i++){const value=ymin+(ymax-ymin)*i/3,py=y(value);ctx.beginPath();ctx.moveTo(left,py);ctx.lineTo(right,py);ctx.stroke();ctx.fillText(fmt(value,0),left-7,py+3);}ctx.textAlign='center';for(let i=0;i<=3;i++){const value=xmin+(xmax-xmin)*i/3;ctx.fillText(fmt(value,0),x(value),bottom+13);}ctx.textAlign='left';ctx.fillText(ylabel,left,10);ctx.textAlign='right';ctx.fillText(xlabel,right,h-3);return{x,y,left,right,top,bottom};}
function drawTelemetry(){const{ctx,w,h}=canvasSetup($('telemetry')),key=$('chart-mode').value,rows=(frame.history||[]).filter(r=>Number.isFinite(r[key]));let ymin=Math.min(0,...rows.map(r=>r[key])),ymax=Math.max(key==='speed'?16:1,...rows.map(r=>r[key]));const a=axes(ctx,w,h,rows[0]?.timestamp||0,Math.max(5,rows.at(-1)?.timestamp||5),ymin,ymax,'time · s',({speed:'m/s',acceleration:'m/s²',clearance:'m',knowledge_age:'s'})[key]);if(!rows.length)return;ctx.beginPath();ctx.moveTo(a.x(rows[0].timestamp),a.bottom);rows.forEach(r=>ctx.lineTo(a.x(r.timestamp),a.y(r[key])));ctx.lineTo(a.x(rows.at(-1).timestamp),a.bottom);ctx.closePath();const gradient=ctx.createLinearGradient(0,a.top,0,a.bottom);gradient.addColorStop(0,'#afd9c780');gradient.addColorStop(1,'#dcece210');ctx.fillStyle=gradient;ctx.fill();ctx.beginPath();rows.forEach((r,i)=>(i?ctx.lineTo.bind(ctx):ctx.moveTo.bind(ctx))(a.x(r.timestamp),a.y(r[key])));ctx.strokeStyle='#278f74';ctx.lineWidth=2;ctx.stroke();}
function displayedActors(now){
 if(!motionSamples.length||replay&&!replayPlaying)return frame.vehicles||[];
 // Buffer measured samples instead of moving for 220 ms then freezing until
 // the next 500 ms poll. Never predict motion beyond the newest observation.
 return interpolateActors(motionSamples,now-(replayPlaying?260:650));
}
function drawMap(now){const{ctx,w,h}=canvasSetup($('scene')),actors=displayedActors(now),ego=actors.find(a=>a.vehicle_id==='ego');if(follow){camera.x=ego?ego.x+(network.city?0:55):network.city?360:90;camera.y=ego?ego.y:network.city?360:-4.8;}const scale=(network.city?Math.min(w,h)/180:w/240)*zoom,X=x=>w/2+(x-camera.x)*scale,Y=y=>h/2-(y-camera.y)*scale;ctx.fillStyle='#e8ede5';ctx.fillRect(0,0,w,h);
 // Procedural scenery is presentation geometry; road and actor coordinates
 // below are read from the actual SUMO network and measured frames.
 if(!network.city)for(let x=Math.floor((camera.x-w/scale/2)/35)*35;x<camera.x+w/scale/2;x+=35){if(Math.abs(x-500)<25)continue;for(const side of[-1,1]){const y=side>0?25:-42;ctx.fillStyle='#d7e1d3';roundRect(ctx,X(x),Y(y+12),26*scale,17*scale,2*scale);ctx.fill();ctx.fillStyle='#e0e7da';roundRect(ctx,X(x+1),Y(y+13),26*scale,17*scale,2*scale);ctx.fill();ctx.strokeStyle='#c9d6c5';ctx.lineWidth=.7;ctx.stroke();ctx.fillStyle='#cedcc6';ctx.fillRect(X(x+4),Y(y+9),20*scale,scale);for(let j=0;j<3;j++){const tx=X(x+j*9+5),ty=Y(side>0?16:-24);ctx.fillStyle='#c5d6bd';ctx.beginPath();ctx.arc(tx+scale,ty+scale,2.5*scale,0,Math.PI*2);ctx.fill();ctx.fillStyle='#b4cbaa';ctx.beginPath();ctx.arc(tx,ty,2.5*scale,0,Math.PI*2);ctx.fill();}}}
 if(network.city)for(const d of network.districts||[]){ctx.fillStyle=d.color;ctx.fillRect(X(d.x-50),Y(d.y+45),100*scale,90*scale);ctx.fillStyle='#526577';ctx.font='bold 10px Segoe UI';ctx.textAlign='center';ctx.fillText(d.name,X(d.x),Y(d.y));ctx.textAlign='left';}ctx.lineCap='round';for(const j of network.junctions||[]){if(j.shape.length<3)continue;ctx.beginPath();j.shape.forEach((p,i)=>(i?ctx.lineTo.bind(ctx):ctx.moveTo.bind(ctx))(X(p[0]),Y(p[1])));ctx.closePath();ctx.fillStyle='#788586';ctx.fill();}for(const lane of network.lanes||[]){if(lane.internal)continue;ctx.beginPath();lane.shape.forEach((p,i)=>(i?ctx.lineTo.bind(ctx):ctx.moveTo.bind(ctx))(X(p[0]),Y(p[1])));ctx.strokeStyle='#7c8888';ctx.lineWidth=lane.width*scale;ctx.stroke();ctx.beginPath();lane.shape.forEach((p,i)=>{const a=lane.shape[Math.max(0,i-1)],b=lane.shape[Math.min(lane.shape.length-1,i+1)],length=Math.hypot(b[0]-a[0],b[1]-a[1])||1;(i?ctx.lineTo.bind(ctx):ctx.moveTo.bind(ctx))(X(p[0]+(b[1]-a[1])/length*lane.width/2),Y(p[1]-(b[0]-a[0])/length*lane.width/2));});ctx.strokeStyle=network.city&&network.left_hand&&lane.id.endsWith('_1')?'#ddbc42':'#d6ded6';ctx.lineWidth=Math.max(.5,.12*scale);ctx.setLineDash(network.city&&network.left_hand&&lane.id.endsWith('_1')?[]:[2.8*scale,4.2*scale]);ctx.stroke();ctx.setLineDash([]);}ctx.lineCap='butt';
 if(network.city)drawCityLots(ctx,network.parking_lots,X,Y,scale);
 if(showReachable&&!network.city){const classes=frameReachability(frame);
 for(const [samples,color]of [[showOfflineReachable?classes.offline:[],'#b9a9e380'],[classes.safe,'#8bd3aa'],[visibleUnsafeStates(classes,showOfflineReachable),'#eb8792']])for(const p of samples){if(!p.layer)continue;ctx.fillStyle=color;ctx.beginPath();ctx.arc(X(p.x),Y(-8+p.lane*3.2),2.5,0,Math.PI*2);ctx.fill();}
 }
 if(showSensors&&ego&&frame.sensing){ctx.strokeStyle='#4b9be640';ctx.lineWidth=1;ctx.setLineDash([3,5]);ctx.beginPath();ctx.arc(X(ego.x),Y(ego.y),frame.sensing.range*scale,0,Math.PI*2);ctx.stroke();ctx.setLineDash([]);for(const v of (frame.sensing.observations||[]).filter(v=>v.id!=='ego').slice(0,14)){ctx.strokeStyle=v.source==='IoT'?'#9a7bca50':'#4b9be650';ctx.beginPath();ctx.moveTo(X(ego.x),Y(ego.y));ctx.lineTo(X(v.x),Y(v.y));ctx.stroke();ctx.beginPath();ctx.arc(X(v.x),Y(v.y),Math.max(3,1.6*scale),0,Math.PI*2);ctx.stroke();}}
 if(showLayers){for(const c of frame.world_constraints||[]){if(c.finish<frame.time||c.begin>frame.time||c.end<camera.x-150||c.start>camera.x+150)continue;if(c.kind==='spatial'||c.kind==='spatial_temporal'){const y=c.lane<0?0:-6.4+c.lane*3.2;ctx.fillStyle='#d9803f25';ctx.fillRect(X(c.start),Y(y),(c.end-c.start)*scale,(c.lane<0?9.6:3.2)*scale);ctx.strokeStyle='#c9905860';ctx.lineWidth=1;ctx.strokeRect(X(c.start),Y(y),(c.end-c.start)*scale,(c.lane<0?9.6:3.2)*scale);}else if(c.kind.includes('speed')&&c.speed<16){ctx.fillStyle=c.speed===0?'#cc756f25':'#b7cf8c30';ctx.fillRect(X(c.start),Y(0),(c.end-c.start)*scale,9.6*scale);}}const t=frame.trajectory;if(t&&t.x?.length){ctx.beginPath();t.x.forEach((x,i)=>{const y=t.world_y?.[i]??(-8+t.lane[i]*3.2);(i?ctx.lineTo.bind(ctx):ctx.moveTo.bind(ctx))(X(x),Y(y));});ctx.strokeStyle='#2787ff35';ctx.lineWidth=2.4*scale;ctx.lineJoin='round';ctx.stroke();ctx.strokeStyle='#2787ff';ctx.lineWidth=1.5;ctx.setLineDash([4,4]);ctx.stroke();ctx.setLineDash([]);}}
 if(network.city)for(const approach of networkSignals){
  const crossing=crossingLayout(network,approach);ctx.strokeStyle='#fff9df';ctx.lineWidth=Math.max(1,.48*scale);
  for(const p of crossing.stripes){ctx.beginPath();ctx.moveTo(X(p.x-crossing.tangent.x*1.6),Y(p.y-crossing.tangent.y*1.6));ctx.lineTo(X(p.x+crossing.tangent.x*1.6),Y(p.y+crossing.tangent.y*1.6));ctx.stroke();}
 }
 // Signals are colored using the measured traffic-light state.
 for(const approach of networkSignals)for(const head of approach.heads){const aspect=signalAspect(frame.signals,head.movement);ctx.fillStyle={green:'#25a46e',amber:'#edb640',red:'#d75c50',off:'#6e8191'}[aspect];ctx.strokeStyle='#253846';ctx.lineWidth=.7;ctx.beginPath();ctx.arc(X(head.x),Y(head.y),Math.max(2,.3*scale),0,Math.PI*2);ctx.fill();ctx.stroke();const seconds=signalSeconds(frame.signals,head.movement);if(scale>1.8&&seconds!==null){ctx.font='bold 10px monospace';ctx.fillText(String(seconds),X(head.x)+4,Y(head.y)-4);}}
 if(network.city)drawCityRoute(ctx,X,Y,scale,ego,actors);hitActors=[];for(const v of actors){const color=v.vehicle_id==='ego'?'#087e72':/truck|barrier/.test(v.vehicle_id)?'#c9854d':v.vehicle_id==='lead'?'#647f96':'#8e9d9b';const cx=X(v.x),cy=Y(v.y),length=Math.max(3,v.length*scale),width=Math.max(2,v.width*scale);ctx.save();ctx.translate(cx,cy);ctx.rotate((v.heading-90)*Math.PI/180);ctx.fillStyle='#34433925';roundRect(ctx,-length+scale,-width/2+scale,length,width,width*.15);ctx.fill();ctx.fillStyle=color;roundRect(ctx,-length,-width/2,length,width,width*.16);ctx.fill();ctx.fillStyle=v.vehicle_id==='ego'?'#a5d9c5':'#c5d2cb';ctx.fillRect(-length*.4,-width*.35,length*.19,width*.7);ctx.fillStyle='#c9d9cc';ctx.fillRect(-length*.85,-width*.32,length*.22,width*.64);ctx.fillStyle='#e0e9d0';ctx.fillRect(-length*.08,-width*.4,length*.045,width*.18);ctx.fillRect(-length*.08,width*.22,length*.045,width*.18);ctx.restore();hitActors.push({id:v.vehicle_id,x:cx-length/2,y:cy,r:Math.max(8,length/2)});if(v.vehicle_id==='ego'){ctx.font='600 9px Segoe UI';ctx.fillStyle='#087e72';ctx.textAlign='center';ctx.fillText('EGO',cx-length/2,cy-width/2-9);ctx.strokeStyle='#087e7225';ctx.lineWidth=1;roundRect(ctx,cx-length-4,cy-width/2-4,length+8,width+8,4);ctx.stroke();}}
 ctx.fillStyle='#87998b';ctx.font='8px Segoe UI';ctx.textAlign='center';for(let x=Math.ceil((camera.x-w/scale/2)/50)*50;x<camera.x+w/scale/2;x+=50){ctx.fillText(x+' m',X(x),Y(-13));}drawMinimap(actors,camera,w/scale);}
function drawMinimap(actors,cam,extent){if(network.city){drawCityMinimap(actors);return;}const{ctx,w,h}=canvasSetup($('minimap')),X=x=>10+x/1000*(w-20),Y=y=>h/2-y/400*(h-8);ctx.fillStyle='#edf3e9';ctx.fillRect(0,0,w,h);ctx.strokeStyle='#b1c0b1';ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(X(0),Y(-4.8));ctx.lineTo(X(1000),Y(-4.8));ctx.moveTo(X(501),Y(-180));ctx.lineTo(X(501),Y(180));ctx.stroke();ctx.fillStyle='#5ea08015';ctx.strokeStyle='#539779';ctx.lineWidth=.8;ctx.fillRect(X(cam.x-extent/2),8,extent/1000*(w-20),h-16);ctx.strokeRect(X(cam.x-extent/2),8,extent/1000*(w-20),h-16);for(const a of actors){ctx.fillStyle=a.vehicle_id==='ego'?'#087e72':/barrier|truck/.test(a.vehicle_id)?'#c9854d':'#94a592';ctx.beginPath();ctx.arc(X(a.x),Y(a.y),a.vehicle_id==='ego'?2.6:1.5,0,Math.PI*2);ctx.fill();}}
$('scene').addEventListener('wheel',e=>{e.preventDefault();zoom=Math.max(network.city?.08:.18,Math.min(5,zoom*Math.exp(-e.deltaY*.001)));},{passive:false});
$('scene').addEventListener('pointerdown',e=>{drag={x:e.clientX,y:e.clientY,startX:e.clientX,startY:e.clientY,camera:{...camera}};$('scene').setPointerCapture(e.pointerId);});
$('scene').addEventListener('pointermove',e=>{if(!drag)return;const scale=(network.city?Math.min($('scene').clientWidth,$('scene').clientHeight)/180:$('scene').clientWidth/240)*zoom,dx=e.clientX-drag.x,dy=e.clientY-drag.y;if(Math.hypot(dx,dy)>3){follow=false;$('follow').classList.remove('selected');camera.x=drag.camera.x-dx/scale;camera.y=drag.camera.y+dy/scale;}});
$('scene').addEventListener('pointerup',e=>{if(drag&&Math.hypot(e.clientX-drag.startX,e.clientY-drag.startY)<5){const rect=$('scene').getBoundingClientRect(),x=e.clientX-rect.left,y=e.clientY-rect.top,actor=hitActors.find(a=>Math.hypot(a.x-x,a.y-y)<a.r);if(actor){chosenVehicle=actor.id;$('vehicle-detail').parentElement.open=true;renderFrame();}}drag=null;});
let lastAnimation=performance.now(),lastReplayFetch=0;function animate(now){const driverLive=!replay&&!!currentRun()?.alive&&currentRun()?.status.state==='running'&&!frameFetchFailed&&now-receivedAt<2000&&!$('live-view').hidden;driverAudio.update(frame,driverLive,now);if(now-(animate.lastDriverHud||0)>100){animate.lastDriverHud=now;const lights=turnSignals(frame.ego),blink=Math.floor((frame.time||0)*2)%2===0;for(const side of ['left','right'])$('indicator-'+side).classList.toggle('lit',!!lights[side]&&blink);const alert=assistance(frame);$('adas-state').textContent=alert.message;$('adas-state').dataset.level=alert.level;$('adas-state').hidden=alert.level==='none';}const elapsed=(now-lastAnimation)/1000;lastAnimation=now;if(replayPlaying){replayTime+=elapsed*(Number($('speed').value)||5);if(replayTime>=Number($('scrubber').max)){replayTime=Number($('scrubber').max);replayPlaying=false;}$('scrubber').value=String(replayTime);$('replay-time').textContent=fmt(replayTime)+' s';if(now-lastReplayFetch>200){lastReplayFetch=now;pollFrame();}}if(!$('live-view').hidden){if(sceneMode==='2d')drawMap(now);else if(scene3D){const actors=displayedActors(now);scene3D.render(actors,predictionFor(actors));if(now-(animate.lastHazards||0)>100){animate.lastHazards=now;renderLocalHazards(scene3D.localClasses);}if(now-(animate.lastMap||0)>200){animate.lastMap=now;drawMinimap(actors,{x:frame.ego?.x||60},150);}}}requestAnimationFrame(animate);}
let lastRunRefresh=0;
async function poll(){if(pollBusy)return;pollBusy=true;try{if(performance.now()-lastRunRefresh>1800){await pollRuns();lastRunRefresh=performance.now();}if(!replay)await pollFrame();$('connection').textContent=frameFetchFailed?'Reconnecting to engine…':'Local engine connected';}catch(e){$('connection').textContent='Reconnecting to engine…';}finally{pollBusy=false;}}
$('engine-log').parentElement.addEventListener('toggle',async e=>{if(e.target.open&&selected){try{$('engine-log').textContent=(await api('/api/log?id='+selected)).log;}catch(error){toast(error.message);}}});
window.addEventListener('resize',drawCharts);
async function init(){try{[network,scenarioInfo]=await Promise.all([api('/api/network'),api('/api/scenarios')]);networkSignals=signalLayout(network);scenarioDescription();await init3D();renderPlannerCards();installParameterHelp();if(new URLSearchParams(location.search).get('view')==='city')await enterCity();else await poll();drawCharts();setInterval(poll,250);requestAnimationFrame(animate);}catch(e){$('connection').textContent='Connecting to local engine…';toast(e.message);setTimeout(init,1500);}}
async function init3D(){
 try{scene3D=new SimulationScene($('scene3d'),id=>{chosenVehicle=id;$('vehicle-detail').parentElement.open=true;renderFrame();},text=>{$('scene-inspection').textContent=text;$('scene-inspection').hidden=false;});scene3D.setNetwork(network);scene3D.setTrip(cityTrip);setCameraButtons('chase');}
 catch(error){$('mode-3d').disabled=true;setSceneMode('2d');toast('3D unavailable on this browser. The measured 2D view remains available.');console.warn('3D initialization:',error);}
}
function setSceneMode(mode){
 if(!['2d','3d'].includes(mode)||mode==='3d'&&!scene3D)return;
 sceneMode=mode;$('scene').hidden=mode!=='2d';$('scene3d').hidden=mode==='2d';
 for(const [id,key]of [['mode-3d','3d'],['mode-2d','2d']])$(id).classList.toggle('selected',mode===key);
 $('scene-title').textContent=mode==='2d'?'Traffic map · 2D':'Driving visualization · 3D';
 $('map-help').textContent=mode==='2d'?'Scroll to zoom · drag to pan · click a vehicle':'Drag to orbit · right-drag to pan · scroll to zoom · click a vehicle';
 $('chase').disabled=mode==='2d';$('scene-inspection').hidden=true;
 if(network.city){follow=false;zoom=.12;camera={x:430,y:430};scene3D?.setCamera('overview');setCameraButtons('overview');}
 else{follow=true;zoom=1;scene3D?.setCamera('chase');setCameraButtons(mode==='3d'?'chase':'follow');}
}
function setCameraButtons(preset){for(const name of ['follow','chase','overview'])$(name).classList.toggle('selected',name===preset);}
function setCameraPreset(preset){if(sceneMode!=='2d')scene3D?.setCamera(preset);setCameraButtons(preset);}
function renderDiagnostics(){
 const algorithm=currentRun()?.manifest.algorithm||parameters.algorithm;document.querySelector('.pipeline').innerHTML=`<span>SENSE</span><i>→</i><span>${['rs','astar'].includes(algorithm)?'DIRECT':'QUERY'}</span><i>→</i><span>PRUNE</span><i>→</i><span>${algorithm==='astar'?'A*':'DP'}</span>`;
 const expanded=$('plan-diagnostics').querySelector('details')?.open;
 const d=frame.diagnostics||{},raw=frame.raw||[],feasible=frame.adjusted||[],planTime=frame.plan_time??raw[0]?.t;
 const profile=plannerProfiles[currentRun()?.manifest.algorithm||parameters.algorithm]||plannerProfiles.kars;
 const stages=d.timings_ms||{};const total=Object.values(stages).reduce((a,b)=>a+b,0)||1;
 const reasons=Object.entries(d.rejection_reasons||{}).sort((a,b)=>b[1]-a[1]).slice(0,6);
 $('plan-diagnostics').innerHTML=`<div class="diagnostic-header"><b>${escapeHTML(d.solver||profile.search)}</b><span>Plan age ${fmt(Number.isFinite(planTime)?frame.time-planTime:NaN)} s</span></div><div class="state-counts"><div><b>${d.raw_nodes??raw.length}</b><small>raw states</small></div><span>→</span><div><b>${d.feasible_nodes??feasible.length}</b><small>retained</small></div><span>→</span><div><b>${frame.chain?.length||0}</b><small>path states</small></div></div><div class="diagnostic-line">Smoothing <b>${frame.emergency?'braking override':escapeHTML(d.optimization_status|| (frame.trajectory?.optimized?'accepted':frame.trajectory?'discrete fallback':'no path'))}</b></div>${d.constraints_used!==undefined?`<div class="diagnostic-line">Constraints used <b>${d.constraints_used} / ${d.constraints_received}</b></div>`:''}<details class="stage-details"><summary>Stage timings & pruning reasons</summary>${Object.keys(stages).length?`<div class="timing-stack">${Object.entries(stages).map(([k,v],i)=>`<i title="${escapeHTML(k)}: ${fmt(v,2)} ms" style="width:${Math.max(1,v/total*100)}%;background:${['#43a897','#eba466','#6b89b8','#a599cf','#d1b775'][i]}"></i>`).join('')}</div>${Object.entries(stages).map(([k,v])=>`<div class="diagnostic-line"><span>${escapeHTML(k)}</span><b>${fmt(v,2)} ms</b></div>`).join('')}`:'<p>Re-run to record stage diagnostics.</p>'}<div class="reason-title">Rejected transitions by source</div>${reasons.length?reasons.map(([reason,count])=>`<div class="diagnostic-line"><span>${escapeHTML(reason)}</span><b>${count}</b></div>`).join(''):'<p>No rejection details in this snapshot.</p>'}<p>One transition may have several rejection reasons. Retained states can include paths that end before the horizon.</p></details>`;
 $('candidates').innerHTML=(frame.candidates||[]).map(c=>`<div class="candidate ${c.lane===frame.selected_lane?'chosen':''}"><div>Lane ${c.lane}${c.lane===frame.selected_lane?' · selected':''}<small>${c.nodes?.length??'—'} states · margin proxy ${c.margin}</small></div><div>Score ${fmt(c.score,2)}<small>path cost ${fmt(c.cost,2)}</small></div></div>`).join('')||'<div class="empty-small">No full-horizon corridor.</div>';
 if(expanded)$('plan-diagnostics').querySelector('details').open=true;

}
function usePlanner(algorithm,reference=null){
 if(reference){const m=reference.manifest,c=m.config;parameters={...parameters,scenario:m.scenario,seed:m.seed,duration:m.duration,density:m.density_period,delay:reference.metrics.delay??m.delay??0,loss:reference.metrics.loss??m.loss??0,jitter:c.delay_jitter,sensor_range:c.sensor_range,outage:c.outage_end>c.outage_begin};}
 parameters.algorithm=algorithm;
 const form=$('configuration');for(const [k,v]of Object.entries(parameters)){const element=form.elements[k];if(element){if(element.type==='checkbox')element.checked=!!v;else element.value=String(v);}}
 scenarioDescription();$('settings').showModal();
}
function renderPlannerCards(){
 const active=currentRun()?.manifest.algorithm||parameters.algorithm;
 $('planner-cards').innerHTML=Object.entries(plannerProfiles).map(([id,p],i)=>`<article class="panel planner-card ${id===active?'active-planner':''}" style="--planner-color:${p.color}"><div class="planner-top"><span class="method-number">0${i+1}</span><span class="small-tag">${p.tag}</span></div><h3>${p.title}</h3><p>${p.summary}</p><ol class="method-stages">${p.stages.map(stage=>`<li>${stage}</li>`).join('')}</ol><dl><dt>Knowledge input</dt><dd>${p.knowledge}</dd><dt>Search method</dt><dd>${p.search}</dd><dt>Vehicle prediction</dt><dd>${p.prediction}</dd><dt>Constraint coverage</dt><dd>${p.constraints}</dd><dt>Fallback</dt><dd>${p.fallback}</dd></dl><div class="paper-note">${p.paper}</div><button class="button outline" data-planner="${id}">Configure ${p.short} →</button></article>`).join('');
 document.querySelectorAll('[data-planner]').forEach(b=>b.onclick=()=>usePlanner(b.dataset.planner));
 const c=currentRun()?.manifest.config||{},w=c.weights||{center:.1,efficiency:1,stability:.2,lane_change:2};
 $('shared-settings').innerHTML=[['Horizon',(c.horizon??5)+' steps'],['Planning step',(c.dt??1)+' s'],['SUMO step',(c.simulation_dt??.2)+' s'],['Speed cap',(c.max_speed??16)+' m/s'],['Node limit',(c.max_states??180)+' / layer'],['Lane change',(c.lane_change_duration??2.5)+' s']].map(([k,v])=>`<div><small>${k}</small><b>${v}</b></div>`).join('');
 $('cost-formula').textContent=`${w.center} × |lane − 1| + ${w.efficiency} × (v_max − v)² / v_max + ${w.stability} × a² + ${w.lane_change} × |Δlane| + 0.01`;
}
function renderComparison(force=false){
 const completed=runs.filter(r=>plannerProfiles[r.manifest.algorithm]&&!r.alive&&r.status.state==='completed'&&Object.keys(r.metrics).length);
 const signature=JSON.stringify(completed.map(r=>[r.id,r.manifest.started_at]));
 if(!force&&signature===comparisonSignature)return;comparisonSignature=signature;
 if(!completed.some(r=>r.id===comparisonAnchor))comparisonAnchor=completed.some(r=>r.id===selected)?selected:completed[0]?.id;
 $('comparison-anchor').innerHTML=completed.map(r=>`<option value="${escapeHTML(r.id)}" ${r.id===comparisonAnchor?'selected':''}>${escapeHTML(r.manifest.scenario)} · ${escapeHTML(r.manifest.algorithm)} · seed ${r.manifest.seed} · ${escapeHTML(r.id)}</option>`).join('')||'<option>No completed runs</option>';
 const anchor=completed.find(r=>r.id===comparisonAnchor),matches=matchingRuns(completed,anchor);
 $('comparison-summary').textContent=!anchor?'Complete a simulation to populate this comparison.':comparisonKey(anchor)?`Seed ${anchor.manifest.seed} · ${anchor.manifest.duration} s duration · insertion every ${anchor.manifest.density_period} s · ${matches.filter(r=>plannerProfiles[r.manifest.algorithm]).length} of 2 planners matched`:'This saved run lacks complete provenance. Run the planners again to build a reliable comparison.';
 const headers=['Planner','Outcome','Mean speed','Travel time','Collisions','Rule samples','Acceleration RMS','Peak jerk','Plan cycle'];
 $('comparison-table').innerHTML=`<thead><tr>${headers.map(h=>`<th>${h}</th>`).join('')}</tr></thead><tbody>${Object.entries(plannerProfiles).map(([id,p])=>{const r=matches.find(r=>r.manifest.algorithm===id),m=r?.metrics;return `<tr><td><b>${p.short}</b>${r?`<button class="comparison-open" data-open-comparison="${r.id}">Inspect run ↗</button>`:''}</td>${m?[m.arrived?'Arrived':m.end_reason||'Did not arrive',fmt(m.average_speed)+' m/s',fmt(m.travel_time)+' s',m.collision_events,m.rule_violations,fmt(m.acceleration_rms,2)+' m/s²',fmt(m.max_jerk,2)+' m/s³',fmt(m.planning_ms,2)+' ms'].map(v=>`<td>${escapeHTML(v)}</td>`).join(''):'<td colspan="8" class="missing-result">No matching completed run</td>'}</tr>`;}).join('')}</tbody>`;
 $('comparison-missing').innerHTML=anchor?Object.entries(plannerProfiles).filter(([id])=>!matches.some(r=>r.manifest.algorithm===id)).map(([id,p])=>`<button class="button outline" data-match-planner="${id}">Configure ${p.short} with reference settings</button>`).join(''):'';
 document.querySelectorAll('[data-open-comparison]').forEach(b=>b.onclick=()=>chooseRun(b.dataset.openComparison));
 document.querySelectorAll('[data-match-planner]').forEach(b=>b.onclick=()=>usePlanner(b.dataset.matchPlanner,anchor));
}

// Short explanations are shared by the driving HUD, telemetry and run controls.
const logic = {
 lane:{title:'Lane changing',description:'The planner scores feasible future paths using progress, acceleration and lane-change cost. The tracker requests one adjacent lane at a time, holds that commitment during replanning and reserves both lanes during the manoeuvre. Lane changes are blocked in the solid-line region (80–140 m) and outside the main road. SUMO may delay a request for safety.'},
 acceleration:{title:'Acceleration & braking',description:'The trajectory supplies a speed target. Each SUMO step limits its change using the configured acceleration and braking bounds. SLSQP smoothing penalizes acceleration changes; if no safe path exists, the emergency controller requests braking. Measured acceleration may differ because SUMO enforces safety.'},
 target:{title:'Target speed',description:'This is the tracker’s next speed command, not a guarantee of executed speed. The planner balances progress against acceleration cost, obstacles and active speed or signal restrictions. The command is bounded by the speed cap and acceleration limits.'},
 gap:{title:'Clearance & collision time',description:'Clearance is the measured bumper gap to traffic ahead overlapping the ego vehicle laterally. Collision time is gap divided by closing speed; it is unavailable when traffic is not closing. The configured safety gap expands planning occupancy, while measured clearance is the actual physical gap.'},
 age:{title:'Knowledge age',description:'Age measures the freshness of remote information. Both active planners receive delivered packets fused with current onboard observations. Delayed packets can misrepresent distant traffic. Missing packets alone do not require emergency braking. Onboard sensing continues independently.'},
 scenario:{title:'Traffic scenario',description:'Each scenario activates different physical events and restrictions. Both 2D and 3D use the same measured SUMO frames, signals and selected trajectory. Switching the view does not change the simulation.'},
 algorithm:{title:'Planner',description:'KARS uses the ontology vocabulary to encode RDF traffic facts, queries restrictions with SPARQL and searches with dynamic programming. A* receives the same delivered restrictions directly and searches the same reachable graph without RDF/SPARQL. Changing the planner applies to the next run.'},
 duration:{title:'Run duration',description:'The maximum simulated time. A run can finish earlier when the ego vehicle arrives. Reaching the duration limit does not mean the route was completed.'},
 seed:{title:'Random seed',description:'Controls repeatable traffic generation. Compare planners with the same seed and scenario; use multiple seeds for broader evaluation.'},
 density:{title:'Traffic insertion interval',description:'Seconds between inserted background vehicles. A smaller interval creates denser traffic. It is an insertion period, not a vehicle count.'},
 sensor_range:{title:'Onboard sensing range',description:'Nearby vehicles within this distance are observed locally. Vehicles outside it rely on available remote messages. The displayed sensing boundary is a visual guide.'},
 delay:{title:'IoT message delay',description:'Adds simulated delivery latency to remote traffic messages. Onboard observations remain current; distant observations reflect the last delivered packet timestamp.'},
 loss:{title:'Packet loss',description:'Fraction of remote messages dropped, from 0 (none) to 1 (all). It does not disable onboard sensing.'},
 jitter:{title:'Delay jitter',description:'Random variation around the configured delivery delay. The ± value is in seconds; delivery latency remains nonnegative.'},
 realtime:{title:'Execution speed',description:'Controls wall-clock playback pacing, not vehicle speed or physical dynamics. Maximum runs without intentional pacing.'},
 outage:{title:'Communication blackout',description:'Drops remote communication between simulated seconds 30 and 40. Onboard observations remain available. Runs shorter than 30 seconds do not reach this event.'},
 gui:{title:'Native SUMO window',description:'Opens SUMO’s own viewer alongside this dashboard. It does not change the selected planner.'},
 path:{title:'Planned path & restrictions',description:'The blue path is the current requested trajectory. Shaded road sections show planning restrictions, not measured vehicle bodies. Turning this overlay off changes only the display.'}
};
let openLogicKey=null;
function logicValues(key){
 const c=currentRun()?.manifest.config||{},e=frame.ego||{},cmd=frame.commands||{};
 const values={lane:[['Measured lane',e.lane],['Commanded lane',cmd.command_lane],['Manoeuvre active',cmd.lane_change_active===undefined?'—':cmd.lane_change_active?'Yes':'No'],['Nominal duration',(c.lane_change_duration??2.5)+' s']],acceleration:[['Measured acceleration',fmt(e.acceleration,2)+' m/s²'],['Acceleration bound',(c.max_acceleration??2)+' m/s²'],['Braking bound',(c.min_acceleration??-4)+' m/s²'],['SUMO step',(c.simulation_dt??.2)+' s']],target:[['Measured speed',fmt(Math.abs(e.speed)*3.6)+' km/h'],['Command speed',fmt(cmd.command_speed*3.6)+' km/h'],['Speed cap',fmt((c.max_speed??16)*3.6)+' km/h']],gap:[['Measured gap',fmt(frame.clearance)+' m'],['Collision time',fmt(frame.ttc)+' s'],['Planning safety gap',(c.safety_gap??8)+' m']],age:[['Knowledge age',fmt(frame.age)+' s'],['Stale threshold',(c.stale_timeout??3)+' s']]};
 values.braking=[['Current status',frame.emergency?'Bounded braking / obstacle wait':'Normal planning'],['Reason',frame.emergency_reason||frame.control_reason||'No emergency requested'],['Measured speed',fmt(Math.abs(e.speed)*3.6)+' km/h']];return values[key]||[];
}
function updateLogicValues(){if(!openLogicKey)return;if(stageKeys.includes(openLogicKey)){renderStageDetail(openLogicKey);return;}$('logic-values').innerHTML=logicValues(openLogicKey).map(([k,v])=>`<div><span>${escapeHTML(k)}</span><b>${escapeHTML(v??'—')}</b></div>`).join('');}
function showLogic(key){if(stageKeys.includes(key)){showStage(key);return;}if(!logic[key])return;openLogicKey=key;$('logic-title').textContent=logic[key].title;$('logic-description').textContent=logic[key].description;updateLogicValues();if(!$('logic-dialog').open)$('logic-dialog').showModal();}
document.addEventListener('click',event=>{const button=event.target.closest('[data-help]');if(button){event.preventDefault();showLogic(button.dataset.help);}});
$('close-logic').onclick=()=>$('logic-dialog').close();
$('logic-dialog').onclick=e=>{if(e.target===$('logic-dialog'))$('logic-dialog').close();};
$('logic-dialog').addEventListener('close',()=>{openLogicKey=null;});
function installParameterHelp(){
 for(const input of $('configuration').querySelectorAll('input,select')){
  if(!logic[input.name])continue;const label=input.closest('label');if(label.querySelector('[data-help]'))continue;
  const button=document.createElement('button');button.type='button';button.className='help-button';button.dataset.help=input.name;button.textContent='ⓘ';button.setAttribute('aria-label','Explain '+logic[input.name].title);button.title=logic[input.name].description;label.insertBefore(button,input);
 }
 for(const [id,key]of [['metric-acceleration','acceleration'],['metric-gap','gap'],['metric-age','age'],['selected-lane','lane'],['safety-banner','braking']]){const element=$(id);element.dataset.help=key;element.tabIndex=0;element.setAttribute('role','button');element.title=logic[key].description;element.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();showLogic(key);}});}
}
function renderLocalHazards(classes){
 if(!network.city||!classes)return;
 if(classes.pending){$('hazard-notifications').hidden=true;$('reachable-summary').textContent=classes.disabled?'Reachability layers hidden':classes.unavailable?'Reachability preview unavailable':'Updating reachable sets…';return;}
 const messages=localHazardMessages(classes,showOfflineReachable),notification=$('hazard-notifications');
 notification.hidden=!showReachable||!messages.length||$('live-view').hidden;
 const html=messages.length?'<strong>Nearby blocked states</strong>'+messages.map(m=>'<div>'+escapeHTML(m)+'</div>').join(''):'';
 if(notification.innerHTML!==html)notification.innerHTML=html;
 const reasons=new Map();for(const p of visibleUnsafeStates(classes,showOfflineReachable))reasons.set(p.reason||'Rejected state',(reasons.get(p.reason||'Rejected state')||0)+1);$('reachable-summary').title=[...reasons].map(([reason,count])=>count+' states: '+reason).join('\n')||'No rejected states in the displayed envelope';
 $('reachable-summary').textContent=`${classes.mode==='parking'?'Parking RS':'Online RS'}${showOfflineReachable?' + offline envelope':''} · ${classes.directions?.includes(-1)?'reverse'+(classes.directions.includes(1)?' / forward':''):'forward'} · ${visibleUnsafeStates(classes,showOfflineReachable).length} rejected · selected endpoint ${classes.selectedEndpoint?Math.max(0,classes.selectedEndpoint.time-frame.time).toFixed(1)+' s':'—'}`;
}
function renderDriving(){
 const messages=network.city?localHazardMessages(predictionFor(displayedActors(performance.now())),showOfflineReachable):hazardMessages(frame),notification=$('hazard-notifications');
 notification.hidden=!showReachable||!messages.length||$('live-view').hidden;
 notification.innerHTML=messages.length?'<strong>Nearby blocked states</strong>'+messages.map(m=>'<div>'+escapeHTML(m)+'</div>').join(''):'';
renderParking(frame,cityTrip,parameters.city_parking_slot);if(frame.city){const c=frame.city;$('journey-distance').textContent=(c.remaining/1000).toFixed(2)+' km';$('journey-eta').textContent=Number.isFinite(c.eta)?Math.ceil(c.eta/60)+' min estimate':'Measuring';$('journey-turn').textContent=(c.parking?.complete?'Parked in bay '+c.parking.slot_id:c.instruction||'Follow the route')+(Number.isFinite(c.junction_distance)?' · '+Math.round(c.junction_distance)+' m':'');$('journey-options').textContent=(c.alternatives?.length||1)+' routes · traffic + distance';}if(network.city){const classes=predictionFor(displayedActors(performance.now()));renderLocalHazards(classes);$('reachable-summary').title='Online sampled bicycle reachability, recomputed from the displayed vehicle state. Gray branches are candidate motions; pale green samples pass checks and red samples mark rejected road, signal, speed or vehicle states. Blue is the lowest-cost feasible candidate. Lavender points are the valid projection of precomputed motion primitives. Their first rejected state is red; later unreachable samples are hidden. The source offline library is unchanged.';if(frame.city?.parking?.complete)$('reachable-summary').textContent='Parking complete';}if(frame.city)$('city-traffic-count').textContent=frame.city.active_vehicles+' active · target '+frame.city.traffic_target;
 const e=frame.ego,cmd=frame.commands||{};
 renderSignalHud(frame,$('next-signal'),$('indicator-reason'));$('traffic-context').textContent=frame.city?.parking?.complete?'Vehicle secured in bay '+frame.city.parking.slot_id:frame.city?.motion_context?.message||(!frame.ego?'Choose a start and destination':frame.city?.parked?'Vehicle secured in destination bay':frame.ego?.speed<.2?'Waiting for traffic or the approach signal':'Following the selected route');document.querySelector('.turn-indicators').dataset.parked=String(!!frame.city?.parked);$('next-signal').hidden=!network.city;$('indicator-reason').hidden=!network.city;
 $('drive-speed').textContent=e?fmt(Math.abs(e.speed)*3.6,0):'—';
 $('drive-status').textContent=frame.city?cityJourneyStatus(frame,currentRun()):!e?'WAITING FOR TELEMETRY':frame.emergency?'EMERGENCY BRAKING':frame.controlled_stop?'CAUTIOUS BRAKING':cmd.lane_change_active?'CHANGING LANE':e.acceleration<-.15?'DECELERATING':e.acceleration>.15?'ACCELERATING':'HOLDING SPEED';
 $('drive-scenario').textContent=cityPreview&&cityTrip?`${cityTrip.start.name} → ${cityTrip.destination.name}`:frame.city?`${frame.city.trip.start.name} → ${frame.city.trip.destination.name}`:scenarioInfo[currentRun()?.manifest.scenario]?.title||'All scenarios · 2D + 3D';
 $('decision-lane').textContent=!e?'Awaiting plan':cmd.lane_change_active?`Lane ${e.lane} → ${cmd.command_lane}`:`Holding lane ${e.lane}`;
 $('decision-acceleration').textContent=fmt(e?.acceleration,2)+' m/s²';
 $('decision-target').textContent=fmt(cmd.command_speed*3.6)+' km/h';
 $('decision-gap').textContent=Number.isFinite(frame.clearance)?fmt(frame.clearance)+' m':'No lead vehicle';updateLogicValues();
}

$('offline-rs-toggle').onclick=()=>{showOfflineReachable=!showOfflineReachable;$('offline-rs-toggle').classList.toggle('selected',showOfflineReachable);$('offline-rs-toggle').setAttribute('aria-pressed',String(showOfflineReachable));scene3D?.setOfflineReachable(showOfflineReachable);renderDriving();};
$('reachable-toggle').onclick=()=>{showReachable=!showReachable;$('reachable-toggle').classList.toggle('selected',showReachable);scene3D?.setReachable(showReachable);renderDriving();};
$('sound-toggle').onclick=async()=>{try{const on=await driverAudio.toggle();$('sound-toggle').textContent=on?'Sound on':'Enable sound';$('sound-toggle').setAttribute('aria-pressed',String(on));$('sound-toggle').classList.toggle('selected',on);if(on)driverAudio.tone(500,.06);}catch(e){toast(e.message);}};
$('sensor-toggle').onclick=()=>{showSensors=!showSensors;$('sensor-toggle').classList.toggle('selected',showSensors);scene3D?.setSensors(showSensors);};
logic.braking={title:'Why is the vehicle braking?',description:'Braking is required when no constraint-valid horizon path exists or an active all-lane blockage enters the stopping envelope. A safe shortened horizon requests controlled braking and replanning. Missing remote packets alone do not request emergency braking. The reason below is recorded by the simulation; legacy runs may not contain it.'};
const stageKeys=['sensing','ontology','graph','sparql','reachable','planner','actuation'];
const stageInfo={
 sensing:['01','Sense & fuse','Positions, speeds, lanes and signal state come from TraCI. Within the configured range they form simulated onboard observations. Outside it, delivered IoT packets supply potentially older observations. This simulates sensing; there is no camera, lidar or radar detector in the current code.'],
 ontology:['02','Ontology vocabulary','The static traffic.ttl ontology defines vehicles, lanes, road boundaries, markings, speed signs, zones, crossings, signals and constraints, with explicit relationships between them. It provides the vocabulary used to encode observations; it is not a sensor and does not receive data independently. No OWL inference or GeoSPARQL reasoning is executed.'],
 graph:['03','Knowledge graph','Figure 6 of the supplied base paper connects vehicles, lanes, road boundaries, lane markings and speed-limit geometry. This interactive view maps those relationships to the selected SUMO run; the recorded constraints feed KARS’s SPARQL query and reachable-state pruning.'],
 sparql:['04','SPARQL restrictions','The real constraints.rq SELECT query extracts the kind, position interval, lane, speed and active time of RDF Constraint instances. These rows become Python constraints for graph pruning. The current query retrieves already-computed restrictions; it does not infer new rules. A* uses the same delivered Python constraints directly.'],
 reachable:['05','Reachable regions','Bounded acceleration and adjacent lane moves generate future sampled states. Restrictions remove invalid transitions and disconnected states. The road overlay projects raw and feasible states to their longitudinal positions and lanes for each future step. Filled strips summarize sampled extents; they are not a certified continuous safe area.'],
 planner:['06','Search & smooth','KARS uses dynamic programming and A* uses an admissible lower bound on the same constrained graph. Lane-ending corridor candidates are scored using progress, acceleration, lane changes and a margin proxy. SLSQP smooths the selected path; validation can retain the discrete path.'],
 actuation:['07','Execute & observe','The tracker sends bounded speed commands and one adjacent lane request to SUMO. It retains lane commitments during replanning. Known same-lane followers do not block forward escape through their inflated margins; their occupancy still guards lane transitions. SUMO controls their following safety. Measured motion returns to sensing on the next simulation step.']};
function pipelineActive(){return ['kars','kars_delay'].includes(currentRun()?.manifest.algorithm||parameters.algorithm);}
function graphConstraintFacts(){
 const recorded=frame.pipeline?.rdf_groups?.['Planner constraints'];
 if(recorded?.length)return recorded;
 const sources=new Set(),facts=[];
 for(const [index,c] of (frame.constraints||[]).entries()){
  if(sources.has(c.source))continue;
  sources.add(c.source);
  for(const predicate of ['source','kind','start','end','lane','speed','begin','finish']){
   if(c[predicate]!==undefined)facts.push({subject:'frame_constraint_'+index,predicate,object:c[predicate]});
  }
 }
 return facts;
}
function renderGraphEvidence(){
 const p=frame.pipeline||{},constraints=graphConstraintFacts();
 const relationships=Object.entries(p.rdf_groups||{}).filter(([name])=>name!=='Planner constraints').flatMap(([,facts])=>facts);
 const samples=relationships.length?relationships:p.rdf_samples||[];
 const constraintNote=p.rdf_groups?.['Planner constraints']?.length?'Recorded RDF restrictions.':'Restrictions from this saved frame, shown as triples.';
 const model=buildKnowledgeDiagram(frame,network);
 if(!model.nodes.length){$('logic-values').innerHTML='<p class="graph-note">Start or select a run to display its traffic knowledge graph.</p>';return;}
 const selected=model.nodes.find(n=>n.id===selectedGraphNode)||model.nodes[0];selectedGraphNode=selected.id;
 const rawOpen=$('kg-raw-facts')?.open;
 const constraintOpen=$('kg-raw-constraints')?.open;
 $('logic-values').innerHTML=`<div class="kg-figure"><div class="kg-figure-heading"><div><b>Traffic knowledge graph</b><span>Figure 6 structure · selected run at ${fmt(frame.time)} s</span></div><span class="small-tag">${model.nodes.length} nodes · ${model.edges.length} relations</span></div><p class="kg-context">Vehicle → lane → road, with lane boundaries, markings and speed-zone geometry. Click a node to inspect its data.</p><div class="kg-diagram-wrap">${diagramSVG(model,selectedGraphNode)}</div><div class="kg-legend"><span class="kg-entity-key">Vehicles / road</span><span class="kg-lane-key">Lanes / geometry</span><span class="kg-feature-key">Traffic features</span><span class="kg-value-key">Observed values</span></div><div class="kg-selection"><b>${escapeHTML(selected.label)}</b><span>${escapeHTML(selected.detail)}</span><pre>${escapeHTML(JSON.stringify(selected.facts,null,2))}</pre></div><p class="kg-reference">Reference: the supplied base paper, Figure 6(a), “Static traffic knowledge scenario.” R0 and each lane group combine the in/out network segments; select them to see their member IDs. This projection uses the scenario’s actual limits and intervals. SUMO lane 0 is rightmost; lane 2 is leftmost. Vehicle speeds are current observations. Crosswalk speed is a simulated advisory. ${pipelineActive()?(model.recorded?'Relationships come from recorded RDF and the selected frame.':'Legacy view reconstructed from the selected frame and network.'):'A* uses these constraints directly; RDF conversion is bypassed.'}</p></div>`+
  (constraints.length?`<details id="kg-raw-constraints" class="kg-raw" ${constraintOpen?'open':''}><summary>Planner constraint triples · ${constraints.length} facts</summary><p class="graph-note">${constraintNote}</p><pre class="stage-code">${escapeHTML(JSON.stringify(constraints,null,2))}</pre></details>`:'')+
  (samples.length?`<details id="kg-raw-facts" class="kg-raw" ${rawOpen?'open':''}><summary>All recorded relationship samples · ${samples.length} facts</summary><pre class="stage-code">${escapeHTML(JSON.stringify(samples,null,2))}</pre></details>`:'');
}
function selectGraphNode(event){const node=event.target.closest('[data-kg-node]');if(!node)return;selectedGraphNode=node.dataset.kgNode;renderGraphEvidence();}
$('logic-values').addEventListener('click',selectGraphNode);
$('logic-values').addEventListener('keydown',event=>{if(event.target.closest('[data-kg-node]')&&['Enter',' '].includes(event.key)){event.preventDefault();selectGraphNode(event);}});
function stageValues(key){
 const p=frame.pipeline||{},s=frame.sensing||{},d=frame.diagnostics||{},c=currentRun()?.manifest.config||{};
 const samples=(s.observations||[]).slice(0,8);
 const content={sensing:JSON.stringify({range_m:s.range??c.sensor_range,local_ids:s.local_ids,remote_ids:s.remote_ids,packet_time:s.packet_time,observations:samples},null,2),ontology:`Vehicle — locatedAt → Lane
Vehicle — hasSpeed → numeric speed
Lane — isOn → Road
Lane — hasLeftLane / hasRightLane → Lane
TrafficLight — hasCurrentColor → signal state
Constraint — kind / start / end / lane / speed / begin / finish`,graph:JSON.stringify(p.rdf_groups||p.rdf_samples||[],null,2),sparql:p.query_used?(p.query||'Query not recorded in this legacy run.')+`

RESULT ROWS
`+JSON.stringify(p.query_rows||[],null,2):'A*: RDF and SPARQL are bypassed. Delivered constraints feed adjustment directly.',reachable:JSON.stringify({raw:d.raw_nodes??frame.raw?.length,feasible:d.feasible_nodes??frame.adjusted?.length,layers:d.layers,rejection_reasons:d.rejection_reasons},null,2),planner:JSON.stringify({algorithm:currentRun()?.manifest.algorithm,solver:d.solver,selected_lane:frame.selected_lane,selected_cost:d.selected_cost,smoothing:d.optimization_status},null,2),actuation:JSON.stringify({commands:frame.commands,measured_speed:frame.ego?.speed,measured_acceleration:frame.ego?.acceleration,emergency:frame.emergency,controlled_stop:frame.controlled_stop,reason:frame.emergency_reason||frame.control_reason},null,2)};
 return content[key]||'Awaiting data.';
}
function renderStageDetail(key){
 if(key==='graph'){
  renderGraphEvidence();
 }else{
  $('logic-values').innerHTML=(key==='graph'?'<p class="graph-note">This saved run contains legacy RDF samples. Start a new KARS run to record lane boundaries, markings, speed zones and complete constraint examples.</p>':'')+'<pre class="stage-code">'+escapeHTML(stageValues(key))+'</pre>';
 }
}
function showStage(key){openLogicKey=key;$('logic-title').textContent=stageInfo[key][1];$('logic-description').textContent=stageInfo[key][2];renderStageDetail(key);if(!$('logic-dialog').open)$('logic-dialog').showModal();}
function renderKnowledgeWorkspace(){
 $('knowledge-flow').closest('.knowledge-workspace').hidden=!!network.city;
 const active=pipelineActive(),p=frame.pipeline||{},s=frame.sensing||{},d=frame.diagnostics||{};
 const stats={sensing:`${s.local_ids?.length??frame.local_vehicles??0} local · ${s.remote_ids?.length??frame.remote_vehicles??0} IoT`,ontology:'Vehicle · Lane · Constraint',graph:active?`${p.dynamic_triples??frame.triples??0} dynamic facts`:'Bypassed by A*',sparql:active?`${fmt(frame.query_ms,2)} ms · ${frame.constraints?.length??0} rows`:'Direct restrictions',reachable:`${frame.raw?.length??0} → ${frame.adjusted?.length??0} states`,planner:d.solver|| (active?'Dynamic programming':'A*'),actuation:frame.emergency?'Braking / waiting':`Target ${fmt(frame.commands?.command_speed*3.6)} km/h`};
 $('knowledge-flow').innerHTML=stageKeys.map(key=>`<button class="flow-stage ${!active&&['ontology','graph','sparql'].includes(key)?'bypassed':''}" data-help="${key}"><small>${stageInfo[key][0]}</small><b>${stageInfo[key][1]}</b><span>${escapeHTML(stats[key])}</span><i>Details ↗</i></button>`).join('');
 $('pipeline-timestamp').textContent=frame.ego?`Sensor ${fmt(frame.time)} s · plan ${fmt(frame.plan_time)} s`:'Awaiting observations';
}

init();
