import test from 'node:test';
import assert from 'node:assert/strict';
import {interpolateActors} from '../simulation_ui/motion.js';
const sample=(at,x,heading=90)=>({at,frame:{vehicles:[{vehicle_id:'ego',x,y:0,speed:10,heading}]}});
test('movement spans the full poll interval instead of freezing after 220 ms',()=>{
  const samples=[sample(0,0),sample(500,5),sample(1000,10)];
  assert.equal(interpolateActors(samples,250)[0].x,2.5);
  assert.equal(interpolateActors(samples,400)[0].x,4);
  assert.equal(interpolateActors(samples,750)[0].x,7.5);
});
test('heading interpolates across north using the shortest angle',()=>{
  assert.equal(interpolateActors([sample(0,0,359),sample(500,5,1)],250)[0].heading,0);
});
test('network stalls clamp to measured positions without forward extrapolation',()=>{
  assert.deepEqual(interpolateActors([],100),[]);
  assert.equal(interpolateActors([sample(0,0),sample(500,5)],2000)[0].x,5);
});
test('lane changes steer the body along a smooth measured-endpoint curve',()=>{
 const samples=[{at:0,frame:{vehicles:[{vehicle_id:'ego',x:0,y:0,heading:90,speed:10,road_id:'in',lane_id:'in_0'}]}},
 {at:1000,frame:{vehicles:[{vehicle_id:'ego',x:20,y:3.2,heading:90,speed:10,road_id:'in',lane_id:'in_1'}]}}];
 const mid=interpolateActors(samples,500)[0];
 const yaw=mid.heading*Math.PI/180,axle=4.7*.78;
 assert(Math.abs((mid.x-Math.sin(yaw)*axle)-(10-axle))<1e-6);
 assert(Math.abs((mid.y-Math.cos(yaw)*axle)-1.6)<1e-6);
 assert(mid.heading<90&&mid.heading>70);
 const first=interpolateActors(samples,1)[0],last=interpolateActors(samples,999)[0];
 assert(Math.abs(first.heading-90)<.1);assert(Math.abs(last.heading-90)<.1);
 assert.equal(interpolateActors(samples,1000)[0].y,3.2);
});

test('measured elevations interpolate through an underpass ramp',()=>{
 const a=sample(0,0),b=sample(500,5);a.frame.vehicles[0].z=0;b.frame.vehicles[0].z=4;
 assert.equal(interpolateActors([a,b],250)[0].z,2);
});


test('reverse parking keeps vehicle heading instead of flipping to direction of travel',()=>{
 const a={at:0,frame:{vehicles:[{vehicle_id:'ego',x:20,y:20,z:0,speed:-.8,heading:180,road_id:'parking',length:4.7}]}},
 b={at:200,frame:{vehicles:[{vehicle_id:'ego',x:20,y:20.16,z:0,speed:-.8,heading:180,road_id:'parking',length:4.7}]}};
 const mid=interpolateActors([a,b],100)[0];assert.equal(mid.heading,180);assert.equal(mid.speed,-.8);assert(Math.abs(mid.y-20.08)<1e-8);
});

test('body heading remains continuous when a junction sample becomes the next interval',()=>{
 const samples=[90,120,150,180].map((heading,i)=>({at:i*200,frame:{vehicles:[{vehicle_id:'ego',x:i*2,y:i*i*.5,speed:8,heading,road_id:':junction',length:4.7}]}}));
 for(const t of [200,400]){
  const a=interpolateActors(samples,t-.001)[0],b=interpolateActors(samples,t+.001)[0];
  assert(Math.abs((b.heading-a.heading+540)%360-180)<.01);
  assert(Math.hypot(b.x-a.x,b.y-a.y)<.01);
 }
});

test('turning angular speed is continuous across measured frame boundaries',()=>{
 const samples=[90,104,140,151].map((heading,i)=>({at:i*200,frame:{vehicles:[{vehicle_id:'ego',x:i*2,y:i*i*.2,speed:8,heading,road_id:':turn',length:4.7}]}}));
 const h=t=>interpolateActors(samples,t)[0].heading;
 for(const t of [200,400]){const incoming=(h(t)-h(t-.01))/.01,outgoing=(h(t+.01)-h(t))/.01;assert(Math.abs(incoming-outgoing)<.001);}
});
