import {axes,center,createReachabilityValidator,projectOfflineReachability} from './reachability-constraints.js';
import {offlineReachability,motionDirections} from './offline-reachability.js';
import {cityTrajectoryPoints} from './city-overlays.js';

const dot=(a,b)=>a.x*b.x+a.y*b.y;
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
function project(p,a,b){const dx=b.x-a.x,dy=b.y-a.y,u=clamp(((p.x-a.x)*dx+(p.y-a.y)*dy)/(dx*dx+dy*dy||1),0,1);return {distance:Math.hypot(p.x-a.x-dx*u,p.y-a.y-dy*u),u};}

export function chooseStableCandidate(candidates,previous){
 if(!candidates.length)return null;
 const best=[...candidates].sort((a,b)=>a.cost-b.cost)[0];
 if(!previous)return best;
 const incumbent=candidates.find(b=>b.direction===previous.direction&&b.profile===previous.profile&&b.steering===previous.steering&&b.acceleration===previous.acceleration&&b.targetSpeed===previous.targetSpeed);
 // Only currently feasible candidates can be retained. A meaningful cost
 // improvement or an invalid incumbent changes the selected motion immediately.
 return incumbent&&incumbent.cost<=best.cost+Math.max(.6,Math.abs(best.cost)*.06)?incumbent:best;
}

// Every selected sample has a branch/parent identity; the blue path is never
// sourced from a separate geometry after reachable-set selection.
function finishReachability(branches,best,offline,directions,horizon,mode='online'){
 for(const [index,b]of branches.entries()){
  b.id='candidate_'+index;
  b.points=b.points.map((p,i)=>({...p,direction:p.direction??b.direction,id:b.id+':'+i,branch_id:b.id,parent_id:i?b.id+':'+(i-1):null}));
 }
 const safe=branches.flatMap(b=>b.points.filter((p,i)=>i>0&&!p.unsafe)),unsafe=branches.flatMap(b=>b.points.filter(p=>p.unsafe));
 const selected=(best?.points||[]).filter(p=>!p.unsafe),selectedEndpoint=selected.at(-1)||null;
 // A hold state is still a feasible member of the set.
 if(selectedEndpoint&&!safe.some(p=>p.id===selectedEndpoint.id))safe.push(selectedEndpoint);
 return {safe,unsafe,branches,selected,selectedEndpoint,selectedBranchId:best?.id??null,offline:offline.points,offlineUnsafe:offline.rejected||[],offlineBranches:offline.branches,offlineRaw:offline.rawPoints||offline.points,offlineMetadata:offline.metadata,directions,horizon,mode,
  optimization:{method:mode==='parking'?'checked parking speed-profile search':'bounded bicycle candidate search',cost:best?.cost??null,complete:!!best?.complete,direction:best?.direction,profile:best?.profile,steering:best?.steering,acceleration:best?.acceleration,targetSpeed:best?.targetSpeed}};
}

