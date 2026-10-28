// Bridge the displayed (buffered) actor to the latest measured position before
// appending forecast states. This avoids an overlay starting ahead of the car.
export function cityTrajectoryPoints(frame,actor,{guidance=true}={}){
 if(!actor)return [];
 const points=[{x:actor.x,y:actor.y}],trace=frame.ego_trace||[];
 let closest=-1,distance=Infinity;
 for(let i=0;i<trace.length;i++){const d=Math.hypot(trace[i][0]-actor.x,trace[i][1]-actor.y);if(d<=distance){closest=i;distance=d;}}
 const heading=actor.heading*Math.PI/180,dx=Math.sin(heading),dy=Math.cos(heading);
 const append=p=>{const last=points.at(-1);if(Math.hypot(p.x-last.x,p.y-last.y)>.04)points.push(p);};
 if(closest>=0){
  const p=trace[closest];if((p[0]-actor.x)*dx+(p[1]-actor.y)*dy>=-.1)append({x:p[0],y:p[1]});
  for(const p of trace.slice(closest+1))append({x:p[0],y:p[1]});
 }
 const measured=frame.ego||actor,angle=measured.heading*Math.PI/180;
 const parking=frame.city?.parking;
 if(parking?.active){
  if(parking.complete)return points;
  const planned=parking.path||[];let closest=0,distance=Infinity;
  planned.forEach((p,i)=>{const d=Math.hypot(p.x-measured.x,p.y-measured.y);if(d<distance){distance=d;closest=i;}});
  for(const p of planned.slice(closest))append(p);
  return points;
 }
 const preview=frame.city_reachability||{},future=(preview.trajectory||[]).filter(p=>p.time>frame.time);
 if(future.length){for(const p of future)append(p);}
 if(guidance&&points.length<2){
  const reference=preview.reference_path||[];
  for(let i=0;i<reference.length;i++)if(i>0)append(reference[i]);
 }
 // Navigation and feasible motion are separate: a red light or missing forecast
 // must not erase the route. Prefer the connected route from the latest reroute.
 const route=frame.city?.route_shape||[];
 if(guidance&&route.length>1){
  const tail=points.at(-1);let near=0,d=Infinity;
  route.forEach((p,i)=>{const q=Math.hypot(p[0]-tail.x,p[1]-tail.y);if(q<d){d=q;near=i;}});
  // Avoid joining a forecast on another lane with a long diagonal shortcut.
  if(points.length<2||d<6)for(const p of route.slice(near+(points.length>1?1:0)))append({x:p[0],y:p[1],z:p[2]||0});
 }
 return points;
}

// Keep distinct time/lane states even when their ground positions coincide.
export function reachableClasses(preview={}){
 const origin=preview.origin,radius=preview.display_radius??45;
 const inside=p=>!origin||Math.hypot(p.x-origin.x,p.y-origin.y)<=radius;
 const reduce=points=>{const seen=new Set();return points.filter(p=>{const key=[Math.round(p.x),Math.round(p.y),Math.round(p.z||0)].join('/');if(!inside(p)||seen.has(key))return false;seen.add(key);return true;});};
 return {safe:reduce(preview.feasible||[]),unsafe:reduce((preview.raw||[]).filter(p=>p.collision===true).map(p=>({...p,...p.hazard_point})))};
}
export function frameReachability(frame={}){
 const ego=frame.ego;if(!ego)return {safe:[],unsafe:[]};
 const radius=frame.sensing?.range??120;
 const nearby=new Set((frame.vehicles||[]).filter(v=>v.vehicle_id!=='ego'&&Math.hypot(v.x-ego.x,v.y-ego.y)<=radius&&Math.abs((v.z||0)-(ego.z||0))<2.5).map(v=>v.vehicle_id));
 const city=frame.city_reachability;
 const source=city||{raw:(frame.raw||[]).map(p=>({...p,y:-8+p.lane*3.2,time:p.t,
  collision:p.valid===false&&(p.reasons||[]).some(r=>nearby.has(r)),blocked_by:(p.reasons||[]).filter(r=>nearby.has(r))})),
  feasible:(frame.adjusted||[]).map(p=>({...p,y:-8+p.lane*3.2,time:p.t}))};
 const classes=reachableClasses({...source,origin:ego,display_radius:Math.min(radius,45)});
 return {safe:classes.safe.filter(p=>p.time>=frame.time),unsafe:classes.unsafe.filter(p=>p.time>=frame.time&&(p.blocked_by||[]).some(id=>nearby.has(id)))};
}
export function hazardMessages(frame){
 const points=frameReachability(frame).unsafe,messages=[];
 for(const p of points)for(const id of p.blocked_by||[]){const text='Motion blocked by '+id;if(!messages.includes(text))messages.push(text);}
 return messages.slice(0,3);
}
export function unsafeLabels(points,maximum=4){
 const labels=[];
 for(const p of [...points].sort((a,b)=>a.time-b.time)){
  const text=(p.reasons||[]).filter(r=>r!=='Unsafe earlier transition')[0]||'No constraint-valid path to this state';
  if(labels.some(q=>q.text===text||Math.hypot(q.x-p.x,q.y-p.y)<8))continue;
  labels.push({...p,text});if(labels.length>=maximum)break;
 }
 return labels;
}
