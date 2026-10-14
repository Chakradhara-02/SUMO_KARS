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
 assert(Math.abs(mid.x-10)<1e-6);assert(Math.abs(mid.y-1.6)<1e-6);
 assert(mid.heading<90&&mid.heading>70);
 const first=interpolateActors(samples,1)[0],last=interpolateActors(samples,999)[0];
 assert(Math.abs(first.heading-90)<.1);assert(Math.abs(last.heading-90)<.1);
 assert.equal(interpolateActors(samples,1000)[0].y,3.2);
});