function parkingReachability(frame,ego,actors,offline,directions,validate,options){
 const parking=frame.city.parking,horizon=3,dt=.1;
 const direction=directions[0]??(parking.gear==='R'?-1:1),gear=direction<0?'R':'D';
 const origin={x:ego.x,y:ego.y,z:ego.z||0,heading:ego.heading,time:frame.time,speed:ego.speed||0,direction,gear};
 const input=parking.remaining_path?.length?parking.remaining_path:parking.path||[];
 // Match a segment, heading and gear, not merely the nearest vertex of a
 // manoeuvre which may pass through the same aisle in both directions.
 let nearest=null;
 for(let i=1;i<input.length;i++){
  const a=input[i-1],b=input[i];if(a.gear&&a.gear!==gear||b.gear&&b.gear!==gear)continue;
  const q=project(ego,a,b),error=Math.abs(((a.heading-ego.heading+540)%360)-180),score=q.distance+error*.025;
  if(!nearest||score<nearest.score)nearest={...q,score,index:i};
 }
 const reference=[origin];
 if(nearest){
  const a=input[nearest.index-1],b=input[nearest.index],u=nearest.u;
  const projected={...a,x:a.x+(b.x-a.x)*u,y:a.y+(b.y-a.y)*u,heading:(a.heading+(((b.heading-a.heading+540)%360)-180)*u+360)%360};
  if(Math.hypot(projected.x-ego.x,projected.y-ego.y)>.05)reference.push(projected);
  for(const p of input.slice(nearest.index)){if(p.gear&&p.gear!==gear)break;if(Math.hypot(p.x-reference.at(-1).x,p.y-reference.at(-1).y)>.01)reference.push(p);}
 }
 const segments=[];let total=0;
 for(let i=1;i<reference.length;i++){const a=reference[i-1],b=reference[i],distance=Math.hypot(b.x-a.x,b.y-a.y);segments.push({a,b,begin:total,end:total+distance});total+=distance;}
 const pose=station=>{for(const segment of segments){if(station<=segment.end+1e-8){const u=clamp((station-segment.begin)/(segment.end-segment.begin),0,1),{a,b}=segment;return {x:a.x+(b.x-a.x)*u,y:a.y+(b.y-a.y)*u,z:a.z??ego.z??0,heading:(a.heading+(((b.heading-a.heading+540)%360)-180)*u+360)%360};}}return reference.at(-1);};
 const branches=[];
 for(const target of [0,direction<0?.45:.7,direction<0?.85:1.4]){
  const points=[{...origin}];let station=0,speed=Math.abs(ego.speed||0),cost=0,reason='',blocked=[],previous=origin,previousA=0;
  for(let step=1;step<=30;step++){
   const desired=Math.min(target,Math.sqrt(Math.max(0,2*.7*(total-station))));
   const nextSpeed=clamp(desired,Math.max(0,speed-.7*dt),speed+.5*dt),advance=Math.min(Math.max(0,total-station),(speed+nextSpeed)/2*dt);
   station+=advance;const p={...pose(station),time:frame.time+step*dt,speed:station>=total-1e-6?0:direction*nextSpeed,direction,gear,blocked_by:[]};
   const check=validate(previous,p);
   if(!check.valid){points.push(check.point);reason=check.reason;blocked=check.blocked_by;break;}
   Object.assign(p,check.point);
   const acceleration=(Math.abs(p.speed)-speed)/dt;cost+=dt*(.3*acceleration**2+.06*((acceleration-previousA)/dt)**2);previousA=acceleration;
   points.push(p);previous=p;speed=Math.abs(p.speed);
  }
  cost+=4*(total-station);
  branches.push({points,reason,blocked_by:[...new Set(blocked)],complete:points.length===31&&!reason,cost,progress:station,acceleration:target===0?-4:0,steering:0,profile:'parking_path',direction,targetSpeed:target});
 }
 const feasible=branches.filter(b=>b.complete),best=chooseStableCandidate(feasible.length?feasible:branches.filter(b=>b.targetSpeed===0),options.previousSelection);
 return finishReachability(branches,best,offline,directions,horizon,'parking');
}

