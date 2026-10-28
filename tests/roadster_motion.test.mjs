import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from '../simulation_ui/vendor/three.module.js';
import {createWheel,advanceWheelDistance,ackermannAngle} from '../simulation_ui/vehicle-wheels.js';
import {interpolateActors} from '../simulation_ui/motion.js';

test('wheel travel matches distance and reverse unwinds the exact forward rotation',()=>{
 const material=new THREE.MeshBasicMaterial(),wheel=createWheel(-1,-.9,.36,material,material,true),origin=wheel.position.clone();
 advanceWheelDistance(wheel,Math.PI*.72,.2);assert(Math.abs(wheel.userData.spin.rotation.z+Math.PI*2)<1e-10);
 advanceWheelDistance(wheel,-Math.PI*.72,.2);assert(Math.abs(wheel.userData.spin.rotation.z)<1e-10);assert(wheel.position.equals(origin));
});

test('front inside wheel turns more sharply and rear wheels stay straight',()=>{
 const left={userData:{front:true,side:'left'}},right={userData:{front:true,side:'right'}},rear={userData:{front:false}};
 assert(ackermannAngle(left,.3,2.8745,1.63)>ackermannAngle(right,.3,2.8745,1.63));
 assert(Math.abs(ackermannAngle(right,-.3,2.8745,1.63))>Math.abs(ackermannAngle(left,-.3,2.8745,1.63)));
 assert.equal(ackermannAngle(rear,.3,2.8745,1.63),0);
});

test('Roadster position and angular velocity remain continuous at nonuniform turn samples',()=>{
 const samples=[[0,0,0,90],[180,1.2,.1,101],[410,2.5,.7,122],[650,3.4,1.8,143],[900,3.8,3.1,169]].map(([at,x,y,heading])=>({at,frame:{vehicles:[{vehicle_id:'ego',x,y,heading,speed:6,road_id:':turn',length:4.7,rear_axle_offset:3.909701}]}}));
 const pose=t=>interpolateActors(samples,t)[0],epsilon=.001;
 for(const t of [180,410,650]){
  const a=pose(t-epsilon),b=pose(t),c=pose(t+epsilon);
  for(const axis of ['x','y','heading'])assert(Math.abs((b[axis]-a[axis])/epsilon-(c[axis]-b[axis])/epsilon)<.002,axis+' derivative jump');
 }
});

test('curved reverse parking keeps the measured body orientation',()=>{
 const samples=[0,1,2,3].map((i)=>({at:i*200,frame:{vehicles:[{vehicle_id:'ego',x:10-i*.12,y:10+i*.1,heading:120+i*4,speed:-.8,road_id:'',length:4.7,rear_axle_offset:3.909701}]}}));
 const v=interpolateActors(samples,300)[0];assert(v.speed<0);assert(v.heading>124&&v.heading<128);assert(v.x<9.9&&v.x>9.7);assert(v.y>10.1&&v.y<10.3);
});
