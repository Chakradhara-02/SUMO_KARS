import {batchStaticSurfaces} from './static-batches.js';
import {FrameQuality} from './frame-quality.js';
import {motionMarker} from './offline-reachability.js';
import {visibleUnsafeStates} from './local-reachability.js';
import {createEgoVehicle} from './vehicle-model.js';
import {landmarkStyle} from './city-scenery.js';
import {TrafficInstances,detailedTraffic} from './traffic-lod.js';
import {cameraProfile} from './camera-profile.js';
import {bridgeLayout} from './bridge-geometry.js';
import {createWheel,advanceWheelDistance,ackermannAngle} from './vehicle-wheels.js';
import {turnSignals} from './driver-assist.js';
import {roadRibbon,roadPitch} from './road-surface.js';
import * as THREE from './vendor/three.module.js';
import {OrbitControls} from './vendor/OrbitControls.js';
import {signalLayout,signalAspect,signalSeconds,crossingLayout} from './signal-layout.js';
import {cityTrajectoryPoints,frameReachability} from './city-overlays.js';

// SUMO is x/y on the ground. Three.js is x/y/z with y vertical.
const point = (x, y, height=0) => new THREE.Vector3(x, height, -y);
const laneY = lane => -8 + lane*3.2;
const palette = {ego:0x1267de, traffic:0xa9afb8, lead:0x8d9cac, obstacle:0xe7a35d, path:0x2787ff};

