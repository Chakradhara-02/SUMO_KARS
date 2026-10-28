import * as THREE from './vendor/three.module.js';
import {createWheel} from './vehicle-wheels.js';
import {roadsterAsset,installRoadster} from './roadster-asset.js';

// A shared lightweight vehicle for road driving and the parked-vehicle display.
// Its origin remains the SUMO front bumper; changing styling cannot change motion.
function createFallbackVehicle(length=4.7,width=1.8){
 const car=new THREE.Group(),paint=new THREE.MeshStandardMaterial({color:0x1267de,metalness:.52,roughness:.28}),glass=new THREE.MeshStandardMaterial({color:0x182b40,metalness:.35,roughness:.18}),trim=new THREE.MeshStandardMaterial({color:0x172330,roughness:.45});
 const box=(parent,x,y,z,l,h,w,material)=>{const m=new THREE.Mesh(new THREE.BoxGeometry(l,h,w),material);m.position.set(x,y,z);parent.add(m);return m;};
 const profile=(parent,coordinates,depth,material)=>{const s=new THREE.Shape();coordinates.forEach(([x,y],i)=>i?s.lineTo(x,y):s.moveTo(x,y));s.closePath();const g=new THREE.ExtrudeGeometry(s,{depth,bevelEnabled:true,bevelSegments:3,bevelSize:.055,bevelThickness:.035,steps:1});g.translate(0,0,-depth/2);const m=new THREE.Mesh(g,material);parent.add(m);return m;};
 const l=length,w=width;
 // Rounded, tapered body sections give the coupe a continuous nose and haunches.
 const sections=[[0,.68],[.025,.83],[.08,.94],[.2,1],[.4,.98],[.63,.98],[.8,1],[.93,.92],[1,.75]],positions=[],indices=[],rings=32;
 sections.forEach(([t,wide],i)=>{for(let j=0;j<rings;j++){const a=j/rings*Math.PI*2;positions.push(-.05-t*(l-.1),.56+Math.sin(a)*.265,Math.cos(a)*(w/2-.065)*wide);if(i){const a0=(i-1)*rings+j,b0=(i-1)*rings+(j+1)%rings,c0=i*rings+j,d0=i*rings+(j+1)%rings;indices.push(a0,b0,c0,b0,d0,c0);}}});
 // Close nose and tail while keeping the body inside the measured footprint.
 for(const i of [0,sections.length-1]){const center=positions.length/3;positions.push(-.05-sections[i][0]*(l-.1),.56,0);for(let j=0;j<rings;j++){const a=i*rings+j,b=i*rings+(j+1)%rings;indices.push(center,...(i===0?[b,a]:[a,b]));}}
 const body=new THREE.BufferGeometry();body.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));body.setIndex(indices);body.computeVertexNormals();car.add(new THREE.Mesh(body,paint));
 const roof=new THREE.Shape();roof.moveTo(-l*.85,.77);roof.quadraticCurveTo(-l*.75,1.04,-l*.64,1.18);roof.quadraticCurveTo(-l*.53,1.27,-l*.41,1.18);roof.quadraticCurveTo(-l*.28,1.03,-l*.21,.78);roof.closePath();
 const cabin=new THREE.ExtrudeGeometry(roof,{depth:w*.70,bevelEnabled:true,bevelSegments:5,bevelSize:.065,bevelThickness:.065,steps:1,curveSegments:16});cabin.translate(0,0,-w*.35);car.add(new THREE.Mesh(cabin,glass));
 box(car,-l*.54,1.225,0,l*.22,.035,w*.62,paint);
 box(car,-l/2,.3,0,l*.84,.09,w*.92,trim);
 const white=new THREE.MeshBasicMaterial({color:0xe8faff}),red=new THREE.MeshBasicMaterial({color:0xff4e62});
 for(const side of [-1,1]){
  box(car,-.055,.64,side*w*.27,.04,.05,w*.22,white);
  box(car,-l+.055,.67,side*w*.27,.04,.05,w*.22,red);
  box(car,-l*.3,1.0,side*w*.44,.25,.10,.13,paint);
  box(car,-l*.52,.75,side*w*.5,.18,.035,.035,trim);
 }
 const door=new THREE.Group();door.position.set(-l*.29,.48,-w*.45);car.add(door);
 box(door,-l*.14,.18,0,l*.28,.38,.055,paint);box(door,-l*.15,.54,0,l*.24,.32,.04,glass);
 const hood=new THREE.Group();hood.position.set(-l*.29,.79,0);car.add(hood);box(hood,l*.105,0,0,l*.21,.045,w*.78,paint);
 const boot=new THREE.Group();boot.position.set(-l*.72,.83,0);car.add(boot);box(boot,-l*.095,0,0,l*.19,.035,w*.73,paint);
 box(car,-l*.90,.91,0,.12,.045,w*.83,trim);
 for(const side of [-1,1])box(car,-l*.9,.855,side*w*.28,.045,.09,.045,trim);
 box(car,-.085,.36,0,.13,.055,w*.72,trim);
 for(const side of [-1,1])box(car,-l+.09,.36,side*w*.24,.12,.045,.20,trim);
 car.userData.panels={door,hood,boot};car.userData.wheels=[];
 const rim=new THREE.MeshStandardMaterial({color:0xc5d7e7,metalness:.65,roughness:.3});
 for(const x of [-l*.2,-l*.8])for(const z of [-w*.48,w*.48]){const wheel=createWheel(x,z,.32,trim,rim,x>-l*.3);car.add(wheel);car.userData.wheels.push(wheel);}
 return car;
}

export function createEgoVehicle(length=4.7,width=2.05,{quality='drive'}={}){
 const root=new THREE.Group(),fallback=createFallbackVehicle(length,width);root.add(fallback);
 root.userData={roadsterRoot:true,assetState:'loading',wheels:fallback.userData.wheels,panels:{},panelSupport:false,wheelbase:length*.61};
 root.userData.ready=roadsterAsset(quality).then(asset=>{
  if(root.userData.disposed)return root;
  root.remove(fallback);const materials=new Set();fallback.traverse(o=>{o.geometry?.dispose();if(o.material)materials.add(o.material);});materials.forEach(m=>m.dispose());
  installRoadster(root,asset,length,width);return root;
 }).catch(error=>{root.userData.assetState='error';root.userData.error=error.message;console.warn('Roadster asset could not load:',error);return root;});
 return root;
}
