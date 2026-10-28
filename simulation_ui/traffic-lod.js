import * as THREE from './vendor/three.module.js';
export function detailedTraffic(actors,ego,limit=32){
 if(actors.length<=limit)return actors;
 const e=ego||actors[0];return actors.map(a=>({a,d:Math.hypot(a.x-e.x,a.y-e.y)})).filter(q=>q.a.vehicle_id==='ego'||q.d<85).sort((a,b)=>(a.a.vehicle_id==='ego'?-1:b.a.vehicle_id==='ego'?1:a.d-b.d)).slice(0,limit).map(q=>q.a);
}
export class TrafficInstances{
 constructor(parent,capacity=650){
  this.parts=[];this.dummy=new THREE.Object3D();this.color=new THREE.Color();this.parent=new THREE.Group();parent.add(this.parent);
  for(const color of [0x7892a2,0x334755,0x202b32,0x202b32]){
   const mesh=new THREE.InstancedMesh(new THREE.BoxGeometry(1,1,1),new THREE.MeshStandardMaterial({color,roughness:.85}),capacity);mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);mesh.frustumCulled=false;mesh.count=0;this.parts.push(mesh);this.parent.add(mesh);
  }
 }
 update(actors){
  for(const p of this.parts)p.count=actors.length;
  actors.forEach((a,i)=>{
   const l=a.length||4.7,w=a.width||1.8,h=l>7?2.5:1.35,yaw=(90-a.heading)*Math.PI/180,c=Math.cos(yaw),s=Math.sin(yaw);
   const parts=[[-l/2,h*.37,l-.1,h*.56,w],[-l*.52,h*.78,l*.48,h*.4,w*.8],[-l*.2,.29,.36,.5,w*1.03],[-l*.8,.29,.36,.5,w*1.03]];
   parts.forEach(([x,y,dx,dy,dz],j)=>{this.dummy.position.set(a.x+c*x,(a.z||0)+y,-a.y-s*x);this.dummy.rotation.set(0,yaw,0);this.dummy.scale.set(dx,dy,dz);this.dummy.updateMatrix();this.parts[j].setMatrixAt(i,this.dummy.matrix);});
  });for(const p of this.parts)p.instanceMatrix.needsUpdate=true;
 }
}
