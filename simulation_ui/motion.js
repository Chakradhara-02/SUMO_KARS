const actorIndexes=new WeakMap();
function indexed(sample){if(!sample)return new Map();let map=actorIndexes.get(sample);if(!map){map=new Map((sample.frame.vehicles||[]).map(v=>[v.vehicle_id,v]));actorIndexes.set(sample,map);}return map;}
const angularDelta=(a,b)=>((b-a+540)%360)-180;
function rearAxle(actor){const h=actor.heading*Math.PI/180,offset=actor.rear_axle_offset??(actor.length||4.7)*.78;return{x:actor.x-Math.sin(h)*offset,y:actor.y-Math.cos(h)*offset};}
const monotoneSlope=(a,b)=>a*b>0?2*a*b/(a+b):0;
function bodyHeading(p,v,previous,next,t,left,right,before,after){
 const dt=Math.max(1,right.at-left.at),change=angularDelta(p.heading,v.heading),slope=change/dt;
 const monotone=(a,b)=>a*b>0?2*a*b/(a+b):0;
 const m0=previous?monotone(angularDelta(previous.heading,p.heading)/Math.max(1,left.at-before.at),slope)*dt:change;
 const m1=next?monotone(slope,angularDelta(v.heading,next.heading)/Math.max(1,after.at-right.at))*dt:change;
 return p.heading+(t*t*t-2*t*t+t)*m0+(-2*t*t*t+3*t*t)*change+(t*t*t-t*t)*m1;
}
// Interpolate measured frames only; no unobserved future motion is invented.
export function interpolateActors(samples, time) {
  if(!samples.length)return [];
  let left=samples[0],right=samples.at(-1),leftIndex=0;
  if(time<=left.at)return left.frame.vehicles||[];
  for(let i=1;i<samples.length;i++)if(samples[i].at>=time){left=samples[i-1];right=samples[i];leftIndex=i-1;break;}
  const ratio=Math.max(0,Math.min(1,(time-left.at)/(right.at-left.at||1)));
  const prior=indexed(left),before=indexed(samples[leftIndex-1]),after=indexed(samples[leftIndex+2]);
  return (right.frame.vehicles||[]).map(v=>{
    const p=prior.get(v.vehicle_id);if(!p)return v;
    const discrete=ratio<.5?p:v;
    const telemetry={signals:discrete.signals,indicator_reason:discrete.indicator_reason};
    const z=(p.z||0)+((v.z||0)-(p.z||0))*ratio;
    const angle=((v.heading-p.heading+540)%360)-180;
    const speed=p.speed+(v.speed-p.speed)*ratio;
    const measuredHeading=bodyHeading(p,v,before.get(v.vehicle_id),after.get(v.vehicle_id),ratio,left,right,samples[leftIndex-1],samples[leftIndex+2]);
    const distance=Math.hypot(v.x-p.x,v.y-p.y);
    if((p.road_id&&v.road_id||p.speed<0||v.speed<0)&&distance>.0001&&ratio>0&&ratio<1){
      // Hermite tangents follow the observed headings. Body yaw follows the
      // curve tangent, so lateral lane-change displacement has visible steering.
      const a=p.heading*Math.PI/180,b=v.heading*Math.PI/180,t=ratio;
      // Interpolate rear axles, then reconstruct the front bumper. Rotation about
      // the measured front bumper makes the rear of the car visibly skate sideways.
      const wheelbase=v.rear_axle_offset??(v.length||4.7)*.78;
      const p0=rearAxle(p),p1=rearAxle(v),direction=p.speed<-.01||v.speed<-.01?-1:1;
      const span=Math.hypot(p1.x-p0.x,p1.y-p0.y);
      let m0={x:Math.sin(a)*span*direction,y:Math.cos(a)*span*direction},m1={x:Math.sin(b)*span*direction,y:Math.cos(b)*span*direction};
      const previous=before.get(v.vehicle_id);
      const next=after.get(v.vehicle_id);
      // Central secants keep lane-change steering continuous across sample seams.
      const duration=Math.max(1,right.at-left.at),slope={x:(p1.x-p0.x)/duration,y:(p1.y-p0.y)/duration};
      if(previous){const q=rearAxle(previous),dt=Math.max(1,left.at-samples[leftIndex-1].at);m0={x:monotoneSlope((p0.x-q.x)/dt,slope.x)*duration,y:monotoneSlope((p0.y-q.y)/dt,slope.y)*duration};}
      if(next){const q=rearAxle(next),dt=Math.max(1,samples[leftIndex+2].at-right.at);m1={x:monotoneSlope(slope.x,(q.x-p1.x)/dt)*duration,y:monotoneSlope(slope.y,(q.y-p1.y)/dt)*duration};}
      const h0=2*t**3-3*t*t+1,h1=t**3-2*t*t+t,h2=-2*t**3+3*t*t,h3=t**3-t*t;
      const x=h0*p0.x+h1*m0.x+h2*p1.x+h3*m1.x,y=h0*p0.y+h1*m0.y+h2*p1.y+h3*m1.y;
      const dx=(6*t*t-6*t)*p0.x+(3*t*t-4*t+1)*m0.x+(-6*t*t+6*t)*p1.x+(3*t*t-2*t)*m1.x;
      const dy=(6*t*t-6*t)*p0.y+(3*t*t-4*t+1)*m0.y+(-6*t*t+6*t)*p1.y+(3*t*t-2*t)*m1.y;
      let yaw=Math.atan2(dx*direction,dy*direction);
      const baseline=measuredHeading*Math.PI/180,limit=(direction<0?0:p.road_id===v.road_id&&Math.abs(angle)<12?14:2)*Math.PI/180,diff=Math.atan2(Math.sin(yaw-baseline),Math.cos(yaw-baseline));
      // A tangent correction must vanish at sample boundaries. Otherwise each
      // incoming packet changes the body angle abruptly during a junction turn.
      yaw=baseline+Math.max(-limit,Math.min(limit,diff))*16*t*t*(1-t)*(1-t);
      return {...v,...telemetry,x:x+Math.sin(yaw)*wheelbase,y:y+Math.cos(yaw)*wheelbase,z,
        heading:(yaw*180/Math.PI+360)%360,speed};
    }
    return {...v,...telemetry,z,x:p.x+(v.x-p.x)*ratio,y:p.y+(v.y-p.y)*ratio,
      heading:(measuredHeading+360)%360,speed};
  });
}
