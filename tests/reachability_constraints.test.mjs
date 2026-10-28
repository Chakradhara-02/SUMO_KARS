import {createReachabilityValidator,conflict,center} from '../simulation_ui/reachability-constraints.js';
import test from 'node:test';
import assert from 'node:assert/strict';
import {localReachability,visibleUnsafeStates} from '../simulation_ui/local-reachability.js';
import {offlineReachability,motionMarker} from '../simulation_ui/offline-reachability.js';
const ego={vehicle_id:'ego',x:20,y:0,z:0,heading:90,speed:8,speed_limit:13.9,length:4.7,width:1.8,road_id:'east'};
const frame={time:0,city:{trip:{edges:['east']}},sensing:{range:120}};
const network={lanes:[{id:'east_0',shape:[[0,0,0],[100,0,0]],width:3.2},{id:'opposite_0',shape:[[100,3.3,0],[0,3.3,0]],width:3.2}]};

test('offline display clips invalid branches but preserves the raw precomputed library',()=>{
 const raw=offlineReachability(frame,ego),r=localReachability(frame,[ego],network);
 assert.deepEqual(r.offlineRaw,raw.points);
 assert(r.offline.length>0&&r.offline.length<raw.points.length);
 assert.equal(r.offlineMetadata.display_filtered,true);
 assert(r.offlineUnsafe.some(p=>p.rejection_kind==='road_boundary'));
 assert(r.offline.every(p=>!p.unsafe&&Math.abs(p.y)<1.61));
 for(const branch of r.offlineBranches)if(branch.rejection){assert(branch.points.every(p=>!p.unsafe));assert(branch.points.at(-1).time<branch.rejection.time);}
});

test('off-road samples become red rejection points, never selected trajectory states',()=>{
 const r=localReachability(frame,[ego],network);
 assert(r.unsafe.some(p=>p.rejection_kind==='road_boundary'));
 assert(visibleUnsafeStates(r).some(p=>p.reason.includes('Road boundary')));
 assert(r.selected.every(p=>!p.unsafe));assert(r.safe.some(p=>p.id===r.selectedEndpoint.id));
 assert(visibleUnsafeStates(r,false).every(p=>!p.offline));
});

test('the projected offline envelope stops at a red signal and shows the reason',()=>{
 const red={...frame,city:{...frame.city,next_signal:{color:'r',distance:15,seconds:15}}};
 const r=localReachability(red,[ego],network);
 assert(r.offlineUnsafe.some(p=>p.rejection_kind==='signal'));
 assert(r.unsafe.some(p=>p.rejection_kind==='signal'));
 assert(r.offline.every(p=>p.x<=32+1e-6));assert(r.selected.every(p=>p.x<=32+1e-6&&!p.unsafe));
});

test('offline speed-limit violations are marked rather than shown as valid purple points',()=>{
 const slow={...ego,speed_limit:8},r=localReachability(frame,[slow],network);
 assert(r.offlineUnsafe.some(p=>p.rejection_kind==='speed_limit'));
 assert(r.offline.every(p=>Math.abs(p.speed)<=8.15+1e-6));
});

test('reverse offline and online states share rear-obstacle rejection checks',()=>{
 const car={...ego,speed:-.8},other={...ego,x:13,vehicle_id:'rear_blocker',speed:0};
 const r=localReachability(frame,[car,other],network);
 const rejected=visibleUnsafeStates(r).filter(p=>p.rejection_kind==='vehicle');
 assert(rejected.length);assert(rejected.every(p=>p.blocked_by.includes('rear_blocker')));
 assert(rejected.every(p=>motionMarker(p,car).x<car.x));
 assert(r.selected.every(p=>!p.unsafe));
});


test('a green countdown expiring before crossing also rejects the future signal state',()=>{
 const green={...frame,city:{...frame.city,next_signal:{color:'g',distance:12,seconds:.5}}};
 const r=localReachability(green,[ego],network);
 assert(r.unsafe.some(p=>p.rejection_kind==='signal'));
 assert(r.offlineUnsafe.some(p=>p.rejection_kind==='signal'));
 assert(r.selected.every(p=>!p.unsafe&&p.x<=29+1e-6));
});


test('optimized collision broad phase agrees with the full four-axis footprint test',()=>{
 let seed=12345;const random=()=>{seed=(1664525*seed+1013904223)>>>0;return seed/4294967296;};
 const car={...ego,x:0,y:0,speed:0},p={...car,time:0},q={...p,time:.1};
 for(let i=0;i<500;i++){
  const other={vehicle_id:'other',x:random()*20-10,y:random()*20-10,z:0,heading:random()*360,speed:0,length:2+random()*10,width:1+random()*2};
  const expected=conflict(center(car,car.length,car.width),center(other,other.length,other.width));
  const result=createReachabilityValidator({...frame,city:{}},car,[car,other])(p,q);
  assert.equal(result.point.collision,expected,'case '+i);
 }
});
