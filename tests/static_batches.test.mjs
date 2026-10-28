import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from '../simulation_ui/vendor/three.module.js';
import {batchStaticSurfaces} from '../simulation_ui/static-batches.js';

test('static road surfaces share a draw while dynamic materials and instances stay independent',()=>{
 const group=new THREE.Group(),box=new THREE.BoxGeometry(),material=new THREE.MeshStandardMaterial({color:0x697780});
 for(let i=0;i<10;i++){const road=new THREE.Mesh(new THREE.PlaneGeometry(5,3),material);road.rotation.x=-Math.PI/2;road.position.x=i*6;group.add(road);}
 const dynamic=new THREE.Mesh(new THREE.SphereGeometry(),new THREE.MeshBasicMaterial());group.add(dynamic);
 const stats=batchStaticSurfaces(group,box,new Set([material]));
 assert.equal(stats.originalMeshes,10);assert.equal(stats.batches,1);assert(group.children.includes(dynamic));
 const merged=group.children.find(o=>o.userData.staticSurfaceBatch);merged.geometry.computeBoundingBox();
 assert.equal(merged.geometry.boundingBox.min.x,-2.5);assert.equal(merged.geometry.boundingBox.max.x,56.5);
});

test('distant surfaces remain in separate spatial batches',()=>{
 const group=new THREE.Group(),material=new THREE.MeshStandardMaterial();
 for(const x of [0,5,500,505]){const mesh=new THREE.Mesh(new THREE.PlaneGeometry(3,3),material);mesh.position.x=x;group.add(mesh);}
 const stats=batchStaticSurfaces(group,new THREE.BoxGeometry(),new Set([material]));assert.equal(stats.batches,2);
});
