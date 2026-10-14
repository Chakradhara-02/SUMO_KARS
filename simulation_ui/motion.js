// Interpolate measured frames only; no unobserved future motion is invented.
export function interpolateActors(samples, time) {
  if(!samples.length)return [];
  let left=samples[0],right=samples.at(-1);
  if(time<=left.at)return left.frame.vehicles||[];
  for(let i=1;i<samples.length;i++)if(samples[i].at>=time){left=samples[i-1];right=samples[i];break;}
  const ratio=Math.max(0,Math.min(1,(time-left.at)/(right.at-left.at||1)));
  const prior=new Map((left.frame.vehicles||[]).map(v=>[v.vehicle_id,v]));
  return (right.frame.vehicles||[]).map(v=>{
    const p=prior.get(v.vehicle_id);if(!p)return v;
    const angle=((v.heading-p.heading+540)%360)-180;
    const speed=p.speed+(v.speed-p.speed)*ratio;
    const distance=Math.hypot(v.x-p.x,v.y-p.y);
    if(p.road_id&&v.road_id&&distance>.05&&ratio>0&&ratio<1){
      // Hermite tangents follow the observed headings. Body yaw follows the
      // curve tangent, so lateral lane-change displacement has visible steering.
      const a=p.heading*Math.PI/180,b=v.heading*Math.PI/180,t=ratio;
      const m0={x:Math.sin(a)*distance,y:Math.cos(a)*distance},m1={x:Math.sin(b)*distance,y:Math.cos(b)*distance};
      const h0=2*t**3-3*t*t+1,h1=t**3-2*t*t+t,h2=-2*t**3+3*t*t,h3=t**3-t*t;
      const x=h0*p.x+h1*m0.x+h2*v.x+h3*m1.x,y=h0*p.y+h1*m0.y+h2*v.y+h3*m1.y;
      const dx=(6*t*t-6*t)*p.x+(3*t*t-4*t+1)*m0.x+(-6*t*t+6*t)*v.x+(3*t*t-2*t)*m1.x;
      const dy=(6*t*t-6*t)*p.y+(3*t*t-4*t+1)*m0.y+(-6*t*t+6*t)*v.y+(3*t*t-2*t)*m1.y;
      return {...v,x,y,heading:(Math.atan2(dx,dy)*180/Math.PI+360)%360,speed};
    }
    return {...v,x:p.x+(v.x-p.x)*ratio,y:p.y+(v.y-p.y)*ratio,
      heading:(p.heading+angle*ratio+360)%360,speed};
  });
}
