// Bridge the displayed (buffered) actor to the latest measured position before
// appending forecast states. This avoids an overlay starting ahead of the car.
export function cityTrajectoryPoints(frame,actor){
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
 for(const p of frame.city_reachability?.trajectory||[]){
  if(p.time>frame.time&&(p.x-measured.x)*Math.sin(angle)+(p.y-measured.y)*Math.cos(angle)>=-1)append(p);
 }
 return points;
}
