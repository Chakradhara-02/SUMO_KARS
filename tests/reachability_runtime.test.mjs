import test from 'node:test';
import assert from 'node:assert/strict';
import {ReachabilityRuntime,trimTrajectory} from '../simulation_ui/reachability-runtime.js';
import {localReachability,chooseStableCandidate} from '../simulation_ui/local-reachability.js';
const makeEgo=()=>({vehicle_id:'ego',x:20,y:0,z:0,heading:90,speed:8,length:4.7,width:1.8,road_id:'road',speed_limit:13.9});
const network={lanes:[{id:'road_0',shape:[[0,0,0],[300,0,0]],width:6.4}]};
function fixture(auto=true){let clock=0;const sent=[];let generation=0;
 const worker={onmessage:null,postMessage(message){const d=structuredClone(message);sent.push(d);if(d.type==='context'){generation=d.generation;return;}if(auto)queueMicrotask(()=>this.deliver(d));},deliver(d){const result=localReachability(d.frame,d.actors,network,{includeOffline:d.includeOffline});this.onmessage({data:{type:'result',id:d.id,generation:d.generation,result,computeMs:1}});},terminate(){}};
 const runtime=new ReachabilityRuntime({createWorker:()=>worker,now:()=>clock});
 const frame={time:10,city:{trip:{edges:['road']}},sensing:{range:120}},actors=[makeEgo()];
 return {runtime,worker,sent,frame,actors,setClock:x=>clock=x};}
const settle=()=>new Promise(resolve=>queueMicrotask(resolve));

test('60 animation frames schedule at most eight searches, with no request backlog',async()=>{
 const f=fixture();
 for(let i=0;i<60;i++){f.setClock(i*1000/60);f.frame.time=10+Math.floor(i/15)*.25;f.actors[0].x=20+i*8/60;f.runtime.sample(f.frame,f.actors,network,{includeOffline:false});await settle();}
 assert(f.runtime.stats.submitted<=8);assert(f.runtime.stats.completed>=7);
 assert(f.sent.filter(d=>d.type==='plan').every(d=>d.includeOffline===false));
});

test('paused or replayed static snapshots do not repeat identical work',async()=>{
 const f=fixture();f.runtime.sample(f.frame,f.actors,network);await settle();
 for(let i=1;i<=20;i++){f.setClock(i*125);const r=f.runtime.sample(f.frame,f.actors,network);assert(!r.pending);}
 assert.equal(f.runtime.stats.submitted,1);
});

test('one outstanding job prevents queued work and late results from an old gear are dropped',()=>{
 const f=fixture(false);f.runtime.sample(f.frame,f.actors,network);
 const old=f.sent.find(d=>d.type==='plan');
 for(let i=1;i<20;i++){f.setClock(i*20);f.runtime.sample(f.frame,f.actors,network);}
 assert.equal(f.sent.filter(d=>d.type==='plan').length,1);
 f.actors[0].speed=-.8;f.actors[0].gear='R';f.runtime.sample(f.frame,f.actors,network);
 f.worker.deliver(old);assert.equal(f.runtime.stats.completed,0);assert.equal(f.runtime.stats.dropped,1);
});

test('a newly observed blocker hides an old selected path before the next search completes',async()=>{
 const f=fixture();f.runtime.sample(f.frame,f.actors,network,{includeOffline:false});await settle();
 f.setClock(50);f.frame.time=10.25;f.actors[0].x=22;f.actors.push({...makeEgo(),vehicle_id:'blocker',x:28,speed:0});
 const r=f.runtime.sample(f.frame,f.actors,network,{includeOffline:false});assert(r.pending);assert.equal(r.displaySelected.length,0);
});

test('the displayed trajectory starts at the current car and does not backtrack to an old origin',()=>{
 const points=[0,1,2,3].map((x,i)=>({x,y:0,time:10+i*.1,heading:90,direction:1}));
 const path=trimTrajectory(points,{x:1.4,y:0,z:0,heading:90,speed:8},10.1);
 assert.equal(path[0].x,1.4);assert(path.slice(1).every(p=>p.x>=1.4));
 assert.deepEqual(trimTrajectory(points,{x:1.4,y:2,heading:90},10),[]);
});

test('selection hysteresis keeps a feasible incumbent but never retains an invalid candidate',()=>{
 const incumbent={direction:1,profile:'arc',steering:0,acceleration:0,cost:10},alternate={...incumbent,steering:.09,cost:9.7};
 assert.equal(chooseStableCandidate([incumbent,alternate],incumbent),incumbent);
 assert.equal(chooseStableCandidate([incumbent,{...alternate,cost:2}],incumbent).steering,.09);
 assert.equal(chooseStableCandidate([alternate],incumbent),alternate);
});

test('turning offline display off avoids its lookup and projected state validation',()=>{
 const f=fixture(),r=localReachability(f.frame,f.actors,network,{includeOffline:false});
 assert.equal(r.offline.length,0);assert.equal(r.offlineRaw.length,0);assert.equal(r.offlineUnsafe.length,0);
 assert(r.selectedEndpoint);assert(r.offlineMetadata.disabled);
});


test('cold worker results are accepted for an unchanged paused scene',()=>{
 const f=fixture(false);f.runtime.sample(f.frame,f.actors,network);
 const job=f.sent.find(d=>d.type==='plan');f.setClock(1000);f.runtime.sample(f.frame,f.actors,network);f.worker.deliver(job);
 assert.equal(f.runtime.stats.completed,1);assert(!f.runtime.sample(f.frame,f.actors,network).pending);
});

test('stale moving-scene results trigger another job rather than leaving the preview stuck',()=>{
 const f=fixture(false);f.runtime.sample(f.frame,f.actors,network);
 const job=f.sent.find(d=>d.type==='plan');f.setClock(1000);f.frame.time=11;f.actors[0].x=28;f.runtime.sample(f.frame,f.actors,network);f.worker.deliver(job);
 assert.equal(f.runtime.stats.dropped,1);f.runtime.sample(f.frame,f.actors,network);
 assert.equal(f.sent.filter(d=>d.type==='plan').length,2);
});


test('hidden reachability and trajectory layers do not start background searches',()=>{
 const f=fixture();for(let i=0;i<60;i++){f.setClock(i*20);assert(f.runtime.sample(f.frame,f.actors,network,{enabled:false}).disabled);}
 assert.equal(f.runtime.stats.submitted,0);assert.equal(f.sent.length,0);
});