export class SimulationScene {
  constructor(canvas, onSelect, onInspect) {
    this.canvas=canvas; this.onSelect=onSelect; this.onInspect=onInspect;
    this.frameQuality=new FrameQuality();
    this.renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:false});
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,1.75));
    this.renderer.outputColorSpace=THREE.SRGBColorSpace;
    this.renderer.toneMapping=THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure=1.05;
    this.scene=new THREE.Scene(); this.scene.background=new THREE.Color(0xf1f3f5);
    this.scene.fog=new THREE.FogExp2(0xf1f3f5,.0035);
    this.camera=new THREE.PerspectiveCamera(43,1,.1,4500);
    this.controls=new OrbitControls(this.camera,canvas);
    this.controls.enableDamping=true; this.controls.dampingFactor=.09;
    this.controls.maxPolarAngle=Math.PI*.49; this.controls.minDistance=8; this.controls.maxDistance=2600;
    this.controls.addEventListener('start',()=>{this.follow=false;});
    this.scene.add(new THREE.HemisphereLight(0xffffff,0x98a0ab,2.8));
    const sun=new THREE.DirectionalLight(0xffffff,2.5);sun.position.set(-40,100,40);this.scene.add(sun);
    this.road=new THREE.Group();this.scene.add(this.road);
    this.environment=new THREE.Group();this.actors=new THREE.Group();this.overlay=new THREE.Group();
    this.road.add(this.environment,this.actors,this.overlay);this.trafficInstances=new TrafficInstances(this.road);
    this.localReachable=new THREE.Group();this.road.add(this.localReachable);this.localPointClouds=[];
    for(const color of [0x8bd3aa,0xeb8792]){const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.BufferAttribute(new Float32Array(4096*3),3).setUsage(THREE.DynamicDrawUsage));geometry.setDrawRange(0,0);const cloud=new THREE.Points(geometry,new THREE.PointsMaterial({color,size:6,sizeAttenuation:false,depthWrite:false,depthTest:color!==0xeb8792,transparent:true,opacity:.95}));cloud.renderOrder=color===0xeb8792?30:20;cloud.frustumCulled=false;this.localReachable.add(cloud);this.localPointClouds.push(cloud);}
    this.offlineReachableEnabled=true;this.offlineCloud=new THREE.Points(new THREE.BufferGeometry(),new THREE.PointsMaterial({color:0xb9a9e3,size:3,sizeAttenuation:false,transparent:true,opacity:.55,depthWrite:false}));this.offlineCloud.geometry.setAttribute('position',new THREE.BufferAttribute(new Float32Array(4096*3),3).setUsage(THREE.DynamicDrawUsage));this.offlineCloud.geometry.setDrawRange(0,0);this.offlineCloud.renderOrder=10;this.offlineCloud.frustumCulled=false;this.localReachable.add(this.offlineCloud);
    this.candidateLines=new THREE.LineSegments(new THREE.BufferGeometry(),new THREE.LineBasicMaterial({color:0x98a9b4,transparent:true,opacity:.38,depthWrite:false}));this.candidateLines.geometry.setAttribute('position',new THREE.BufferAttribute(new Float32Array(8192*3),3).setUsage(THREE.DynamicDrawUsage));this.candidateLines.geometry.setDrawRange(0,0);this.candidateLines.frustumCulled=false;this.localReachable.add(this.candidateLines);
    this.blockedCandidateLines=new THREE.LineSegments(new THREE.BufferGeometry(),new THREE.LineBasicMaterial({color:0xf1bdc6,transparent:true,opacity:.7,depthWrite:false}));this.blockedCandidateLines.geometry.setAttribute('position',new THREE.BufferAttribute(new Float32Array(2048*3),3).setUsage(THREE.DynamicDrawUsage));this.blockedCandidateLines.geometry.setDrawRange(0,0);this.blockedCandidateLines.frustumCulled=false;this.localReachable.add(this.blockedCandidateLines);
    this.reachable=new THREE.Group();this.sensors=new THREE.Group();this.road.add(this.reachable,this.sensors);
    this.cityTrip=new THREE.Group();this.road.add(this.cityTrip);this.parkingTarget=new THREE.Group();this.road.add(this.parkingTarget);
    this.selectedEndpointCloud=new THREE.Points(new THREE.BufferGeometry(),new THREE.PointsMaterial({color:0x2787ff,size:13,sizeAttenuation:false,depthTest:false,depthWrite:false,transparent:true,opacity:1}));this.selectedEndpointCloud.geometry.setAttribute('position',new THREE.BufferAttribute(new Float32Array(3),3));this.selectedEndpointCloud.geometry.setDrawRange(0,0);this.selectedEndpointCloud.renderOrder=40;this.localReachable.add(this.selectedEndpointCloud);
    this.cityPathGeometry=new THREE.BufferGeometry();this.cityPathCoordinates=new Float32Array(512*6);
    this.cityPathGeometry.setAttribute('position',new THREE.BufferAttribute(this.cityPathCoordinates,3).setUsage(THREE.DynamicDrawUsage));
    const cityIndices=[];for(let i=0;i<511;i++){const n=i*2;cityIndices.push(n,n+1,n+2,n+1,n+3,n+2);}this.cityPathGeometry.setIndex(cityIndices);this.cityPathGeometry.setDrawRange(0,0);
    this.cityPath=new THREE.Mesh(this.cityPathGeometry,new THREE.MeshBasicMaterial({color:palette.path,side:THREE.DoubleSide}));this.cityPath.frustumCulled=false;this.road.add(this.cityPath);
    this.reachableEnabled=true;this.sensorsEnabled=true;
    this.actorMeshes=new Map();this.box=new THREE.BoxGeometry(1,1,1);
    this.materials=new Map();this.preset='chase';this.follow=true;this.layers=true;
    this.frame={};this.planKey='';this.selectedId=null;
    this.raycaster=new THREE.Raycaster();this.raycaster.params.Points.threshold=1;
    this.pointer=new THREE.Vector2();
    canvas.addEventListener('pointerdown',e=>{this.down={x:e.clientX,y:e.clientY};});
    canvas.addEventListener('pointerup',e=>{
      if(!this.down||Math.hypot(e.clientX-this.down.x,e.clientY-this.down.y)>5)return;
      this.pick(e);
    });
    this.setCamera('chase');
    canvas.addEventListener('webglcontextlost',e=>{e.preventDefault();this.onInspect('3D context lost. Use the 2D map or reload to restore it.');});
  }
  material(color,opacity=1) {
    const key=`${color}/${opacity}`;
    if(!this.materials.has(key))this.materials.set(key,new THREE.MeshStandardMaterial({color,roughness:.78,metalness:.14,transparent:opacity<1,opacity,depthWrite:opacity===1}));
    return this.materials.get(key);
  }
  block(group,x,y,z,w,h,d,color,opacity=1) {
    const mesh=new THREE.Mesh(this.box,this.material(color,opacity));
    mesh.position.set(x,y,z);mesh.scale.set(w,h,d);group.add(mesh);return mesh;
  }
  clear(group) {
    while(group.children.length){const child=group.children[0];group.remove(child);
      child.traverse(o=>{if(o.userData.roadsterRoot)o.userData.disposed=true;if(o.geometry&&o.geometry!==this.box)o.geometry.dispose();
        if(o.isInstancedMesh)o.dispose();if(o.material&&!Array.from(this.materials.values()).includes(o.material)){o.material.map?.dispose();o.material.dispose();}});}
  }
  line(group,points,color,opacity=1) {
    if(points.length<2)return;
    const geometry=new THREE.BufferGeometry().setFromPoints(points);
    const object=new THREE.Line(geometry,new THREE.LineBasicMaterial({color,transparent:opacity<1,opacity}));group.add(object);return object;
  }
  setNetwork(network) {
    this.network=network;this.bridgeDecks=[];this.staticParkingActors=[];this.laneShapes=new Map((network.lanes||[]).map(l=>[l.id,l.shape]));this.clear(this.environment);
    this.heightCells=new Map();this.heightCache=new Map();
    for(const lane of network.lanes||[])for(let i=1;i<lane.shape.length;i++){
      const a=lane.shape[i-1],b=lane.shape[i];
      for(let x=Math.floor(Math.min(a[0],b[0])/60)-1;x<=Math.floor(Math.max(a[0],b[0])/60)+1;x++)
      for(let y=Math.floor(Math.min(a[1],b[1])/60)-1;y<=Math.floor(Math.max(a[1],b[1])/60)+1;y++){
        const key=x+','+y;if(!this.heightCells.has(key))this.heightCells.set(key,[]);this.heightCells.get(key).push([a,b]);}}

    this.scene.fog.density=network.city?.00055:.0035;
    this.block(this.environment,network.city?430:500,-.7,network.city?-430:0,1800,1,network.city?1800:650,0xf1f3f5);
    if(network.city){
      const distanceToRoad=(x,y)=>{let best=Infinity;for(const lane of network.lanes||[])for(let i=1;i<lane.shape.length;i++){
        const a=lane.shape[i-1],b=lane.shape[i],dx=b[0]-a[0],dy=b[1]-a[1],u=Math.max(0,Math.min(1,((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy||1)));
        best=Math.min(best,Math.hypot(x-a[0]-dx*u,y-a[1]-dy*u));}return best;};
      for(let x=-150;x<=1000;x+=78)for(let y=-120;y<=1000;y+=83){
        const px=x+Math.sin(x+y)*18,py=y+Math.cos(x-y)*18;if(distanceToRoad(px,py)<35||(network.parking_lots||[]).some(l=>px>l.bounds[0]-22&&px<l.bounds[2]+22&&py>l.bounds[1]-22&&py<l.bounds[3]+22))continue;
        const park=(Math.abs(x+y)%7)<2;
        if(park){this.block(this.environment,px,.02,-py,45,.12,45,0xc2d6b0);
          for(let i=0;i<3;i++){this.block(this.environment,px+i*9-9,1.6,-py,1,3.2,1,0x887c66);
            const tree=new THREE.Mesh(new THREE.SphereGeometry(4,8,6),this.material(0x6a956e));tree.position.set(px+i*9-9,5,-py);this.environment.add(tree);}}
        else{const height=7+Math.abs(Math.sin(x*y))*24;this.block(this.environment,px,height/2,-py,28,height,28,[0x7199b8,0xd7a06f,0x87b29f,0xa796bf,0xc88c8c][Math.abs(x+y)%5]);
          for(let level=4;level<height;level+=4)this.block(this.environment,px,level,-py-14.1,23,1.1,.1,0x728b9b);}
      }

    }
    if(network.city)for(const district of network.districts||[]){
      const canvas=document.createElement('canvas');canvas.width=512;canvas.height=80;const ctx=canvas.getContext('2d');
      ctx.fillStyle='#ffffffdc';ctx.fillRect(0,0,512,80);ctx.fillStyle='#314d60';ctx.font='bold 26px Segoe UI';ctx.textAlign='center';ctx.fillText(district.name,256,49);
      const label=new THREE.Sprite(new THREE.SpriteMaterial({map:new THREE.CanvasTexture(canvas),depthTest:false}));
      label.position.copy(point(district.x,district.y,38));label.scale.set(110,17,1);label.userData.overviewLabel=true;this.environment.add(label);
    }
    for(const junction of network.junctions||[]){
      if(junction.shape.length<3)continue;
      const shape=new THREE.Shape(junction.shape.map(p=>new THREE.Vector2(p[0],p[1])));
      const mesh=new THREE.Mesh(new THREE.ShapeGeometry(shape),this.material(network.city?0x697780:0xd2d7de));
      mesh.rotation.x=-Math.PI/2;mesh.position.y=(junction.shape.reduce((n,p)=>n+(p[2]||0),0)/junction.shape.length)+.015;this.environment.add(mesh);
      if(network.city&&mesh.position.y>1){const slab=new THREE.Mesh(new THREE.ExtrudeGeometry(shape,{depth:.65,bevelEnabled:false,steps:1}),this.material(0x939ea5));slab.rotation.x=-Math.PI/2;slab.position.y=mesh.position.y-.665;this.environment.add(slab);}
    }
    const edgeLaneCounts=new Map();for(const l of network.lanes||[]){const edge=l.id.replace(/_\d+$/,'');edgeLaneCounts.set(edge,(edgeLaneCounts.get(edge)||0)+1);}
    for(const lane of network.lanes||[]){
      if(lane.internal)continue;
      const ribbon=roadRibbon(lane.shape,lane.width),surface=new THREE.BufferGeometry();
      surface.setAttribute('position',new THREE.Float32BufferAttribute(ribbon.positions,3));surface.setIndex(ribbon.indices);surface.computeVertexNormals();
      this.environment.add(new THREE.Mesh(surface,this.material(network.city?0x697780:0xd2d7de)));
      if(network.city&&/(^|__)park_|(^|__)arrival_|^city_mall__|__city_mall_\d+$/.test(lane.id))continue;
      for(let i=1;i<lane.shape.length;i++){
        const a=point(...lane.shape[i-1]),b=point(...lane.shape[i]),length=a.distanceTo(b);
        const road={quaternion:new THREE.Quaternion()};
        road.quaternion.setFromUnitVectors(new THREE.Vector3(1,0,0),b.clone().sub(a).normalize());
        const dx=(b.x-a.x)/length,dz=(b.z-a.z)/length;
        const index=Number(lane.id.split('_').at(-1)),median=network.city&&network.left_hand&&index===(edgeLaneCounts.get(lane.id.replace(/_\d+$/,''))||1)-1;
        const step=median?length:7;
        for(let s=0;s<length;s+=step){
          const size=median?length:Math.min(2.8,length-s),center=s+size/2;
          const mark=this.block(this.environment,a.x+dx*center-dz*lane.width/2,a.y+(b.y-a.y)*Math.min(1,center/length)+.06,a.z+dz*center+dx*lane.width/2,size,.025,median?.16:.13,median?0xf0c54c:0xfffdf2);
          mark.quaternion.copy(road.quaternion);
        }
        if(index===0){const edge=this.block(this.environment,(a.x+b.x)/2+dz*lane.width/2,(a.y+b.y)/2+.055,(a.z+b.z)/2-dx*lane.width/2,length,.025,.12,0xf9fbf5);edge.quaternion.copy(road.quaternion);}
      }
    }
    if(network.city){
      const bridge=bridgeLayout(network);this.bridgeDecks=bridge.decks;
      const span=(a,b,width,height,color,lift=0)=>{const start=point(a[0],a[1],a[2]+lift),end=point(b[0],b[1],b[2]+lift),delta=end.clone().sub(start),mid=start.clone().add(end).multiplyScalar(.5);const mesh=this.block(this.environment,mid.x,mid.y,mid.z,delta.length(),height,width,color);mesh.quaternion.setFromUnitVectors(new THREE.Vector3(1,0,0),delta.normalize());};
      for(const d of bridge.decks)span(d.a,d.b,d.width,d.thickness,0x939ea5,-.4);
      for(const r of bridge.rails){span(r.a,r.b,r.width,r.height,0xc4c9c4,.45);span(r.a,r.b,.18,.14,0x4b5c64,1.16);}
      for(const p of bridge.posts)this.block(this.environment,p.x,p.z+p.height/2,-p.y,.28,p.height,.28,0xe9bf43);
      for(const p of bridge.piers)this.block(this.environment,p.x,p.height/2,-p.y,1.6,p.height,1.6,0xadb5b5);
      for(const c of bridge.caps)span(c.a,c.b,c.width,c.height,0x9ea9ab);
    }
    // Minimal roadside geometry keeps the focus on real traffic and decisions.
    for(const lane of network.lanes||[]){
      if(lane.internal||network.city)continue;
      const pts=lane.shape.map(p=>point(p[0],p[1],.04));
      this.line(this.environment,pts,0xb8c1cb,.45);
    }
    this.signals=[];
    for(const approach of signalLayout(network)){
      const {pole,beamEnd,tangent}=approach;const deck=approach.lanes[0]?.shape.at(-1)?.[2]||0;
      this.block(this.environment,pole.x,3.35+deck,-pole.y,.22,6.7,.22,0x6c7780);
      const a=point(pole.x,pole.y),b=point(beamEnd.x,beamEnd.y),length=a.distanceTo(b);
      const beam=this.block(this.environment,(a.x+b.x)/2,6.65+deck,(a.z+b.z)/2,length,.18,.18,0x6c7780);beam.rotation.y=-Math.atan2(b.z-a.z,b.x-a.x);
      for(const head of approach.heads){
        const group=new THREE.Group();group.position.copy(point(head.x,head.y,deck));group.rotation.y=Math.atan2(-tangent.x,tangent.y);this.environment.add(group);
        this.block(group,0,5.85,0,.8,1.9,.4,0x17212b);
        const bulbs={};for(const [aspect,y]of [['red',6.3],['amber',5.85],['green',5.4]]){
          const bulb=new THREE.Mesh(new THREE.SphereGeometry(.25,12,10),new THREE.MeshBasicMaterial({color:0x293640}));bulb.position.set(0,y,.22);group.add(bulb);bulbs[aspect]=bulb;
        }
        const canvas=document.createElement('canvas');canvas.width=64;canvas.height=64;const ctx=canvas.getContext('2d');ctx.fillStyle='#17212b';ctx.fillRect(0,0,64,64);ctx.fillStyle='#eef4ef';ctx.font='bold 46px Segoe UI';ctx.textAlign='center';ctx.fillText(head.movement.direction?.toLowerCase()==='l'?'←':head.movement.direction?.toLowerCase()==='r'?'→':'↑',32,49);
        const arrow=new THREE.Sprite(new THREE.SpriteMaterial({map:new THREE.CanvasTexture(canvas)}));arrow.position.set(0,4.85,.2);arrow.scale.set(.55,.55,1);group.add(arrow);
        const clockCanvas=document.createElement('canvas');clockCanvas.width=160;clockCanvas.height=96;
          const clockContext=clockCanvas.getContext('2d'),clockTexture=new THREE.CanvasTexture(clockCanvas);
          const countdown=new THREE.Sprite(new THREE.SpriteMaterial({map:clockTexture,depthTest:false}));
          countdown.position.set(0,4.05,.5);countdown.scale.set(.95,.65,1);group.add(countdown);
          this.signals.push({movement:head.movement,bulbs,clockContext,clockTexture,lastClock:''});
      }
      // Stop line and zebra crossing use the incoming approach's orientation.
      if(network.city){
        const normal={x:-tangent.y,y:tangent.x};
        for(const lane of approach.lanes){
          const end=lane.shape.at(-1);
          const stop=this.block(this.environment,end[0]-tangent.x*3,deck+.035,-end[1]+tangent.y*3,lane.width,.02,.25,0xfaf9e8);stop.rotation.y=Math.atan2(normal.y,normal.x);

        }
      }
    }
    if(network.city)for(const approach of signalLayout(network)){
      const crossing=crossingLayout(network,approach);
      for(const p of crossing.stripes){const stripe=this.block(this.environment,p.x,p.z+.055,-p.y,.48,.035,3.2,0xfff9df);stripe.rotation.y=Math.atan2(crossing.normal.y,crossing.normal.x);}
    }
    if(network.city&&network.left_hand){
      const streets=new Set();
      for(const lane of network.lanes||[]){
        if(lane.internal||/(^|__)park_|(^|__)arrival_|^city_mall__|__city_mall_\d+$/.test(lane.id)||!lane.id.endsWith('_0')||lane.shape.some(p=>Math.abs(p[2]||0)>.1)||lane.shape.length>3)continue;
        const edge=lane.id.replace(/_\d+$/,''),pair=edge.split('__').sort().join('__');const drawDivider=!streets.has(pair);streets.add(pair);
        const a=lane.shape[0],b=lane.shape.at(-1),dx=b[0]-a[0],dy=b[1]-a[1],length=Math.hypot(dx,dy);if(!length)continue;
        // Lane 0 is the outer-left lane in the generated left-hand network.
        const nx=-dy/length,ny=dx/length;
        const shift=-lane.width*1.5;

        for(let s=2;s<length;s+=3){
          const curb=this.block(this.environment,a[0]+dx/length*s+nx*lane.width/2,.13,-a[1]-dy/length*s-ny*lane.width/2,1.5,.2,.28,Math.floor(s/3)%2?0xe8c84e:0x353b40);curb.rotation.y=Math.atan2(dy,dx);
        }
      }
    }
    if(network.city)this.buildParkingLots(network.parking_lots||[]);
    this.batchEnvironment();
  }
  buildParkingLots(lots){
    for(const lot of lots){const x=lot.x,y=lot.y,style=landmarkStyle(lot);
      this.block(this.environment,x+39,-.025,-y-24,78,.07,48,0x68727b);
      for(const [cx,cy,w,d] of [[x+39,y+44,78,4],[x+39,y+2,78,2],[x+76,y+24,2,44]])this.block(this.environment,cx,.12,-cy,w,.24,d,0xd6d7cc);
      this.block(this.environment,x+39,lot.kind==='mall'?7:3.5,-y-56,54,lot.kind==='mall'?14:7,18,style.wall);
      this.block(this.environment,x+39,4,-y-46.8,46,4,.15,style.accent);
      for(const slot of lot.slots){
        for(const side of [-1,1])this.block(this.environment,slot.x+side*slot.width/2,.04,-slot.y,.08,.025,slot.length,0xf3f2e9);
        this.block(this.environment,slot.x,.04,-slot.y-slot.length/2,slot.width,.025,.08,0xf3f2e9);
        if(slot.occupied)this.staticParkingActors.push({vehicle_id:'parked_'+lot.id+'_'+slot.id,x:slot.front_x,y:slot.front_y,z:0,heading:180,speed:0,length:4.7,width:1.8});
      }
      const canvas=document.createElement('canvas');canvas.width=512;canvas.height=72;const ctx=canvas.getContext('2d');ctx.fillStyle='#f1f7fa';ctx.font='bold 30px Segoe UI';ctx.textAlign='center';ctx.fillText(lot.name.toUpperCase(),256,47);const sign=new THREE.Mesh(new THREE.PlaneGeometry(46,5),new THREE.MeshBasicMaterial({map:new THREE.CanvasTexture(canvas),transparent:true,depthWrite:false}));sign.position.set(x+39,lot.kind==='mall'?10:5,-y-46.85);this.environment.add(sign);
    }
  }
  batchEnvironment(){
    this.environment.updateMatrixWorld(true);
    const batches=new Map();
    this.environment.traverse(object=>{if(object.isMesh&&object.geometry===this.box){if(!batches.has(object.material))batches.set(object.material,[]);batches.get(object.material).push(object);}});
    const inverse=this.environment.matrixWorld.clone().invert();
    for(const [material,objects]of batches){
      const batch=new THREE.InstancedMesh(this.box,material,objects.length);
      objects.forEach((object,i)=>{batch.setMatrixAt(i,inverse.clone().multiply(object.matrixWorld));object.parent.remove(object);});
      batch.instanceMatrix.needsUpdate=true;batch.computeBoundingSphere();this.environment.add(batch);
    }
    this.staticSurfaceStats=batchStaticSurfaces(this.environment,this.box,new Set(this.materials.values()));
  }
  setParkingSlot(slotId){
    this.selectedParkingSlot=slotId;const lot=this.frame.city?.trip?.parking_lot||this.trip?.parking_lot;if(!lot)return;
    const slot=lot.slots.find(s=>s.id===slotId);this.clear(this.parkingTarget);if(!slot)return;
    const pad=new THREE.Mesh(new THREE.PlaneGeometry(slot.width,slot.length),new THREE.MeshBasicMaterial({color:0x39d6b0,transparent:true,opacity:.35,side:THREE.DoubleSide,depthWrite:false}));pad.rotation.x=-Math.PI/2;pad.position.set(slot.x,.055,-slot.y);this.parkingTarget.add(pad);
    // The only blue parking path is the selected reachable candidate.
  }
  setTrip(trip){
    this.trip=trip;this.clear(this.cityTrip);this.clear(this.parkingTarget);if(!trip)return;
    if(trip.parking_lot)this.setParkingSlot(this.selectedParkingSlot||trip.arrival_bay.slot_id);
    const bay=trip.parking_lot?null:trip.arrival_bay;
    if(bay){const a=bay.heading*Math.PI/180,dx=Math.sin(a),dy=Math.cos(a),cx=bay.x-dx*2.4,cy=bay.y-dy*2.4;
      const pad=this.block(this.cityTrip,cx,(bay.z||0)+.025,-cy,11,.08,3.5,0x789a91);pad.rotation.y=(90-bay.heading)*Math.PI/180;
      const walk=this.block(this.cityTrip,cx-dy*3.3,(bay.z||0)+.11,-cy-dx*3.3,16,.22,2.3,0xd9cdb8);walk.rotation.y=pad.rotation.y;
      for(const offset of [-1.65,1.65]){const line=this.block(this.cityTrip,cx-dy*offset,(bay.z||0)+.075,-cy-dx*offset,10,.03,.1,0xffffff);line.rotation.y=pad.rotation.y;}
    }
    const routeGuide=this.line(this.cityTrip,trip.shape.map(p=>point(p[0],p[1],(p[2]||0)+.08)),0x7895a8,.45);if(routeGuide)routeGuide.userData.routeGuide=true;
    for(const [p,color,label]of [[trip.start,0x169b7d,'START'],[trip.destination,0xe58a45,'DESTINATION']]){
      const pin=new THREE.Mesh(new THREE.RingGeometry(1.2,1.8,24),new THREE.MeshBasicMaterial({color,side:THREE.DoubleSide}));pin.rotation.x=-Math.PI/2;pin.position.copy(point(p.x,p.y,(p.z||0)+.08));this.cityTrip.add(pin);
      const canvas=document.createElement('canvas');canvas.width=512;canvas.height=80;const ctx=canvas.getContext('2d');
      ctx.fillStyle='#ffffffed';ctx.fillRect(0,0,512,80);ctx.fillStyle='#254254';ctx.font='bold 22px Segoe UI';ctx.textAlign='center';ctx.fillText(label+' · '+p.name,256,48);
      const text=new THREE.Sprite(new THREE.SpriteMaterial({map:new THREE.CanvasTexture(canvas)}));text.position.copy(point(p.x,p.y,(p.z||0)+4));text.scale.set(30,4.7,1);text.userData.tripLabel=true;this.cityTrip.add(text);
    }
  }
  roundedBody(group,x,y,l,h,w,color,r=.12) {
    // Extruded, bevelled body keeps the true length/width footprint.
    const shape=new THREE.Shape(),a=-l/2,b=l/2,c=-h/2,d=h/2;
    shape.moveTo(a+r,c);shape.lineTo(b-r,c);shape.quadraticCurveTo(b,c,b,c+r);
    shape.lineTo(b,d-r);shape.quadraticCurveTo(b,d,b-r,d);shape.lineTo(a+r,d);
    shape.quadraticCurveTo(a,d,a,d-r);shape.lineTo(a,c+r);shape.quadraticCurveTo(a,c,a+r,c);
    const bevel=Math.min(.06,w*.04);
    const geometry=new THREE.ExtrudeGeometry(shape,{depth:w-2*bevel,bevelEnabled:true,bevelSegments:3,steps:1,bevelSize:bevel,bevelThickness:bevel,curveSegments:5});
    geometry.translate(0,0,-w/2+bevel);
    const body=new THREE.Mesh(geometry,this.material(color));body.position.set(x,y,0);group.add(body);return body;
  }
  makeActor(actor) {
    const group=new THREE.Group(),ego=actor.vehicle_id==='ego',truck=(actor.length||5)>7,
      color=ego?palette.ego:actor.vehicle_id.startsWith('city_auto_')?0x32965b:/truck|barrier/.test(actor.vehicle_id)?palette.obstacle:actor.vehicle_id==='lead'?palette.lead:this.network?.city?[0x8b9da8,0xc39870,0x789c80,0x9688a8,0xb47e7a][Number(actor.vehicle_id.split('_').at(-1))%5]||palette.traffic:palette.traffic;
    const l=actor.length||5,w=actor.width||1.8,h=truck?2.4:1.35;
    if(w<1){
      this.block(group,-l/2,.5,0,l*.7,.18,.2,color);
      for(const x of [-l*.14,-l*.86]){const wheel=new THREE.Mesh(new THREE.CylinderGeometry(.3,.3,.15,12),this.material(0x252b34));wheel.rotation.x=Math.PI/2;wheel.position.set(x,.3,0);group.add(wheel);}
      this.block(group,-l*.6,.77,0,.7,.12,.3,0x273845);this.block(group,-l*.42,1.02,0,.25,.5,.35,0x57768d);
      const helmet=new THREE.Mesh(new THREE.SphereGeometry(.18,10,8),this.material(0xe5c252));helmet.position.set(-l*.42,1.42,0);group.add(helmet);
      const halo=new THREE.Mesh(new THREE.RingGeometry(.5,.6,20),new THREE.MeshBasicMaterial({color:palette.path,side:THREE.DoubleSide}));halo.rotation.x=-Math.PI/2;halo.position.set(-l/2,.06,0);halo.visible=false;group.add(halo);group.userData.halo=halo;group.userData.actorId=actor.vehicle_id;this.actors.add(group);return group;
    }
    // TraCI front bumper is the origin; all bodywork remains within the footprint.
    if(!ego){
    this.roundedBody(group,-l/2,h*.38,l-.12,h*.5,w-.12,color,.18);
    if(truck){this.roundedBody(group,-l*.65,h*.65,l*.65,h*.7,w-.15,color);this.roundedBody(group,-l*.15,h*.65,l*.25,h*.6,w-.2,0x727f8e);}
    else{
      const roof=new THREE.Shape();roof.moveTo(-l*.82,.6);roof.lineTo(-l*.64,h*.94);roof.quadraticCurveTo(-l*.48,h*1.08,-l*.37,h*.92);roof.lineTo(-l*.22,.6);roof.closePath();
      const cabin=new THREE.ExtrudeGeometry(roof,{depth:w*.78,bevelEnabled:true,bevelSegments:2,bevelSize:.06,bevelThickness:.04,steps:1});cabin.translate(0,0,-w*.39);
      group.add(new THREE.Mesh(cabin,this.material(0x334151)));
      this.roundedBody(group,-l*.52,h*.98,l<3.2?l*.48:l*.22,.065,w*.69,l<3.2?0xe4c942:color,.025);
    }
      group.userData.wheels=[];
      for(const x of [-l*.2,-l*.8])for(const z of actor.vehicle_id.startsWith('city_auto_')&&x>-l*.3?[0]:[-w*.48,w*.48]){
        const wheel=createWheel(x,z,.32,this.material(0x20262d),this.material(0x9aa9b7),x>-l*.3);
        group.add(wheel);group.userData.wheels.push(wheel);
      }
    }else{const model=createEgoVehicle(l,w);group.add(model);group.userData.model=model;group.userData.wheels=model.userData.wheels;}
      group.userData.indicators=[];
      for(const side of ['left','right'])for(const x of [-.08,-l+.08]){
        const material=new THREE.MeshStandardMaterial({color:0x6b512d,emissive:0xff9a12,emissiveIntensity:0});
        const lamp=new THREE.Mesh(new THREE.BoxGeometry(ego?.025:.12,ego?.035:.13,ego?.14:.19),material);
        const front=x>-l/2;
        lamp.position.set(ego?(front?-l*.035:-l+l*.03):x,ego?(front?.40:.61):.68,(side==='left'?-1:1)*w*(ego?.36:.43));group.add(lamp);
        if(ego)lamp.visible=false;
        group.userData.indicators.push({side,lamp});
      }
    if(!ego)for(const z of [-w*.32,w*.32]){this.block(group,-.04,.57,z,.05,.13,.33,0xffffff);this.block(group,-l+.04,.52,z,.05,.12,.32,0xf15b58);}
    // Soft ground contact shadow, independent of expensive dynamic shadow maps.
    const shadow=new THREE.Mesh(new THREE.PlaneGeometry(l,w*1.15),new THREE.MeshBasicMaterial({color:0x3e4652,transparent:true,opacity:.12,depthWrite:false}));
    shadow.rotation.x=-Math.PI/2;shadow.position.set(-l/2,.035,0);group.add(shadow);
    const halo=new THREE.Mesh(new THREE.RingGeometry(w*.72,w*.8,48),new THREE.MeshBasicMaterial({color:palette.path,transparent:true,opacity:.5,side:THREE.DoubleSide}));
    halo.rotation.x=-Math.PI/2;halo.position.set(-l/2,.06,0);halo.visible=ego;group.add(halo);group.userData.halo=halo;
    group.userData.actorId=actor.vehicle_id;this.actors.add(group);return group;
  }
  setFrame(frame,runId='') {
    const resetCamera=this.runId!==runId||!this.frame.ego&&frame.ego;
    this.frame=frame;
    const parkingKey=[frame.city?.parking?.slot_id,frame.city?.parking?.path?.length,frame.city?.parking?.complete].join('/');if(parkingKey!==this.parkingKey){this.parkingKey=parkingKey;this.setParkingSlot(frame.city?.parking?.slot_id||this.selectedParkingSlot);}
    this.runId=runId;if(resetCamera&&frame.ego)this.setCamera(this.preset);
    const key=runId+'/'+(frame.plan_time??frame.raw?.[0]?.t??'empty');
    if(key!==this.planKey){this.planKey=key;this.buildPlanning();}
    this.buildSensors();
    for(const item of this.signals||[]){const {movement,bulbs}=item,aspect=signalAspect(frame.signals,movement);
      for(const [name,bulb]of Object.entries(bulbs))bulb.material.color.setHex(name===aspect?{red:0xff493e,amber:0xffc448,green:0x29e580}[name]:0x26343e);
      const seconds=signalSeconds(frame.signals,movement),key=aspect+'/'+seconds;
      if(item.lastClock!==key){item.lastClock=key;const ctx=item.clockContext;ctx.fillStyle='#101b22';ctx.fillRect(0,0,160,96);ctx.fillStyle={red:'#ff6258',green:'#4cff94',amber:'#ffd04c'}[aspect]||'#8c9aa0';ctx.font='bold 70px monospace';ctx.textAlign='center';ctx.fillText(seconds===null?'--':String(seconds),80,73);item.clockTexture.needsUpdate=true;}
    }
  }
  buildPlanning() {
    this.clear(this.overlay);
    this.clear(this.reachable);
    if(this.frame.city){this.buildCityPlanning();return;}
    const f=this.frame,origin=f.ego?.x??0,baseTime=f.time??0,t=f.trajectory;
    const classes=frameReachability(f);
    for(const [samples,color] of [[classes.unsafe,0xef4444],[classes.safe,0x22c55e]]){
      const geometry=new THREE.BufferGeometry().setFromPoints(samples.filter(n=>n.layer).map(n=>point(n.x,laneY(n.lane),.22)));
      this.reachable.add(new THREE.Points(geometry,new THREE.PointsMaterial({color,size:5,sizeAttenuation:false,depthWrite:false})));
    }
    this.reachable.visible=this.reachableEnabled;
    if(t?.x?.length>1&&t.x.some((x,i)=>Math.abs(x-t.x[0])>1e-6||Math.abs((t.world_y?.[i]??laneY(t.lane[i]))-(t.world_y?.[0]??laneY(t.lane[0])))>1e-6)){
      const pts=t.x.map((x,i)=>point(x,t.world_y?.[i]??laneY(t.lane[i]),.12));
      const curve=new THREE.CurvePath();
      for(let i=1;i<pts.length;i++)if(pts[i].distanceToSquared(pts[i-1])>1e-10)curve.add(new THREE.LineCurve3(pts[i-1],pts[i]));
      const path=new THREE.Mesh(new THREE.TubeGeometry(curve,64,.12,8,false),new THREE.MeshBasicMaterial({color:palette.path}));this.overlay.add(path);
      const ribbonPoints=[];for(let i=0;i<=64;i++){const center=curve.getPoint(i/64),tangent=curve.getTangent(i/64),side=new THREE.Vector3(-tangent.z,0,tangent.x).normalize().multiplyScalar(.8);ribbonPoints.push(center.clone().add(side),center.clone().sub(side));}
      const vertices=[],indices=[];ribbonPoints.forEach(p=>vertices.push(p.x,.065,p.z));for(let i=0;i<64;i++){const n=i*2;indices.push(n,n+1,n+2,n+1,n+3,n+2);}
      const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute(vertices,3));geometry.setIndex(indices);geometry.computeVertexNormals();
      this.overlay.add(new THREE.Mesh(geometry,new THREE.MeshBasicMaterial({color:palette.path,transparent:true,opacity:.2,side:THREE.DoubleSide,depthWrite:false})));
    }
    for(const c of f.constraints||[]){
      if(c.finish<baseTime||c.begin>baseTime+5||c.end<origin-20||c.start>origin+160)continue;
      const start=Math.max(origin-20,c.start),end=Math.min(origin+160,c.end),all=c.lane<0;
      this.block(this.overlay,(start+end)/2,.045,all?4.8:-laneY(c.lane),Math.max(.1,end-start),.025,all?9.6:3.2,c.kind.includes('speed')?0x679de7:c.kind==='marking'?0xe6bc69:0xe58962,.1);
    }
    const labelled=new Set(),actorIds=new Set((f.vehicles||[]).map(v=>v.vehicle_id));
    for(const c of f.constraints||[]){
      if(actorIds.has(c.source)||labelled.has(c.source)||c.kind==='rear_occupancy'||c.end<origin||c.start>origin+140||c.finish<baseTime||c.begin>baseTime)continue;
      labelled.add(c.source);
      const x=Math.max(origin,c.start),z=13;
      this.block(this.overlay,x,1.5,z,.1,3,.1,0x94a0ad);
      const canvas=document.createElement('canvas');canvas.width=384;canvas.height=96;
      const ctx=canvas.getContext('2d');ctx.fillStyle='#ffffff';ctx.fillRect(0,0,384,96);ctx.strokeStyle='#bad4ef';ctx.lineWidth=4;ctx.strokeRect(2,2,380,92);
      ctx.fillStyle='#43617e';ctx.textAlign='center';ctx.font='24px Segoe UI';ctx.fillText(c.kind.includes('speed')?`${Math.round(c.speed*3.6)} km/h · ${c.source}`:c.source,192,57,355);
      const texture=new THREE.CanvasTexture(canvas),label=new THREE.Sprite(new THREE.SpriteMaterial({map:texture,depthWrite:false}));label.position.set(x,3.3,z);label.scale.set(12,3,1);this.overlay.add(label);
      if(c.kind==='spatial'||c.kind==='spatial_temporal')for(const side of [-1,1]){
        const cone=new THREE.Mesh(new THREE.ConeGeometry(.25,.7,12),this.material(0xe7a35d));cone.position.copy(point(x,laneY(c.lane<0?1:c.lane)+side*1.2,.35));this.overlay.add(cone);
      }
    }
    this.overlay.visible=this.layers;
  }
  roadHeight(x,y,reference=0){
    const cacheKey=Math.round(x*5)+','+Math.round(y*5)+','+Math.round(reference);
    if(this.heightCache?.has(cacheKey))return this.heightCache.get(cacheKey);
    let best=Infinity,height=reference;
    for(const [a,b] of this.heightCells?.get(Math.floor(x/60)+','+Math.floor(y/60))||[]){
      const dx=b[0]-a[0],dy=b[1]-a[1],t=Math.max(0,Math.min(1,((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy||1)));
      const z=(a[2]||0)+((b[2]||0)-(a[2]||0))*t,score=Math.hypot(x-a[0]-dx*t,y-a[1]-dy*t)+Math.abs(z-reference)*.7;
      if(score<best){best=score;height=z;}}
    if(this.heightCache?.size>12000)this.heightCache.clear();this.heightCache?.set(cacheKey,height);return height;
  }
  buildCityPlanning(){
    this.line(this.overlay,(this.frame.ego_trace||[]).map(p=>point(p[0],p[1],(p[2]??this.roadHeight(p[0],p[1],this.frame.ego?.z||0))+.1)),0xe8a449,.9);
    this.reachable.visible=this.reachableEnabled;this.overlay.visible=this.layers;
  }
  setLayers(value){this.layers=value;this.overlay.visible=value;this.cityTrip.visible=value;}
  setReachable(value){this.reachableEnabled=value;this.reachable.visible=value;this.localReachable.visible=value&&!!this.frame.city;}
  setOfflineReachable(value){this.offlineReachableEnabled=value;this.offlineCloud.visible=value;}
  setSensors(value){this.sensorsEnabled=value;this.sensors.visible=value;}
  buildSensors(){
    this.clear(this.sensors);const f=this.frame,e=f.ego;if(!e)return;
    const range=f.sensing?.range;if(!range)return;
    const ring=[];for(let i=0;i<=96;i++){const angle=i/96*Math.PI*2;ring.push(point(e.x+Math.cos(angle)*range,e.y+Math.sin(angle)*range,.09));}
    this.line(this.sensors,ring,0x4b9be6,.25);
    for(const v of (f.sensing?.observations||[]).filter(v=>v.id!=='ego').slice(0,14)){
      this.line(this.sensors,[point(e.x,e.y,.25),point(v.x,v.y,.3)],v.source==='IoT'?0x9a7bca:0x4b9be6,.16);
      const halo=new THREE.Mesh(new THREE.RingGeometry(1.5,1.65,24),new THREE.MeshBasicMaterial({color:v.source==='IoT'?0x9a7bca:0x4b9be6,transparent:true,opacity:.4,side:THREE.DoubleSide}));halo.rotation.x=-Math.PI/2;halo.position.copy(point(v.x,v.y,.08));this.sensors.add(halo);
    }
    this.sensors.visible=this.sensorsEnabled;
  }
  setCamera(preset) {
    this.preset=preset;this.follow=['follow','chase'].includes(preset);
    const ego=this.frame.ego,x=ego?.x??50,z=-(ego?.y??-4.8);
    if(preset==='overview'){if(this.network?.city){this.controls.target.set(430,0,-430);this.camera.position.set(430,1900,950);}else{this.controls.target.set(500,0,0);this.camera.position.set(390,580,520);}}
    else if(preset==='chase'){
      const heading=(ego?.heading??90)*Math.PI/180,direction=new THREE.Vector3(Math.sin(heading),0,-Math.cos(heading));
      const base=new THREE.Vector3(x,0,z);
      this.controls.target.copy(base).addScaledVector(direction,13);this.controls.target.y=1;
      this.camera.position.copy(base).addScaledVector(direction,-18);this.camera.position.y=7;
    }
    else{this.controls.target.set(x+24,0,z);this.camera.position.set(x-25,27,z+21);}
    this.controls.update();
  }
  pick(event) {
    const r=this.canvas.getBoundingClientRect();this.pointer.set((event.clientX-r.left)/r.width*2-1,-(event.clientY-r.top)/r.height*2+1);
    this.raycaster.setFromCamera(this.pointer,this.camera);
    const hit=this.raycaster.intersectObjects(this.actors.children,true)[0];if(!hit)return;
    let object=hit.object;while(object&&!object.userData.actorId)object=object.parent;
    if(object?.userData.actorId.startsWith('parked_')){this.onInspect('Occupied parking bay');return;}
    if(object){this.selectedId=object.userData.actorId;this.onSelect(this.selectedId);}
  }

  render(actors,prediction) {
    const now=performance.now(),frameMs=now-(this.renderTime??now),elapsed=Math.min(.1,frameMs/1000);this.renderTime=now;
    const w=this.canvas.clientWidth,h=this.canvas.clientHeight;if(!w||!h)return;
    this.updateLocalReachability(actors,prediction);
    this.updateCityPath(actors.find(a=>a.vehicle_id==='ego'));
    for(const child of this.cityTrip.children){if(child.userData.tripLabel)child.visible=this.preset==='overview';if(child.userData.routeGuide)child.visible=!this.frame.city?.parking?.active;}
    for(const child of this.environment.children)if(child.userData.overviewLabel)child.visible=this.preset==='overview';
    if(this.width!==w||this.height!==h){this.width=w;this.height=h;this.renderer.setSize(w,h,false);this.camera.aspect=w/h;this.camera.updateProjectionMatrix();}
    const focus=actors.find(a=>a.vehicle_id==='ego'),visualActors=[...actors,...(this.staticParkingActors||[])],detail=detailedTraffic(visualActors,focus);
    const ids=new Set(detail.map(a=>a.vehicle_id));this.trafficInstances.update(visualActors.filter(a=>!ids.has(a.vehicle_id)));
    const cap=actors.length>300?Math.min(window.devicePixelRatio||1,1.15):Math.min(window.devicePixelRatio||1,1.5),quality=this.frameQuality.update(frameMs,now,cap);if(this.quality!==quality){this.quality=quality;this.renderer.setPixelRatio(quality);this.width=0;}
    for(const [id,mesh]of this.actorMeshes){if(!ids.has(id)){this.actors.remove(mesh);mesh.traverse(o=>{if(o.userData.roadsterRoot)o.userData.disposed=true;if(o.geometry&&o.geometry!==this.box)o.geometry.dispose();if(o.material&&!Array.from(this.materials.values()).includes(o.material))o.material.dispose();});this.actorMeshes.delete(id);}}
    for(const actor of detail){let mesh=this.actorMeshes.get(actor.vehicle_id);if(!mesh){mesh=this.makeActor(actor);this.actorMeshes.set(actor.vehicle_id,mesh);}
      mesh.position.copy(point(actor.x,actor.y,actor.z||0));
      const wanted=(90-actor.heading)*Math.PI/180;
      mesh.rotation.y=wanted;mesh.rotation.z=roadPitch(this.laneShapes?.get(actor.lane_id),actor.x,actor.y);
      const previousHeading=mesh.userData.previousHeading??actor.heading;
      const change=((actor.heading-previousHeading+540)%360)-180;
      const dynamics=mesh.userData.model?.userData,wheelbase=dynamics?.wheelbase||(actor.length||4.7)*.6;
      const heading=actor.heading*Math.PI/180,cx=actor.x-Math.sin(heading)*(actor.length||4.7)/2,cy=actor.y-Math.cos(heading)*(actor.length||4.7)/2,previousCenter=mesh.userData.previousCenter;
      let distance=previousCenter?(cx-previousCenter.x)*Math.sin(heading)+(cy-previousCenter.y)*Math.cos(heading):0;
      if(Math.hypot(cx-(previousCenter?.x??cx),cy-(previousCenter?.y??cy))>10)distance=0;
      mesh.userData.previousCenter={x:cx,y:cy};
      const steer=Math.abs(distance)>.0001?Math.max(-.55,Math.min(.55,Math.atan(-change*Math.PI/180*wheelbase/distance))):0;
      mesh.userData.previousHeading=actor.heading;
      mesh.userData.steering=(mesh.userData.steering||0)+(steer-(mesh.userData.steering||0))*(1-Math.exp(-8*elapsed));
      for(const wheel of mesh.userData.wheels||[])advanceWheelDistance(wheel,distance,dynamics?.assetState==='ready'?ackermannAngle(wheel,mesh.userData.steering,wheelbase,dynamics.track):mesh.userData.steering);
      if(dynamics?.bodyMotion){const yawRate=change*Math.PI/180/Math.max(.001,elapsed),k=1-Math.exp(-5*elapsed);dynamics.bodyMotion.rotation.x+=(Math.max(-.018,Math.min(.018,actor.speed*yawRate*.002))-dynamics.bodyMotion.rotation.x)*k;dynamics.bodyMotion.rotation.z+=(Math.max(-.012,Math.min(.012,-(actor.acceleration||0)*.002))-dynamics.bodyMotion.rotation.z)*k;}
      if(actor.vehicle_id==='ego')this.canvas.dataset.egoModel=dynamics?.assetState==='ready'?'tesla-roadster':dynamics?.assetState||'loading';
      const signals=turnSignals(actor),blink=Math.floor((this.frame.time||0)*2)%2===0;
      for(const {side,lamp} of mesh.userData.indicators||[]){const on=signals[side]&&blink;if(actor.vehicle_id==='ego')lamp.visible=on;lamp.material.emissiveIntensity=on?2:0;lamp.material.color.setHex(on?0xffac28:0x6b512d);}
      mesh.userData.halo.visible=actor.vehicle_id==='ego'||actor.vehicle_id===this.selectedId;
      if(actor.vehicle_id==='ego'&&this.frame.city?.parking?.complete){mesh.userData.halo.material.color.setHex(0x35d5ae);mesh.userData.halo.scale.setScalar(1+.08*Math.sin(now*.004));}else if(actor.vehicle_id==='ego'){mesh.userData.halo.material.color.setHex(palette.path);mesh.userData.halo.scale.setScalar(1);}
    }
    if(this.follow){const ego=actors.find(a=>a.vehicle_id==='ego');if(ego){
      if(this.preset==='chase'||cameraProfile(ego,this.bridgeDecks).underpass||this.frame.city?.parking?.active){
        const heading=ego.heading*Math.PI/180,direction=new THREE.Vector3(Math.sin(heading),0,-Math.cos(heading));
        const baseProfile=cameraProfile(ego,this.bridgeDecks),reversing=(ego.speed||0)<-.05||this.frame.city?.parking?.gear==='R';
        const profile=reversing?{...baseProfile,behind:24,height:10,target:-2}:baseProfile;
        const base=point(ego.x,ego.y,ego.z||0),target=base.clone().addScaledVector(direction,profile.target),camera=base.clone().addScaledVector(direction,-profile.behind);
        target.y=(ego.z||0)+1.2;camera.y=(ego.z||0)+profile.height;
        if(this.frame.city?.parking?.active){target.copy(base);target.y=1;camera.copy(base).add(new THREE.Vector3(-11,15,12));}
        const damping=1-Math.exp(-10*elapsed);this.controls.target.lerp(target,damping);this.camera.position.lerp(camera,damping);
      }else{
        const desired=point(ego.x+24,ego.y),delta=desired.clone().sub(this.controls.target);
        this.controls.target.add(delta);this.camera.position.add(delta);
      }
    }}
    this.controls.update();this.renderer.render(this.scene,this.camera);
    if(now-(this.lastRenderStats||0)>250){this.lastRenderStats=now;this.canvas.dataset.drawCalls=String(this.renderer.info.render.calls);this.canvas.dataset.renderRatio=String(this.quality);}
  }
  updateLocalReachability(actors,prediction){
    this.localReachable.visible=!!this.frame.city&&this.reachableEnabled;
    if(!this.frame.city)return;
    this.localClasses=prediction;
    if(!prediction||prediction.pending){this.localReachable.visible=false;return;}
    const ego=actors.find(a=>a.vehicle_id==='ego');
    const endpoint=this.localClasses.selectedEndpoint,endpointGeometry=this.selectedEndpointCloud.geometry;
    if(endpoint){const p=motionMarker(endpoint,ego);endpointGeometry.attributes.position.setXYZ(0,p.x,(p.z||0)+.28,-p.y);endpointGeometry.attributes.position.needsUpdate=true;}
    endpointGeometry.setDrawRange(0,endpoint?1:0);this.canvas.dataset.selectedReachablePoint=endpoint?.id||'';this.canvas.dataset.selectedReachableBranch=this.localClasses.selectedBranchId||'';
    const uploadKey=prediction._version+'/'+this.offlineReachableEnabled;
    if(this.lastReachabilityUpload===uploadKey)return;this.lastReachabilityUpload=uploadKey;
    this.offlineCloud.visible=this.offlineReachableEnabled;
    const offlineGeometry=this.offlineCloud.geometry,offlineAttribute=offlineGeometry.attributes.position,offlineCount=Math.min(4096,this.localClasses.offline.length);
    for(let i=0;i<offlineCount;i++){const p=motionMarker(this.localClasses.offline[i],ego);offlineAttribute.setXYZ(i,p.x,(p.z||0)+.11,-p.y);}
    offlineAttribute.needsUpdate=true;offlineGeometry.setDrawRange(0,offlineCount);
    this.canvas.dataset.offlinePoints=String(offlineCount);this.canvas.dataset.reachabilityDirections=this.localClasses.directions.join(',');
    this.canvas.dataset.localSafePoints=String(this.localClasses.safe.length);this.canvas.dataset.localBlockedPoints=String(visibleUnsafeStates(this.localClasses,this.offlineReachableEnabled).length);
    const lineGeometry=this.candidateLines.geometry,lineAttribute=lineGeometry.attributes.position;let lineCount=0;
    for(const branch of this.localClasses.branches)for(let i=1;i<branch.points.length&&lineCount<8190;i++)for(const raw of [branch.points[i-1],branch.points[i]]){const p=motionMarker(raw,ego,branch.direction);lineAttribute.setXYZ(lineCount++,p.x,(p.z||0)+.12,-p.y);}
    lineAttribute.needsUpdate=true;lineGeometry.setDrawRange(0,lineCount);
    const blockedGeometry=this.blockedCandidateLines.geometry,blockedAttribute=blockedGeometry.attributes.position;let blockedCount=0;
    for(const branch of this.localClasses.branches.filter(b=>b.points.at(-1)?.unsafe))for(const raw of branch.points.slice(-2))if(blockedCount<2048){const p=motionMarker(raw,ego,branch.direction);blockedAttribute.setXYZ(blockedCount++,p.x,(p.z||0)+.18,-p.y);}
    blockedAttribute.needsUpdate=true;blockedGeometry.setDrawRange(0,blockedCount);
    for(const [index,samples]of [this.localClasses.safe,visibleUnsafeStates(this.localClasses,this.offlineReachableEnabled)].entries()){
      const geometry=this.localPointClouds[index].geometry,attribute=geometry.attributes.position,count=Math.min(4096,samples.length);
      for(let i=0;i<count;i++){const p=motionMarker(samples[i],ego);attribute.setXYZ(i,p.x,(p.z||0)+.24,-p.y);}
      attribute.needsUpdate=true;geometry.setDrawRange(0,count);
    }
  }
  updateCityPath(ego){
    this.cityPath.visible=!!this.frame.city&&this.layers&&!!ego;if(!this.cityPath.visible)return;
    const direction=(ego.speed||0)<-.05||this.frame.city?.parking?.gear==='R'?-1:1;
    const path=(this.localClasses?.displaySelected||[]).slice(0,512).map(p=>motionMarker({...p,heading:p.heading??ego.heading},ego,p.direction??direction));
    for(let i=0;i<path.length;i++){
      const a=path[Math.max(0,i-1)],b=path[Math.min(path.length-1,i+1)],length=Math.hypot(b.x-a.x,b.y-a.y)||1;
      const nx=-(b.y-a.y)/length*.3,ny=(b.x-a.x)/length*.3;
      this.cityPathCoordinates.set([path[i].x+nx,(path[i].z??this.roadHeight(path[i].x,path[i].y,ego.z||0))+.16,-path[i].y-ny,path[i].x-nx,(path[i].z??this.roadHeight(path[i].x,path[i].y,ego.z||0))+.16,-path[i].y+ny],i*6);
    }
    this.cityPathGeometry.attributes.position.needsUpdate=true;this.cityPathGeometry.setDrawRange(0,Math.max(0,path.length-1)*6);
  }
}