// Online sampled reachability: each branch integrates controls from the currently
// displayed state. Control samples are not an offline geometric reachable set.
export function localReachability(frame,actors,network,options={}){
 const ego=actors.find(a=>a.vehicle_id==='ego');
 if(!ego)return {safe:[],unsafe:[],branches:[],selected:[],offline:[],offlineUnsafe:[],directions:[],horizon:3,mode:'online'};
 const length=ego.length||4.7,width=ego.width||1.8,wheelbase=length*.6;
 const horizon=3,dt=.1,initialSpeed=Math.abs(ego.speed||0);
 const directions=motionDirections(frame,ego),validate=createReachabilityValidator(frame,ego,actors,network),offline=options.includeOffline===false?{points:[],rejected:[],branches:[],rawPoints:[],metadata:{disabled:true}}:projectOfflineReachability(offlineReachability(frame,ego),validate);
 if(frame.city?.parking?.active)return parkingReachability(frame,ego,actors,offline,directions,validate,options);
 const guidance=cityTrajectoryPoints(frame,ego,{guidance:false});
 const routeError=p=>{let best=Infinity;for(let i=1;i<guidance.length;i++)best=Math.min(best,project(p,guidance[i-1],guidance[i]).distance);if(Number.isFinite(best))return best;const [,n]=axes(ego.heading);return Math.abs(dot({x:p.x-ego.x,y:p.y-ego.y},n));};
 const branches=[],origin={x:ego.x,y:ego.y,z:ego.z||0,time:frame.time,heading:ego.heading,speed:ego.speed||0};
 for(const direction of directions)for(const targetA of [-4,0,2])for(const targetSteer of [-.28,-.18,-.09,0,.09,.18,.28])for(const profile of (targetSteer===0?['arc']:['arc','lane_change'])){
  let body=center(origin,length,width),yaw=ego.heading*Math.PI/180,speed=initialSpeed,steer=0,acceleration=clamp(direction*(ego.acceleration||0),-4,2),cost=0,clearance=Infinity;
  const points=[origin];let reason='',blocked_by=[],previous=origin;
  for(let step=1;step<=horizon/dt;step++){
   acceleration+=clamp(targetA-acceleration,-4*dt,4*dt);
   const limit=direction<0?1.4:Math.min(22.2,ego.speed_limit||13.9);
   let nextSpeed=Math.max(0,speed+acceleration*dt);
   if(nextSpeed>limit)nextSpeed=speed>limit?Math.max(limit,speed-4*dt):limit;
   const steerGoal=profile==='lane_change'?targetSteer*Math.cos(Math.PI*(step-1)*dt/horizon):targetSteer;
   steer+=clamp(steerGoal-steer,-.18*dt,.18*dt);
   // Limit lateral acceleration and steering rate; integrate at midpoint yaw.
   const boundedSteer=clamp(steer,-Math.atan(2.5*wheelbase/Math.max(1,nextSpeed**2)),Math.atan(2.5*wheelbase/Math.max(1,nextSpeed**2)));
   const v=(speed+nextSpeed)/2,dYaw=direction*v/wheelbase*Math.tan(boundedSteer)*dt,mid=yaw+dYaw/2;
   body={...body,x:body.x+direction*v*Math.sin(mid)*dt,y:body.y+direction*v*Math.cos(mid)*dt};yaw+=dYaw;
   const heading=(yaw*180/Math.PI+360)%360,[f,n]=axes(heading),elapsed=step*dt;
   const p={x:body.x+f.x*length/2,y:body.y+f.y*length/2,z:body.z,time:frame.time+elapsed,heading,speed:direction*nextSpeed,direction,gear:direction<0?'R':'D',blocked_by:[]};
   const check=validate(previous,p);clearance=Math.min(clearance,check.clearance);
   if(!check.valid){reason=check.reason;blocked_by=check.blocked_by;points.push(check.point);break;}
   Object.assign(p,check.point);body.z=p.z;body.heading=heading;
   const lateralAcceleration=nextSpeed**2/wheelbase*Math.tan(boundedSteer);
   cost+=dt*(.12*acceleration**2+.3*lateralAcceleration**2+.65*routeError(p)**2+.06*(nextSpeed-Math.min(ego.speed_limit||13.9,Math.max(6,initialSpeed)))**2);
   points.push(p);previous=p;speed=nextSpeed;
  }
  const progress=Math.hypot(previous.x-ego.x,previous.y-ego.y),complete=points.length===31&&!reason;
  cost+=.4*(targetA-(ego.acceleration||0))**2+3*targetSteer**2+(Number.isFinite(clearance)?2/Math.max(.4,clearance+.5):0)-1.2*progress;
  if(direction<0)cost+=10;
  branches.push({points,reason,blocked_by:[...new Set(blocked_by)],complete,cost,progress,acceleration:targetA,steering:targetSteer,profile,direction});
 }
 const complete=branches.filter(b=>b.complete);
 // A blocked horizon uses a bounded braking prefix, never an unsafe extension.
 const candidates=complete.length?complete:branches.filter(b=>b.acceleration===-4);
 const best=complete.length?chooseStableCandidate(candidates,options.previousSelection):candidates.sort((a,b)=>Math.abs(a.points.at(-1)?.speed??0)-Math.abs(b.points.at(-1)?.speed??0)||b.points.length-a.points.length)[0];
 return finishReachability(branches,best,offline,directions,horizon);
}
export function localHazardMessages(classes,includeOffline=true){return [...new Set(visibleUnsafeStates(classes,includeOffline).flatMap(p=>p.blocked_by||[]))].slice(0,3).map(id=>'Candidate blocked by '+id);}


export function visibleUnsafeStates(classes,includeOffline=true){
 const seen=new Set();return [...classes.unsafe,...(includeOffline?classes.offlineUnsafe||[]:[])].filter(p=>{const key=[Math.round(p.x*3),Math.round(p.y*3),p.rejection_kind].join('/');if(seen.has(key))return false;seen.add(key);return true;});
}
