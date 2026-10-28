import {createReachabilityValidator} from './reachability-constraints.js';
const empty=()=>({safe:[],unsafe:[],branches:[],selected:[],displaySelected:[],selectedEndpoint:null,offline:[],offlineUnsafe:[],directions:[],horizon:3,mode:'online',pending:true});

export function trimTrajectory(points,ego,time){
 if(!ego||points.length<2)return [];
 let nearest={distance:Infinity,index:0,u:0};
 for(let i=1;i<points.length;i++){
  const a=points[i-1],b=points[i],dx=b.x-a.x,dy=b.y-a.y,u=Math.max(0,Math.min(1,((ego.x-a.x)*dx+(ego.y-a.y)*dy)/(dx*dx+dy*dy||1))),distance=Math.hypot(ego.x-a.x-dx*u,ego.y-a.y-dy*u);
  if(distance<nearest.distance)nearest={distance,index:i,u};
 }
 if(nearest.distance>.75)return [];
 const future=points.slice(nearest.index).filter(p=>p.time>time+1e-6);
 if(!future.length)return [];
 const first=future[0],heading=ego.heading*Math.PI/180,direction=first.direction??1;
 if((first.x-ego.x)*Math.sin(heading)*direction+(first.y-ego.y)*Math.cos(heading)*direction<-.15)return [];
 return [{...points[nearest.index-1],x:ego.x,y:ego.y,z:ego.z||0,heading:ego.heading,speed:ego.speed||0,time},...future];
}
function planFrame(frame){const c=frame.city||{};return {time:frame.time,ego:frame.ego,ego_trace:frame.ego_trace,city:{parking:c.parking,trip:c.trip?{edges:c.trip.edges,parking_lot:c.trip.parking_lot}:undefined,next_signal:c.next_signal,route_shape:c.route_shape},city_reachability:{trajectory:frame.city_reachability?.trajectory,reference_path:frame.city_reachability?.reference_path},sensing:{range:frame.sensing?.range}};}
function actorState(a){return {vehicle_id:a.vehicle_id,x:a.x,y:a.y,z:a.z,heading:a.heading,speed:a.speed,acceleration:a.acceleration,length:a.length,width:a.width,lane_id:a.lane_id,road_id:a.road_id,speed_limit:a.speed_limit,gear:a.gear};}

export class ReachabilityRuntime{
 constructor({createWorker=()=>new Worker('/reachability.worker.bundle.js'),now=()=>performance.now(),interval=125,maxAge=350}={}){
  this.createWorker=createWorker;this.now=now;this.interval=interval;this.maxAge=maxAge;this.generation=0;this.serial=0;this.current=empty();this.lastSent=-Infinity;this.stats={submitted:0,completed:0,dropped:0,computeMs:0};
 }
 receive(message){
  if(!this.inFlight||message.id!==this.inFlight.id||message.generation!==this.generation){this.stats.dropped++;return;}
  const job=this.inFlight;this.inFlight=null;
  if(message.type!=='result'||this.now()-job.sentAt>this.maxAge&&this.latestStateKey!==job.stateKey){this.stats.dropped++;this.stats.lastError=message.error;this.forceNext=true;this.lastSubmittedSignature=null;return;}
  this.current={...message.result,_version:message.id,_frameTime:job.frameTime,_sentAt:job.sentAt,_signature:job.signature,pending:false};this.stats.completed++;this.stats.computeMs=message.computeMs;this.guardKey=null;
 }
 sample(frame,actors,network,{runKey='',includeOffline=true,includeCandidates=true,enabled=true}={}){
  if(!enabled)return {...empty(),disabled:true};
  const ego=actors.find(a=>a.vehicle_id==='ego');if(!ego||!frame.city)return empty();
  if(this.failed)return {...empty(),unavailable:true};
  const mode=String(!!frame.city.parking?.active)+'/'+(ego.gear??frame.city.parking?.gear??'')+'/'+(frame.city.parking?.stage??'')+'/'+((ego.speed||0)<-.05?'R':'D');
  const context=runKey+'/'+mode,seek=frame.time<this.lastInputTime;this.lastInputTime=frame.time;
  if(!this.worker){try{this.worker=this.createWorker();this.worker.onmessage=e=>this.receive(e.data);this.worker.onerror=()=>{this.failed=true;this.current=empty();this.current.unavailable=true;this.inFlight=null;};}catch{const r=empty();r.unavailable=true;return r;}}
  if(this.network!==network||this.context!==context||seek){const changed=this.network!==network;this.network=network;this.context=context;this.generation++;this.inFlight=null;this.current=empty();this.guardKey=null;this.lastSent=-Infinity;this.lastCheck=-Infinity;this.lastSubmittedSignature=null;this.worker.postMessage({type:'context',generation:this.generation,...(changed?{network}: {})});}
  this.latestStateKey=[frame.time,ego.x,ego.y,ego.heading,actors.length].join('/');
  const now=this.now(),changedOffline=this.includeOffline!==includeOffline||this.includeCandidates!==includeCandidates;this.includeOffline=includeOffline;this.includeCandidates=includeCandidates;
  if(!this.inFlight&&(now-(this.lastCheck??-Infinity)>=this.interval||changedOffline||this.forceNext)){
   let signature=[frame.time,ego.x,ego.y,ego.heading,ego.speed,ego.acceleration,actors.length,includeOffline,includeCandidates].join('/');
   for(const a of actors)if(a.vehicle_id!=='ego'&&Math.hypot(a.x-ego.x,a.y-ego.y)<50)signature+='/'+a.vehicle_id+':'+Math.round(a.x*2)+','+Math.round(a.y*2);
   this.lastSignature=signature;this.lastCheck=now;
   if(signature!==this.lastSubmittedSignature||this.forceNext){
    this.forceNext=false;this.lastSubmittedSignature=signature;
    const id=++this.serial,job={id,sentAt:now,frameTime:frame.time,signature,stateKey:this.latestStateKey};this.inFlight=job;this.lastSent=now;this.stats.submitted++;
    this.worker.postMessage({type:'plan',id,generation:this.generation,frame:planFrame(frame),actors:actors.map(actorState),includeOffline,includeCandidates});
   }
  }
  if(this.current.pending||now-this.current._sentAt>this.maxAge&&this.current._signature!==this.lastSignature)return {...empty(),pendingReason:this.current.pending?'starting':'stale'};
  const displaySelected=trimTrajectory(this.current.selected,ego,frame.time);
  const key=this.current._version+'/'+frame.time;
  if(key!==this.guardKey){
   const validate=createReachabilityValidator(frame,ego,actors,network);this.guardValid=true;
   for(let i=1;i<displaySelected.length;i++)if(!validate(displaySelected[i-1],displaySelected[i]).valid){this.guardValid=false;break;}
   this.guardKey=key;
  }
  if(!this.guardValid){this.forceNext=true;this.stats.guardFailures=(this.stats.guardFailures||0)+1;return {...empty(),pendingReason:'guard'};}
  return {...this.current,displaySelected,selectedEndpoint:displaySelected.at(-1)||null};
 }
 dispose(){this.worker?.terminate();this.worker=null;this.current=empty();}
}
