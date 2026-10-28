const dot=(a,b)=>a.x*b.x+a.y*b.y;
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
export function axes(heading){const h=heading*Math.PI/180,f={x:Math.sin(h),y:Math.cos(h)};return [f,{x:-f.y,y:f.x}];}
export function center(p,length,width){const [f]=axes(p.heading);return {...p,x:p.x-f.x*length/2,y:p.y-f.y*length/2,length,width};}
export function conflict(a,b,margin=.25){
 const [af,an]=axes(a.heading),[bf,bn]=axes(b.heading),delta={x:b.x-a.x,y:b.y-a.y};
 return [af,an,bf,bn].every(axis=>Math.abs(dot(delta,axis))<a.length/2*Math.abs(dot(axis,af))+a.width/2*Math.abs(dot(axis,an))+b.length/2*Math.abs(dot(axis,bf))+b.width/2*Math.abs(dot(axis,bn))+margin);
}

const roadIndexes=new WeakMap(),CELL=20;
function roadIndex(network){
 let grid=roadIndexes.get(network);if(grid)return grid;
 grid=new Map();
 for(const lane of network.lanes||[])for(let i=1;i<lane.shape.length;i++){
  const a=lane.shape[i-1],b=lane.shape[i],dx=b[0]-a[0],dy=b[1]-a[1],width=lane.width||3.2,pad=width/2+.02;
  const segment={a,b,dx,dy,d2:dx*dx+dy*dy,width,speed:lane.speed,edge:lane.id?.replace(/_\d+$/,'')};
  for(let x=Math.floor((Math.min(a[0],b[0])-pad)/CELL);x<=Math.floor((Math.max(a[0],b[0])+pad)/CELL);x++)for(let y=Math.floor((Math.min(a[1],b[1])-pad)/CELL);y<=Math.floor((Math.max(a[1],b[1])+pad)/CELL);y++){
   const key=x+','+y;if(!grid.has(key))grid.set(key,[]);grid.get(key).push(segment);
  }
 }
 roadIndexes.set(network,grid);return grid;
}

