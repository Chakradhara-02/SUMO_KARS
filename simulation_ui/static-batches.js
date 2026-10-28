import * as THREE from './vendor/three.module.js';
import {mergeGeometries} from './vendor/BufferGeometryUtils.js';

// Merge only immutable solid environment surfaces, partitioned into spatial
// tiles so distant road surfaces still benefit from frustum culling.
export function batchStaticSurfaces(group,sharedBox,materials,tileSize=120){
 group.updateMatrixWorld(true);const inverse=group.matrixWorld.clone().invert(),batches=new Map();
 group.traverse(object=>{
  if(!object.isMesh||object.isInstancedMesh||object.geometry===sharedBox||!materials.has(object.material)||object.material.transparent)return;
  const geometry=object.geometry.clone().applyMatrix4(inverse.clone().multiply(object.matrixWorld));
  for(const name of Object.keys(geometry.attributes))if(!['position','normal'].includes(name))geometry.deleteAttribute(name);
  if(!geometry.attributes.normal)geometry.computeVertexNormals();
  if(!geometry.index)geometry.setIndex(Array.from({length:geometry.attributes.position.count},(_,i)=>i));
  geometry.computeBoundingBox();const center=geometry.boundingBox.getCenter(new THREE.Vector3()),key=object.material.uuid+'/'+Math.floor(center.x/tileSize)+'/'+Math.floor(center.z/tileSize);
  if(!batches.has(key))batches.set(key,[]);batches.get(key).push({object,geometry});
 });
 let originals=0,created=0;
 for(const objects of batches.values()){
  if(objects.length<2){objects[0].geometry.dispose();continue;}
  const merged=mergeGeometries(objects.map(o=>o.geometry),false);
  if(merged){merged.computeBoundingSphere();const mesh=new THREE.Mesh(merged,objects[0].object.material);mesh.userData.staticSurfaceBatch=true;group.add(mesh);created++;
   for(const {object}of objects){object.parent.remove(object);object.geometry.dispose();originals++;}
  }
  for(const {geometry}of objects)geometry.dispose();
 }
 return {originalMeshes:originals,batches:created};
}
