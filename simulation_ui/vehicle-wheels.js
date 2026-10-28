import * as THREE from './vendor/three.module.js';

export function createWheel(x,z,radius,tireMaterial,rimMaterial,front=false){
  const steering=new THREE.Group();steering.position.set(x,radius,z);
  const spin=new THREE.Group();steering.add(spin);
  const tire=new THREE.Mesh(new THREE.CylinderGeometry(radius,radius,.2,20),tireMaterial);
  tire.rotation.x=Math.PI/2;spin.add(tire);
  const rim=new THREE.Mesh(new THREE.CylinderGeometry(radius*.58,radius*.58,.215,16),rimMaterial);
  rim.rotation.x=Math.PI/2;spin.add(rim);
  steering.userData={wheel:true,front,radius,spin};
  // Spokes reveal axle rotation without rotating or tilting the tire axis.
  for(const angle of [0,Math.PI/3,2*Math.PI/3]){
    const spoke=new THREE.Mesh(new THREE.BoxGeometry(radius*1.03,.035,.225),rimMaterial);
    spoke.rotation.z=angle;spin.add(spoke);
  }
  return steering;
}

export function advanceWheel(wheel,speed,seconds,steeringAngle=0){
  wheel.rotation.y=wheel.userData.front?steeringAngle:0;
  wheel.userData.spin.rotation.z-=speed*Math.min(.1,seconds)/wheel.userData.radius;
}

export function ackermannAngle(wheel,centerAngle,wheelbase,track){
 if(!wheel.userData.front)return 0;
 if(Math.abs(centerAngle)<.0001)return 0;
 const radius=wheelbase/Math.tan(Math.abs(centerAngle));
 const inner=(centerAngle>0&&wheel.userData.side==='left')||(centerAngle<0&&wheel.userData.side==='right');
 return Math.sign(centerAngle)*Math.atan2(wheelbase,Math.max(wheelbase*.5,radius+(inner?-track/2:track/2)));
}

export function advanceWheelDistance(wheel,distance,steeringAngle=0){
 wheel.rotation.y=wheel.userData.front?steeringAngle:0;
 wheel.userData.spin.rotation.z-=distance/wheel.userData.radius;
}
