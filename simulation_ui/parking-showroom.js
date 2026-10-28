import * as THREE from './vendor/three.module.js';
import {OrbitControls} from './vendor/OrbitControls.js';
import {createEgoVehicle} from './vehicle-model.js';

export function mountShowroom(root){
 const canvas=root.querySelector('canvas');if(!canvas)return()=>{};
 const renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:false});renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.outputColorSpace=THREE.SRGBColorSpace;
 const scene=new THREE.Scene();scene.background=new THREE.Color(0xeef3f8);
 scene.add(new THREE.HemisphereLight(0xffffff,0x647384,3));const light=new THREE.DirectionalLight(0xffffff,3.5);light.position.set(4,8,6);scene.add(light);
 const camera=new THREE.PerspectiveCamera(34,1,.1,50);camera.position.set(4.6,2.6,-5.8);camera.lookAt(-1.9,.65,0);
 const car=createEgoVehicle(4.7,2.05,{quality:'showroom'});car.position.x=.6;car.rotation.y=0;scene.add(car);const controls=new OrbitControls(camera,canvas);controls.target.set(-1.75,.65,0);controls.enableDamping=true;controls.enablePan=false;controls.minDistance=4;controls.maxDistance=12;controls.maxPolarAngle=Math.PI*.48;controls.autoRotateSpeed=.8;controls.update();
 car.userData.ready.then(()=>{if(disposed)return;canvas.dataset.model=car.userData.assetState==='ready'?'tesla-roadster':car.userData.assetState;root.querySelector('.car-controls').innerHTML='<button data-car-view=rotate aria-pressed=false>Rotate view</button><button data-car-view=reset>Reset view</button>';root.querySelector('p').textContent=car.userData.assetState==='ready'?'Tesla Roadster · vehicle secured':'Roadster could not load';});
 const shadow=new THREE.Mesh(new THREE.PlaneGeometry(5.5,2.8),new THREE.MeshBasicMaterial({color:0x8a9bb0,transparent:true,opacity:.15}));shadow.rotation.x=-Math.PI/2;shadow.position.set(-1.75,.02,0);scene.add(shadow);
 let disposed=false,last=0,id;
 const click=e=>{const button=e.target.closest('[data-car-view]');if(!button)return;if(button.dataset.carView==='rotate'){controls.autoRotate=!controls.autoRotate;button.setAttribute('aria-pressed',String(controls.autoRotate));}else{controls.autoRotate=false;camera.position.set(4.6,2.6,-5.8);controls.target.set(-1.75,.65,0);root.querySelector('[data-car-view=rotate]').setAttribute('aria-pressed','false');}};root.addEventListener('click',click);
 function draw(now){if(disposed)return;id=requestAnimationFrame(draw);if(now-last<33||document.hidden)return;const dt=Math.min(.1,(now-last)/1000);last=now;
  const w=canvas.clientWidth,h=canvas.clientHeight;if(!w||!h)return;if(canvas.width!==Math.round(w*renderer.getPixelRatio())||canvas.height!==Math.round(h*renderer.getPixelRatio())){renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();}
  // Orbit the camera around the parked car; never move its body around the bumper.
  controls.update();
  renderer.render(scene,camera);
 }
 id=requestAnimationFrame(draw);
 return()=>{disposed=true;car.userData.disposed=true;controls.dispose();cancelAnimationFrame(id);root.removeEventListener('click',click);const materials=new Set();scene.traverse(o=>{o.geometry?.dispose();if(o.material)materials.add(o.material);});materials.forEach(m=>m.dispose());renderer.dispose();renderer.forceContextLoss();};
}