// One swept-state validator is shared by online rollouts and the displayed
// projection of the immutable offline library.
export function createReachabilityValidator(frame,ego,actors,network){
 const length=ego.length||4.7,width=ego.width||1.8,range=frame.sensing?.range??120,parking=frame.city?.parking?.active,lot=frame.city?.trip?.parking_lot;
 const allowed=new Set([ego.road_id,...(frame.city?.trip?.edges||[])]),grid=network?roadIndex(network):null;
 const road=p=>{if(!network)return {ok:true,z:p.z,speed:ego.speed_limit??22.2};let best=null;
  const nearby=grid.get(Math.floor(p.x/CELL)+','+Math.floor(p.y/CELL))||[];
  for(const s of nearby){if(ego.road_id&&!s.edge?.startsWith(':')&&!allowed.has(s.edge))continue;const u=clamp(((p.x-s.a[0])*s.dx+(p.y-s.a[1])*s.dy)/(s.d2||1),0,1),distance=Math.hypot(p.x-s.a[0]-s.dx*u,p.y-s.a[1]-s.dy*u),z=(s.a[2]||0)+((s.b[2]||0)-(s.a[2]||0))*u;
   if(distance<=s.width/2+.02&&Math.abs(z-p.z)<1.5&&(!best||distance<best.distance))best={ok:true,distance,z,speed:s.speed??ego.speed_limit??13.9};
  }return best||{ok:false,z:p.z};};
 const others=actors.filter(v=>v.vehicle_id!=='ego'&&Math.hypot(v.x-ego.x,v.y-ego.y)<=range);
 if(parking)for(const slot of lot?.slots||[])if(slot.occupied)others.push({vehicle_id:'parked_'+slot.id,x:slot.front_x??slot.x,y:slot.front_y??slot.y,z:0,heading:slot.heading??180,length:4.7,width:1.8,speed:0});
 // Prepare fixed actor axes once; only their centers advance during rollout.
 const egoRadius=Math.hypot(length/2,width/2),margin=parking?.12:.25;
 const prepared=others.map(v=>{const [f,n]=axes(v.heading),l=v.length||4.7,w=v.width||1.8;return {id:v.vehicle_id,x:v.x-f.x*l/2,y:v.y-f.y*l/2,z:v.z||0,vx:f.x*(v.speed||0),vy:f.y*(v.speed||0),f,n,l:l/2,w:w/2,radius:Math.hypot(l/2,w/2)};});
 prepared.sort((a,b)=>(a.x-ego.x)**2+(a.y-ego.y)**2-((b.x-ego.x)**2+(b.y-ego.y)**2));
 const overlaps=(dx,dy,f,n,o)=>{
  const ff=Math.abs(dot(f,o.f)),fn=Math.abs(dot(f,o.n)),nf=Math.abs(dot(n,o.f)),nn=Math.abs(dot(n,o.n));
  return Math.abs(dx*f.x+dy*f.y)<length/2+o.l*ff+o.w*fn+margin&&
   Math.abs(dx*n.x+dy*n.y)<width/2+o.l*nf+o.w*nn+margin&&
   Math.abs(dx*o.f.x+dy*o.f.y)<o.l+length/2*ff+width/2*nf+margin&&
   Math.abs(dx*o.n.x+dy*o.n.y)<o.w+length/2*fn+width/2*nn+margin;
 };
 const reject=(p,reason,kind,ids=[])=>({valid:false,point:{...p,unsafe:true,valid:false,collision:kind==='vehicle',reason,reasons:[reason],rejection_kind:kind,blocked_by:ids},reason,blocked_by:ids,clearance:0});
 return (previous,next)=>{
  const steps=Math.max(3,Math.ceil(Math.hypot(next.x-previous.x,next.y-previous.y)/.5));let clearance=Infinity,result;
  for(let sub=1;sub<=steps;sub++){
   const u=sub/steps,p={...next,x:previous.x+(next.x-previous.x)*u,y:previous.y+(next.y-previous.y)*u,z:previous.z??ego.z??0,
    heading:(previous.heading+(((next.heading-previous.heading+540)%360)-180)*u+360)%360,time:previous.time+(next.time-previous.time)*u,speed:previous.speed+(next.speed-previous.speed)*u};
   const body=center(p,length,width),[f,n]=axes(p.heading),corners=[[-length/2,-width/2],[-length/2,width/2],[length/2,-width/2],[length/2,width/2]].map(([x,y])=>({x:body.x+f.x*x+n.x*y,y:body.y+f.y*x+n.y*y,z:p.z}));
   if(parking){if(lot?.bounds){const [xmin,ymin,xmax,ymax]=lot.bounds;if(corners.some(q=>q.x<xmin+.05||q.x>xmax-.05||q.y<ymin+.05||q.y>ymax-.05))return reject(p,'Parking boundary','parking_boundary');}}
   else {
    const support=road(p);p.z=support.z;
    if(!support.ok||corners.some(q=>!road({...q,z:p.z}).ok))return reject(p,'Road boundary or opposing carriageway','road_boundary');
    const limit=support.speed??ego.speed_limit??22.2;
    if(Math.abs(p.speed)>limit+.15&&Math.abs(p.speed)>=Math.abs(ego.speed||0)-.01)return reject(p,'Speed limit exceeded','speed_limit');
    const signal=frame.city?.next_signal,advance=dot({x:p.x-ego.x,y:p.y-ego.y},axes(ego.heading)[0]);
    if(signal){const color=signal.color?.toLowerCase(),elapsed=p.time-frame.time,remaining=signal.seconds??3;
     const forbidden=color==='r'?elapsed<remaining:color==='y'?elapsed<remaining+6:color==='g'?Number.isFinite(signal.seconds)&&elapsed>=remaining:false;
     if(forbidden&&advance>Math.max(0,signal.distance-3))return reject(p,color==='g'?'Green ends before stop-line crossing':'Red or amber stop line','signal');
    }
   }
   body.z=p.z;const elapsed=Math.max(0,p.time-frame.time),ids=[];
   for(const other of prepared){
    if(Math.abs(other.z-p.z)>2.5)continue;
    const dx=other.x+other.vx*elapsed-body.x,dy=other.y+other.vy*elapsed-body.y,distance2=dx*dx+dy*dy;
    const improve=clearance+length/2+other.l;
    if(!Number.isFinite(clearance)||improve>0&&distance2<improve*improve)clearance=Math.sqrt(distance2)-length/2-other.l;
    const radius=egoRadius+other.radius+Math.SQRT2*margin;
    if(distance2<radius*radius&&overlaps(dx,dy,f,n,other))ids.push(other.id);
   }
   if(ids.length)return reject(p,'Vehicle conflict: '+[...new Set(ids)].join(', '),'vehicle',[...new Set(ids)]);
   result={...p,valid:true,unsafe:false,collision:false,blocked_by:[]};
  }
  return {valid:true,point:result,reason:'',blocked_by:[],clearance};
 };
}

export function projectOfflineReachability(raw,validate){
 const points=[],rejected=[],branches=[];
 for(const [index,b]of raw.branches.entries()){
  const accepted=[b.points[0]];let rejection=null;
  for(const p of b.points.slice(1)){
   const check=validate(accepted.at(-1),p);
   if(!check.valid){rejection={...check.point,offline:true,id:'offline_'+index+':rejected'};rejected.push(rejection);break;}
   const sample={...check.point,offline:true};accepted.push(sample);points.push(sample);
  }
  branches.push({...b,points:accepted,rejection});
 }
 return {points,rejected,branches,rawPoints:raw.points,metadata:{...raw.metadata,display_filtered:true,raw_count:raw.points.length,rejected_branches:rejected.length}};
}
