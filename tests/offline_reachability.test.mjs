import test from 'node:test';
import assert from 'node:assert/strict';
import {offlineReachability,motionDirections,motionMarker} from '../simulation_ui/offline-reachability.js';
const ego={vehicle_id:'ego',x:20,y:30,z:0,heading:90,speed:8,length:4.7,acceleration:0};
const frame={time:10,city:{}};

test('offline lookup exposes precomputed, unfiltered state bins',()=>{
 const rs=offlineReachability(frame,ego);
 assert(rs.points.length>1000);assert.equal(rs.branches.length,39);
 assert.equal(rs.metadata.filtered_for_obstacles,false);
 assert.equal(rs.metadata.bins[0].speed,8);
 assert(rs.points.every(p=>p.offline));
});

test('offline points are invariant to roads, traffic and signals',()=>{
 const clear=offlineReachability(frame,ego),blocked=offlineReachability({...frame,vehicles:[{vehicle_id:'bus'}],city:{next_signal:{color:'r'}}},ego);
 assert.deepEqual(clear,blocked);
});

test('offline lookup rotates and translates geometry without changing the body reference',()=>{
 const east=offlineReachability(frame,ego),north=offlineReachability(frame,{...ego,x:100,y:200,heading:0});
 const a=east.branches.find(b=>b.steering===0&&b.acceleration===0).points.at(-1);
 const b=north.branches.find(b=>b.steering===0&&b.acceleration===0).points.at(-1);
 assert(Math.abs((a.x-20)-(b.y-200))<1e-6);assert(Math.abs(b.x-100)<1e-6);
});

test('stationary uncommitted state shows both directions; moving cars do not reverse instantly',()=>{
 const rest=offlineReachability(frame,{...ego,speed:0});
 assert.deepEqual(rest.metadata.bins.map(b=>b.direction),[1,-1]);
 assert(rest.points.some(p=>p.x<ego.x));assert(rest.points.some(p=>p.x>ego.x));
 assert.deepEqual(motionDirections(frame,ego),[1]);
 assert.deepEqual(motionDirections({...frame,city:{parking:{gear:'R',active:true}}},{...ego,speed:0}),[-1]);
 assert.deepEqual(motionDirections(frame,{...ego,speed:-1}),[-1]);
 assert.deepEqual(motionDirections({...frame,city:{parking:{gear:'P',complete:true}}},{...ego,speed:0}),[]);
});


test('reverse marker reference starts at the rear bumper and extends behind the visible car',()=>{
 const car={...ego,speed:-1},rs=offlineReachability(frame,car);
 const branch=rs.branches.find(b=>b.steering===0&&b.acceleration===0);
 const start=motionMarker(branch.points[0],car,-1),end=motionMarker(branch.points.at(-1),car,-1);
 assert(Math.abs(start.x-(car.x-car.length))<1e-6);
 assert(end.x<car.x-car.length-2);assert.equal(end.heading,90);
});
