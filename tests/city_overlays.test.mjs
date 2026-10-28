import test from 'node:test';
import assert from 'node:assert/strict';
import {cityTrajectoryPoints} from '../simulation_ui/city-overlays.js';

test('trajectory begins at the displayed car and bridges measured road positions',()=>{
 const frame={time:2,ego:{x:20,y:4.8,heading:90},ego_trace:[[0,4.8],[10,4.8],[20,4.8]],
 city_reachability:{trajectory:[{x:19,y:4.8,time:1.5},{x:21,y:4.8,time:2.1},{x:30,y:4.8,time:3}]}};
 const path=cityTrajectoryPoints(frame,{x:12,y:4.8,heading:90});
 assert.deepEqual(path[0],{x:12,y:4.8});assert.equal(path[1].x,20);
 assert(path.every(p=>p.x>=12));assert.equal(path.at(-1).x,30);
});

test('measured junction turn remains in the bridge instead of a diagonal shortcut',()=>{
 const frame={time:2,ego:{x:20,y:10,heading:0},ego_trace:[[10,0],[20,0],[20,10]],city_reachability:{trajectory:[]}};
 assert.deepEqual(cityTrajectoryPoints(frame,{x:15,y:0,heading:90}),[{x:15,y:0},{x:20,y:0},{x:20,y:10}]);
});

test('stationary duplicate states do not produce a degenerate trajectory ribbon',()=>{
 const frame={time:2,ego:{x:20,y:4.8,heading:90},ego_trace:[[20,4.8],[20,4.8]],
 city_reachability:{trajectory:[{x:20,y:4.8,time:3},{x:20,y:4.8,time:4}]}};
 assert.equal(cityTrajectoryPoints(frame,frame.ego).length,1);
});


test('blue road guidance remains when no feasible motion forecast exists',()=>{
 const frame={time:2,ego:{x:20,y:4.8,heading:90},city_reachability:{feasible_count:0,trajectory:[],reference_path:[{x:20,y:4.8},{x:30,y:4.8},{x:30,y:20}]}};
 assert.deepEqual(cityTrajectoryPoints(frame,frame.ego),[{x:20,y:4.8},{x:30,y:4.8},{x:30,y:20}]);
 assert.equal(frame.city_reachability.feasible_count,0);
});


test('a stationary safe wait keeps the navigation line visible',()=>{
 const ego={x:20,y:4.8,heading:90};
 const frame={time:2,ego,city_reachability:{trajectory:[{...ego,time:3},{...ego,time:4}],reference_path:[ego,{x:50,y:4.8}]}};
 assert.equal(cityTrajectoryPoints(frame,ego).at(-1).x,50);
});

test('a missing forecast retains the connected route after a traffic reroute',()=>{
 const ego={x:20,y:4.8,heading:90};
 const frame={time:2,ego,city:{route_shape:[[20,4.8,0],[30,4.8,0],[30,40,0]]},city_reachability:{trajectory:[],feasible:[]}};
 assert.deepEqual(cityTrajectoryPoints(frame,ego).map(p=>[p.x,p.y]),[[20,4.8],[30,4.8],[30,40]]);
 assert.equal(frame.city_reachability.feasible.length,0);
});

test('parking route follows the manoeuvre instead of returning to the road',()=>{
 const ego={x:30,y:12,heading:90};
 const frame={time:2,ego,city:{parking:{active:true,path:[{x:30,y:12},{x:35,y:12},{x:35,y:25}]}},city_reachability:{reference_path:[{x:0,y:0}]}};
 assert.equal(cityTrajectoryPoints(frame,ego).at(-1).y,25);
});


test('motion preview stops at its safe horizon rather than extending through route guidance',()=>{
 const ego={x:0,y:0,heading:90},frame={time:0,ego,city:{route_shape:[[0,0],[100,0]]},city_reachability:{trajectory:[{x:5,y:0,time:1}]}};
 assert.equal(cityTrajectoryPoints(frame,ego,{guidance:false}).at(-1).x,5);
 frame.city_reachability.trajectory=[];
 assert.equal(cityTrajectoryPoints(frame,ego,{guidance:false}).length,1);
});

test('classification preserves rejection reasons and labels do not flood the road',async()=>{
 const {reachableClasses,unsafeLabels}=await import('../simulation_ui/city-overlays.js');
 const safe={id:1,x:1,y:0,time:1,valid:true},bad={id:2,x:20,y:0,time:1,valid:false,collision:true,reasons:['Nearby vehicle']};
 const classes=reachableClasses({raw:[safe,bad],feasible:[safe]});
 assert.deepEqual(classes.safe,[safe]);assert.deepEqual(classes.unsafe,[bad]);
 assert.equal(unsafeLabels([bad,{...bad,id:3,x:30}]).length,1);
 assert.equal(unsafeLabels([bad])[0].text,'Nearby vehicle');
});


test('corner hazard messages require a current nearby conflicting actor',async()=>{
 const {hazardMessages,frameReachability}=await import('../simulation_ui/city-overlays.js');
 const ego={x:0,y:0,z:0},other={vehicle_id:'bus',x:8,y:0,z:0};
 const point={id:2,x:12,y:0,z:0,time:2,collision:true,blocked_by:['bus'],reasons:['Blocked by nearby vehicle: bus'],hazard_point:{x:6,y:0,z:0,time:1}};
 const frame={time:0,ego,vehicles:[other],sensing:{range:20},city_reachability:{raw:[point],feasible:[]}};
 assert.equal(frameReachability(frame).unsafe[0].x,6);
 assert.deepEqual(hazardMessages(frame),['Motion blocked by bus']);
 other.x=30;assert.deepEqual(hazardMessages(frame),[]);
 other.x=8;other.z=7;assert.deepEqual(hazardMessages(frame),[]);
 frame.vehicles=[];assert.deepEqual(hazardMessages(frame),[]);
});

test('speed and signal rejections do not create red obstacle points',async()=>{
 const {reachableClasses}=await import('../simulation_ui/city-overlays.js');
 assert.deepEqual(reachableClasses({raw:[{id:1,x:0,y:0,valid:false,reasons:['Red signal']}],feasible:[]}).unsafe,[]);
});
