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
