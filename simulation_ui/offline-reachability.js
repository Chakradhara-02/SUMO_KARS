import library from './offline-reachability.json' with {type:'json'};

export function motionDirections(frame,ego){
 const speed=ego.speed||0,gear=ego.gear??frame.city?.parking?.gear;
 if(frame.city?.parking?.complete||(gear==='P'&&Math.abs(speed)<.05))return [];
 if(speed<-.05||(Math.abs(speed)<.05&&gear==='R'))return [-1];
 if(speed>.05)return [1];
 return gear==='D'?[1]:[1,-1];
}
// Pure lookup and rigid transform: no simulation, road or actor filtering here.
export function offlineReachability(frame,ego){
 if(!ego)return {points:[],branches:[],metadata:{model:library.model}};
 const directions=motionDirections(frame,ego),h=ego.heading*Math.PI/180,f={x:Math.sin(h),y:Math.cos(h)},n={x:-f.y,y:f.x};
 const points=[],branches=[],bins=[];
 // This library was generated for the supplied ego vehicle, not arbitrary trucks.
 if(Math.abs((ego.length||4.7)-library.length)>.25)return {points,branches,metadata:{model:library.model,supported:false}};
 for(const direction of directions){
  const acceleration=direction*(ego.acceleration||0);
  const records=library.records.filter(r=>r.direction===direction);
  const speedBin=records.reduce((best,r)=>Math.abs(r.speed-Math.abs(ego.speed||0))<Math.abs(best.speed-Math.abs(ego.speed||0))?r:best).speed;
  const record=records.filter(r=>r.speed===speedBin).reduce((best,r)=>Math.abs(r.acceleration-acceleration)<Math.abs(best.acceleration-acceleration)?r:best);
  bins.push({direction,speed:record.speed,acceleration:record.acceleration});
  for(const branch of record.branches){const transformed=branch.points.map(([time,x,y,heading,speed])=>({x:ego.x+f.x*x+n.x*y,y:ego.y+f.y*x+n.y*y,z:ego.z||0,time:(frame.time||0)+time,heading:(ego.heading+heading-90+360)%360,speed,direction,offline:true}));points.push(...transformed.slice(1));branches.push({...branch,direction,points:transformed});}
 }
 return {points,branches,metadata:{model:library.model,horizon:library.horizon,bins,supported:true,filtered_for_obstacles:false}};
}


// Forward plots track the front bumper. Reverse plots track the rear bumper,
// so valid backing positions are visible behind, rather than under, the car.
export function motionMarker(point,ego,direction=point.direction){
 if(direction!==-1)return point;
 const h=point.heading*Math.PI/180,length=ego?.length||4.7;
 return {...point,x:point.x-Math.sin(h)*length,y:point.y-Math.cos(h)*length,reference:'rear-bumper'};
}
