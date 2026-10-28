import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from '../simulation_ui/vendor/three.module.js';
import {createWheel,advanceWheel} from '../simulation_ui/vehicle-wheels.js';
import {turnSignals,assistance,DriverAudio} from '../simulation_ui/driver-assist.js';
import {roadRibbon,roadPitch} from '../simulation_ui/road-surface.js';

test('wheel spins around its axle without tilting or orbiting',()=>{
 const tire=new THREE.MeshBasicMaterial(),rim=new THREE.MeshBasicMaterial();
 const wheel=createWheel(-1,-.9,.32,tire,rim,true),origin=wheel.position.clone();
 for(let i=0;i<100;i++){
  advanceWheel(wheel,12,.016,.2);wheel.updateMatrixWorld(true);
  const mesh=wheel.userData.spin.children[0];
  const axis=new THREE.Vector3(0,1,0).transformDirection(mesh.matrixWorld);
  assert(Math.abs(axis.y)<1e-7);assert(wheel.position.equals(origin));
  assert(Math.abs(axis.dot(new THREE.Vector3(Math.sin(.2),0,Math.cos(.2))))>.9999);
 }
});

test('SUMO indicator bits distinguish left, right, hazard and braking',()=>{
 assert.deepEqual(turnSignals({signals:1}),{left:false,right:true,brake:false});
 assert.deepEqual(turnSignals({signals:2}),{left:true,right:false,brake:false});
 assert.deepEqual(turnSignals({signals:12}),{left:true,right:true,brake:true});
});

test('ADAS warns on closing traffic but stays quiet while queued at rest',()=>{
 assert.equal(assistance({ego:{speed:12},ttc:1.2}).level,'danger');
 assert.equal(assistance({ego:{speed:12},ttc:3}).level,'caution');
 assert.equal(assistance({ego:{speed:0},ttc:0,clearance:1}).level,'none');
 assert.equal(assistance({ego:{speed:10},ttc:null,clearance:null}).level,'none');
});

test('blind spot alert uses signalled side and ignores traffic on another deck',()=>{
 const ego={vehicle_id:'ego',x:0,y:0,heading:90,speed:8,signals:2,z:0};
 const other={vehicle_id:'bus',x:-3,y:3,z:0};
 assert.match(assistance({ego,vehicles:[other]}).message,/Left blind spot/);
 assert.equal(assistance({ego,vehicles:[{...other,z:7}]}).level,'none');
 assert.equal(assistance({ego:{...ego,signals:1},vehicles:[other]}).level,'none');
});

test('audio is opt-in, quiet during replay/pause, and warning tones are rate limited',()=>{
 const audio=new DriverAudio(),calls=[];audio.tone=(...args)=>calls.push(args);
 const frame={ego:{speed:10},ttc:1};
 audio.update(frame,true,0);assert.equal(calls.length,0);
 audio.enabled=true;audio.update(frame,false,0);assert.equal(calls.length,0);
 audio.update(frame,true,0);assert.equal(calls.length,2);
 audio.update(frame,true,100);assert.equal(calls.length,2);
 audio.update(frame,true,1100);assert.equal(calls.length,4);
});

test('curved road surface shares vertices across segments and preserves ramp height',()=>{
 const ribbon=roadRibbon([[0,0,0],[10,0,2],[20,5,4]],3.2);
 assert.equal(ribbon.positions.length,18);assert.equal(ribbon.indices.length,12);
 assert.equal(ribbon.positions[7],1.99);assert.equal(ribbon.positions[13],3.99);
 assert(ribbon.indices.slice(0,6).includes(2)&&ribbon.indices.slice(6).includes(2));
 assert(ribbon.positions.every(Number.isFinite));
});


test('car pitch follows ascending and descending ramps without changing decks',()=>{
 assert(roadPitch([[0,0,0],[100,0,7]],50,0)>0);
 assert(roadPitch([[100,0,7],[200,0,0]],150,0)<0);
 assert.equal(roadPitch([[0,0,7],[100,0,7]],50,0),0);
 assert.equal(roadPitch(undefined,50,0),0);
});

test('parked cars do not produce a contradictory waiting notification',()=>{
 assert.deepEqual(assistance({ego:{speed:0},city:{parked:true}}),{level:'none',message:'Arrival complete'});
});
