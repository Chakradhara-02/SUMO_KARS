import * as THREE from './vendor/three.module.js';
import {GLTFLoader} from './vendor/GLTFLoader.js';

const assets=new Map();
export function roadsterAsset(level='drive'){
 if(!assets.has(level))assets.set(level,new GLTFLoader().loadAsync(`/assets/roadster-${level}.glb`));
 return assets.get(level);
}

export function installRoadster(root,template,length,width){
 const canonical=template.parser.json.extras,scale=Math.min(length/canonical.length,width/canonical.width);
 const model=new THREE.Group();model.name='Tesla Roadster';model.scale.setScalar(scale);
 const wheels=[],bodyMotion=new THREE.Group();bodyMotion.position.x=-canonical.length/2;model.add(bodyMotion);
 for(const source of template.scene.children){
  const mesh=source.clone();mesh.geometry=source.geometry.clone();mesh.material=source.material.clone();
  if(source.userData.wheel){
   const pivot=new THREE.Group(),spin=new THREE.Group();pivot.name=source.name;pivot.position.copy(source.position);mesh.position.set(0,0,0);spin.add(mesh);pivot.add(spin);model.add(pivot);
   pivot.userData={wheel:true,front:!!source.userData.front,side:source.userData.side,radius:source.userData.radius*scale,spin};wheels.push(pivot);
  }else{mesh.position.x+=canonical.length/2;bodyMotion.add(mesh);}
 }
 root.add(model);root.userData.wheels.splice(0,root.userData.wheels.length,...wheels);
 root.userData.panels={};root.userData.assetState='ready';root.userData.modelName='Tesla Roadster';root.userData.bodyMotion=bodyMotion;
 root.userData.wheelbase=canonical.wheelbase*scale;root.userData.rearAxleOffset=canonical.rear_axle_offset*scale;
 root.userData.track=Math.abs(wheels.find(w=>w.userData.front&&w.position.z<0).position.z-wheels.find(w=>w.userData.front&&w.position.z>0).position.z)*scale;
 root.userData.panelSupport=false;return model;
}
