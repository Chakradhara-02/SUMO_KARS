import test from 'node:test';
import assert from 'node:assert/strict';
import {localReachability,localHazardMessages} from '../simulation_ui/local-reachability.js';
const ego=(x=0)=>({vehicle_id:'ego',x,y:0,z:0,heading:90,speed:8,speed_limit:13.9,length:4.7,width:1.8});
const frame={time:10,ego:ego(10),city:{},sensing:{range:120},ego_trace:[],city_reachability:{trajectory:[]}};

test('online branches share the displayed initial state and spread to both sides',()=>{
 const car=ego(0),result=localReachability(frame,[car]);
 assert.equal(result.mode,'online');assert.equal(result.horizon,3);assert.equal(result.branches.length,39);
 assert(result.branches.every(b=>b.points[0].x===0&&b.points[0].y===0));
 assert(result.safe.some(p=>p.y>2));assert(result.safe.some(p=>p.y< -2));
 assert(result.safe.every(p=>p.x>=0)); // No invented reversing at driving speed.
 assert(result.selected.length>1);assert(result.optimization.complete);
});

test('the blue candidate is the minimum-cost complete trajectory',()=>{
 const result=localReachability(frame,[ego()]);
 const best=result.branches.filter(b=>b.complete).sort((a,b)=>a.cost-b.cost)[0];
 assert.deepEqual(result.selected,best.points);assert.equal(result.optimization.cost,best.cost);
 assert(result.selected.every(p=>!p.collision));
});

test('nearby blockers prune branches and never appear in the selected path',()=>{
 const car=ego(),other={...ego(12),vehicle_id:'blocker',speed:0};
 const result=localReachability(frame,[car,other]);assert(result.unsafe.length);
 assert.deepEqual(localHazardMessages(result),['Candidate blocked by blocker']);
 assert(result.selected.every(p=>!p.collision));
 assert(result.branches.filter(b=>b.blocked_by.length).every(b=>b.points.at(-1).collision));
 other.z=7;assert.equal(localReachability(frame,[car,other]).unsafe.length,0);
});

test('stationary parking permits bounded reverse candidates but road driving does not',()=>{
 const car={...ego(),speed:0},road=localReachability(frame,[{...car,gear:'D'}]);assert(road.safe.every(p=>p.x>=0));
 const parking=localReachability(frame,[car]);
 assert(parking.safe.some(p=>p.x<0));assert(parking.safe.some(p=>p.x>0));
});

test('road boundaries truncate candidates and signals constrain the optimized path',()=>{
 const car=ego(),network={lanes:[{id:'test_0',shape:[[-10,0,0],[80,0,0]],width:3.2}]};
 const result=localReachability(frame,[car],network);
 assert(result.branches.some(b=>b.reason.startsWith('Road boundary')));
 assert(result.selected.every(p=>Math.abs(p.y)<1.6));
 const red=localReachability({...frame,city:{next_signal:{color:'r',distance:16,seconds:15}}},[car],network);
 assert(red.selected.every(p=>p.x<=13));assert(red.unsafe.some(p=>p.rejection_kind==='signal'));assert(red.selected.every(p=>!p.unsafe));
});

test('new frames clear blocked samples and replan around the current pose',()=>{
 const car=ego(),other={...ego(12),vehicle_id:'blocker',speed:0};
 assert(localReachability(frame,[car,other]).unsafe.length);
 assert.equal(localReachability(frame,[car]).unsafe.length,0);
 const moved=localReachability(frame,[ego(30)]);assert(moved.branches.every(b=>b.points[0].x===30));
});


test('lane-change candidates countersteer rather than remaining in a circular turn',()=>{
 const result=localReachability(frame,[ego()]);
 const arc=result.branches.find(b=>b.complete&&b.acceleration===0&&b.steering===.09&&b.profile==='arc');
 const change=result.branches.find(b=>b.complete&&b.acceleration===0&&b.steering===.09&&b.profile==='lane_change');
 assert(arc&&change);
 assert(Math.abs(change.points.at(-1).heading-90)<Math.abs(arc.points.at(-1).heading-90));
});


test('optimization chooses a feasible lane-change around a distant stopped vehicle',()=>{
 const car=ego(),other={...ego(22),vehicle_id:'bus',speed:0};
 const result=localReachability(frame,[car,other]);
 const best=result.branches.filter(b=>b.complete).sort((a,b)=>a.cost-b.cost)[0];
 assert(best);assert.equal(best.profile,'lane_change');
 assert(Math.abs(best.points.at(-1).y)>2);assert(best.progress>20);
 assert.deepEqual(result.selected,best.points);assert(result.unsafe.length);
});


test('reverse gear at rest and negative velocity generate points behind the car',()=>{
 const car={...ego(),speed:0};
 const reversePath=[{x:0,y:0,heading:90,gear:'R'},{x:-5,y:0,heading:90,gear:'R'}];
 const reverse=localReachability({...frame,city:{parking:{active:true,gear:'R',path:reversePath}}},[car]);
 assert.deepEqual(reverse.directions,[-1]);assert(reverse.safe.some(p=>p.x< -1));
 assert(reverse.safe.every(p=>p.speed<=0));assert(reverse.offline.some(p=>p.x< -1));
 const moving=localReachability(frame,[{...car,speed:-.8}]);
 assert.deepEqual(moving.directions,[-1]);assert(moving.selected.at(-1).x<0);
 assert(Math.abs(moving.branches.find(b=>b.steering===0).points.at(-1).heading-90)<1e-8);
});

test('reverse collision checks reject nearby rear obstacles',()=>{
 const car={...ego(),speed:-1},rear={...ego(-6.5),vehicle_id:'rear_blocker',speed:0};
 const result=localReachability(frame,[car,rear]);
 assert(result.unsafe.some(p=>p.blocked_by.includes('rear_blocker')));
 assert(result.selected.every(p=>!p.collision));
});


test('selected endpoint is a reachable point connected by the selected parent chain',()=>{
 const r=localReachability(frame,[ego()]);
 assert(r.selectedBranchId);assert(r.selectedEndpoint);
 assert(r.safe.some(p=>p.id===r.selectedEndpoint.id));
 assert.equal(r.selected.at(-1).id,r.selectedEndpoint.id);
 const branch=r.branches.find(b=>b.id===r.selectedBranchId);
 assert.deepEqual(r.selected,branch.points);
 for(let i=1;i<r.selected.length;i++)assert.equal(r.selected[i].parent_id,r.selected[i-1].id);
});

test('parking trajectory is selected from the same displayed reachable candidates',()=>{
 const car={...ego(),speed:-.8},path=[{x:0,y:0,heading:90,gear:'R'},{x:-1,y:.15,heading:100,gear:'R'},{x:-2,y:.6,heading:115,gear:'R'},{x:-4,y:2,heading:140,gear:'R'}];
 const f={...frame,city:{parking:{active:true,gear:'R',path}}};
 const r=localReachability(f,[car]);assert.equal(r.mode,'parking');
 const branch=r.branches.find(b=>b.id===r.selectedBranchId);
 assert(branch);assert.equal(branch.profile,'parking_path');assert.deepEqual(r.selected,branch.points);
 assert(r.safe.some(p=>p.id===r.selectedEndpoint.id));assert(r.selected.at(-1).y>.1);
 assert(r.selected.every(p=>p.direction===-1));
});

test('missing parking path produces a hold candidate rather than unrelated moving rays',()=>{
 const car={...ego(),speed:0},r=localReachability({...frame,city:{parking:{active:true,stage:'waiting_selection'}}},[car]);
 assert(r.selected.every(p=>p.x===car.x&&p.y===car.y));
});
