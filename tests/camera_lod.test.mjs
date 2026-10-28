import test from 'node:test';
import assert from 'node:assert/strict';
import {cameraProfile} from '../simulation_ui/camera-profile.js';
import {detailedTraffic,TrafficInstances} from '../simulation_ui/traffic-lod.js';
import * as THREE from '../simulation_ui/vendor/three.module.js';
import {parkingView} from '../simulation_ui/parking-ui.js';

test('underpass camera stays below deck and follow view remains usable',()=>{
 const decks=[{a:[0,0,7],b:[150,0,7],width:12.8}];
 const under=cameraProfile({x:70,y:2,z:0,heading:90},decks);
 assert(under.underpass);assert(under.height<5);assert(under.height<7-.65-1);
 const upper=cameraProfile({x:70,y:2,z:7,heading:90},decks);
 assert(!upper.underpass);assert.equal(upper.height,7);
});
test('600 vehicles retain ego detail while distant traffic uses four instance draws',()=>{
 const actors=Array.from({length:600},(_,i)=>({vehicle_id:i?'car_'+i:'ego',x:i,y:0,z:0,heading:90,length:4.7,width:1.8}));
 const near=detailedTraffic(actors,actors[0]);assert(near.length<=32);assert(near.some(a=>a.vehicle_id==='ego'));
 const instances=new TrafficInstances(new THREE.Group());instances.update(actors.slice(32));
 assert.equal(instances.parts.length,4);assert(instances.parts.every(p=>p.count===568));
});
test('parking display distinguishes occupied, selected and completed bays',()=>{
 const lot={id:'city_mall',name:'City Mall',x:0,y:0,slots:[{id:'A1',x:22,y:25,width:3.1,length:6,occupied:false},{id:'A2',x:26,y:25,width:3.1,length:6,occupied:true}]};
 const view=parkingView({}, {parking_lot:lot},'A1');assert.match(view.slots,/A1/);assert.match(view.slots,/disabled/);assert.match(view.slots,/Selected/);
 const done=parkingView({city:{trip:{parking_lot:lot},parking:{active:true,complete:true,stage:'parked',gear:'P',slot_id:'A1',progress:1}}},null,null);
 assert(done.locked);assert.match(done.html,/PARKING COMPLETE/);assert.match(done.html,/Parked securely/);
});
