import * as THREE from './vendor/three.module.js';
import {OrbitControls} from './vendor/OrbitControls.js';
import {signalLayout,signalAspect} from './signal-layout.js';
import {cityTrajectoryPoints} from './city-overlays.js';

// SUMO is x/y on the ground. Three.js is x/y/z with y vertical.
const point = (x, y, height=0) => new THREE.Vector3(x, height, -y);
const laneY = lane => -8 + lane*3.2;
const palette = {ego:0xfafcff, traffic:0xa9afb8, lead:0x8d9cac, obstacle:0xe7a35d, path:0x2787ff};

export class SimulationScene {
  constructor(canvas, onSelect, onInspect) {
    this.canvas=canvas; this.onSelect=onSelect; this.onInspect=onInspect;
    this.renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:false});
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,1.75));
    this.renderer.outputColorSpace=THREE.SRGBColorSpace;
    this.renderer.toneMapping=THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure=1.05;
    this.scene=new THREE.Scene(); this.scene.background=new THREE.Color(0xf1f3f5);
    this.scene.fog=new THREE.FogExp2(0xf1f3f5,.0035);
    this.camera=new THREE.PerspectiveCamera(43,1,.1,3000);
    this.controls=new OrbitControls(this.camera,canvas);
    this.controls.enableDamping=true; this.controls.dampingFactor=.09;
    this.controls.maxPolarAngle=Math.PI*.49; this.controls.minDistance=8; this.controls.maxDistance=1500;
    this.controls.addEventListener('start',()=>{this.follow=false;});
    this.scene.add(new THREE.HemisphereLight(0xffffff,0x98a0ab,2.8));
    const sun=new THREE.DirectionalLight(0xffffff,2.5);sun.position.set(-40,100,40);this.scene.add(sun);
    this.road=new THREE.Group();this.scene.add(this.road);
    this.environment=new THREE.Group();this.actors=new THREE.Group();this.overlay=new THREE.Group();
    this.road.add(this.environment,this.actors,this.overlay);
    this.reachable=new THREE.Group();this.sensors=new THREE.Group();this.road.add(this.reachable,this.sensors);
    this.cityTrip=new THREE.Group();this.road.add(this.cityTrip);
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
      child.traverse(o=>{if(o.geometry&&o.geometry!==this.box)o.geometry.dispose();
        if(o.isInstancedMesh)o.dispose();if(o.material&&!Array.from(this.materials.values()).includes(o.material)){o.material.map?.dispose();o.material.dispose();}});}
  }
  line(group,points,color,opacity=1) {
    if(points.length<2)return;
    const geometry=new THREE.BufferGeometry().setFromPoints(points);
    const object=new THREE.Line(geometry,new THREE.LineBasicMaterial({color,transparent:opacity<1,opacity}));group.add(object);return object;
  }
  setNetwork(network) {
    this.network=network;this.clear(this.environment);
    this.scene.fog.density=network.city?.00055:.0035;
    this.block(this.environment,network.city?360:500,-.7,network.city?-360:0,1600,1,network.city?1600:650,0xf1f3f5);
    if(network.city)for(let x=0;x<4;x++)for(let y=0;y<4;y++){
      const cx=x*180+90,cy=y*180+90;
      this.block(this.environment,cx,0,-cy,135,.04,135,(x+y)%5===0?0xbfd3b6:0xe4e5df);
      for(let bx=-1;bx<=1;bx+=2)for(let by=-1;by<=1;by+=2){
        const height=8+((x*7+y*3+bx+by+20)%7)*4;
        this.block(this.environment,cx+bx*34,height/2,-cy+by*34,42,height,42,[0xc5cbd3,0xd3ccc3,0xb9c8cc][(x+y)%3]);
      }
    }
    for(const junction of network.junctions||[]){
      if(junction.shape.length<3)continue;
      const shape=new THREE.Shape(junction.shape.map(p=>new THREE.Vector2(p[0],p[1])));
      const mesh=new THREE.Mesh(new THREE.ShapeGeometry(shape),this.material(0xd2d7de));
      mesh.rotation.x=-Math.PI/2;mesh.position.y=.015;this.environment.add(mesh);
    }
    for(const lane of network.lanes||[]){
      if(lane.internal)continue;
      for(let i=1;i<lane.shape.length;i++){
        const a=point(...lane.shape[i-1]),b=point(...lane.shape[i]),length=a.distanceTo(b);
        const road=this.block(this.environment,(a.x+b.x)/2,-.05,(a.z+b.z)/2,length,.1,lane.width,network.city?0x8f9ba8:0xd2d7de);
        road.rotation.y=-Math.atan2(b.z-a.z,b.x-a.x);
        const dx=(b.x-a.x)/length,dz=(b.z-a.z)/length;
        for(let s=0;s<length;s+=7){
          if(network.city&&network.left_hand&&lane.id.endsWith('_1'))continue;
          const mark=this.block(this.environment,a.x+dx*(s+1.4)-dz*lane.width/2,.028,a.z+dz*(s+1.4)+dx*lane.width/2,Math.min(2.8,length-s),.025,.09,0xffffff);
          mark.rotation.y=road.rotation.y;
        }
      }
    }
    // Minimal roadside geometry keeps the focus on real traffic and decisions.
    for(const lane of network.lanes||[]){
      if(lane.internal||network.city)continue;
      const pts=lane.shape.map(p=>point(p[0],p[1],.04));
      this.line(this.environment,pts,0xb8c1cb,.45);
    }
    this.signals=[];
    for(const approach of signalLayout(network)){
      const {pole,beamEnd,tangent}=approach;
      this.block(this.environment,pole.x,3.35,-pole.y,.22,6.7,.22,0x6c7780);
      const a=point(pole.x,pole.y),b=point(beamEnd.x,beamEnd.y),length=a.distanceTo(b);
      const beam=this.block(this.environment,(a.x+b.x)/2,6.65,(a.z+b.z)/2,length,.18,.18,0x6c7780);beam.rotation.y=-Math.atan2(b.z-a.z,b.x-a.x);
      for(const head of approach.heads){
        const group=new THREE.Group();group.position.copy(point(head.x,head.y));group.rotation.y=Math.atan2(-tangent.x,tangent.y);this.environment.add(group);
        this.block(group,0,5.85,0,.55,1.5,.32,0x17212b);
        const bulbs={};for(const [aspect,y]of [['red',6.3],['amber',5.85],['green',5.4]]){
          const bulb=new THREE.Mesh(new THREE.SphereGeometry(.17,8,8),new THREE.MeshBasicMaterial({color:0x293640}));bulb.position.set(0,y,.22);group.add(bulb);bulbs[aspect]=bulb;
        }
        const canvas=document.createElement('canvas');canvas.width=64;canvas.height=64;const ctx=canvas.getContext('2d');ctx.fillStyle='#17212b';ctx.fillRect(0,0,64,64);ctx.fillStyle='#eef4ef';ctx.font='bold 46px Segoe UI';ctx.textAlign='center';ctx.fillText(head.movement.direction?.toLowerCase()==='l'?'←':head.movement.direction?.toLowerCase()==='r'?'→':'↑',32,49);
        const arrow=new THREE.Sprite(new THREE.SpriteMaterial({map:new THREE.CanvasTexture(canvas)}));arrow.position.set(0,4.85,.2);arrow.scale.set(.55,.55,1);group.add(arrow);
        this.signals.push({movement:head.movement,bulbs});
      }
      // Stop line and zebra crossing use the incoming approach's orientation.
      if(network.city){
        const normal={x:-tangent.y,y:tangent.x};
        for(const lane of approach.lanes){
          const end=lane.shape.at(-1);
          const stop=this.block(this.environment,end[0]-tangent.x*3,.035,-end[1]+tangent.y*3,lane.width,.02,.25,0xfaf9e8);stop.rotation.y=Math.atan2(normal.y,normal.x);
          for(let offset=-lane.width/2+.25;offset<lane.width/2;offset+=.8){
            const stripe=this.block(this.environment,end[0]+normal.x*offset-tangent.x*.7,.038,-end[1]-normal.y*offset+tangent.y*.7,.45,.025,2.2,0xfaf9e8);stripe.rotation.y=Math.atan2(normal.y,normal.x);
          }
        }
      }
    }
    if(network.city&&network.left_hand){
      const streets=new Set();
      for(const lane of network.lanes||[]){
        if(lane.internal||!lane.id.endsWith('_0'))continue;
        const edge=lane.id.replace(/_\d+$/,''),pair=edge.split('__').sort().join('__');const drawDivider=!streets.has(pair);streets.add(pair);
        const a=lane.shape[0],b=lane.shape.at(-1),dx=b[0]-a[0],dy=b[1]-a[1],length=Math.hypot(dx,dy);if(!length)continue;
        // Lane 0 is the outer-left lane in the generated left-hand network.
        const nx=-dy/length,ny=dx/length;
        const shift=-lane.width*1.5;
        if(drawDivider){const divider=this.block(this.environment,(a[0]+b[0])/2+nx*shift,.045,-(a[1]+b[1])/2-ny*shift,length,.02,.18,0xe7c344);divider.rotation.y=Math.atan2(dy,dx);}
        for(let s=2;s<length;s+=3){
          const curb=this.block(this.environment,a[0]+dx/length*s+nx*lane.width/2,.13,-a[1]-dy/length*s-ny*lane.width/2,1.5,.2,.28,Math.floor(s/3)%2?0xe8c84e:0x353b40);curb.rotation.y=Math.atan2(dy,dx);
        }
      }
    }
    this.batchEnvironment();
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
  }
  setTrip(trip){
    this.clear(this.cityTrip);if(!trip)return;
    this.line(this.cityTrip,trip.shape.map(p=>point(p[0],p[1],.08)),0x7895a8,.45);
    for(const [p,color,label]of [[trip.start,0x169b7d,'START'],[trip.destination,0xe58a45,'DESTINATION']]){
      const pin=new THREE.Mesh(new THREE.RingGeometry(1.2,1.8,24),new THREE.MeshBasicMaterial({color,side:THREE.DoubleSide}));pin.rotation.x=-Math.PI/2;pin.position.copy(point(p.x,p.y,.08));this.cityTrip.add(pin);
      const canvas=document.createElement('canvas');canvas.width=512;canvas.height=80;const ctx=canvas.getContext('2d');
      ctx.fillStyle='#ffffffed';ctx.fillRect(0,0,512,80);ctx.fillStyle='#254254';ctx.font='bold 22px Segoe UI';ctx.textAlign='center';ctx.fillText(label+' · '+p.name,256,48);
      const text=new THREE.Sprite(new THREE.SpriteMaterial({map:new THREE.CanvasTexture(canvas)}));text.position.copy(point(p.x,p.y,4));text.scale.set(30,4.7,1);text.userData.tripLabel=true;this.cityTrip.add(text);
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
      color=ego?palette.ego:actor.vehicle_id.startsWith('city_auto_')?0x32965b:/truck|barrier/.test(actor.vehicle_id)?palette.obstacle:actor.vehicle_id==='lead'?palette.lead:this.network?.city?[0x2b7ba3,0xc97c38,0x63945e,0x8966ae,0xc05c5a][Number(actor.vehicle_id.split('_').at(-1))%5]||palette.traffic:palette.traffic;
    const l=actor.length||5,w=actor.width||1.8,h=truck?2.4:1.35;
    if(w<1){
      this.block(group,-l/2,.5,0,l*.7,.18,.2,color);
      for(const x of [-l*.14,-l*.86]){const wheel=new THREE.Mesh(new THREE.CylinderGeometry(.3,.3,.15,12),this.material(0x252b34));wheel.rotation.x=Math.PI/2;wheel.position.set(x,.3,0);group.add(wheel);}
      this.block(group,-l*.6,.77,0,.7,.12,.3,0x273845);this.block(group,-l*.42,1.02,0,.25,.5,.35,0x57768d);
      const helmet=new THREE.Mesh(new THREE.SphereGeometry(.18,10,8),this.material(0xe5c252));helmet.position.set(-l*.42,1.42,0);group.add(helmet);
      const halo=new THREE.Mesh(new THREE.RingGeometry(.5,.6,20),new THREE.MeshBasicMaterial({color:palette.path,side:THREE.DoubleSide}));halo.rotation.x=-Math.PI/2;halo.position.set(-l/2,.06,0);halo.visible=false;group.add(halo);group.userData.halo=halo;group.userData.actorId=actor.vehicle_id;this.actors.add(group);return group;
    }
    // TraCI front bumper is the origin; all bodywork remains within the footprint.
    this.roundedBody(group,-l/2,h*.38,l-.12,h*.5,w-.12,color,.18);
    if(truck){this.roundedBody(group,-l*.65,h*.65,l*.65,h*.7,w-.15,color);this.roundedBody(group,-l*.15,h*.65,l*.25,h*.6,w-.2,0x727f8e);}
    else{
      const roof=new THREE.Shape();roof.moveTo(-l*.82,.6);roof.lineTo(-l*.64,h*.94);roof.quadraticCurveTo(-l*.48,h*1.08,-l*.37,h*.92);roof.lineTo(-l*.22,.6);roof.closePath();
      const cabin=new THREE.ExtrudeGeometry(roof,{depth:w*.78,bevelEnabled:true,bevelSegments:2,bevelSize:.06,bevelThickness:.04,steps:1});cabin.translate(0,0,-w*.39);
      group.add(new THREE.Mesh(cabin,this.material(0x334151)));
      this.roundedBody(group,-l*.52,h*.98,l<3.2?l*.48:l*.22,.065,w*.69,l<3.2?0xe4c942:color,.025);
    }
    for(const x of [-l*.2,-l*.8])for(const z of actor.vehicle_id.startsWith('city_auto_')&&x>-l*.3?[0]:[-w*.48,w*.48]){
      const tire=new THREE.Mesh(new THREE.CylinderGeometry(.32,.32,.2,18),this.material(0x252b34));
      tire.rotation.x=Math.PI/2;tire.position.set(x,.32,z);group.add(tire);
      const rim=new THREE.Mesh(new THREE.CylinderGeometry(.18,.18,.215,12),this.material(0x87929f));rim.rotation.x=Math.PI/2;rim.position.copy(tire.position);group.add(rim);
    }
    for(const z of [-w*.32,w*.32]){this.block(group,-.04,.57,z,.05,.13,.33,0xffffff);this.block(group,-l+.04,.52,z,.05,.12,.32,0xf15b58);}
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
    this.runId=runId;if(resetCamera&&frame.ego)this.setCamera(this.preset);
    const key=runId+'/'+(frame.plan_time??frame.raw?.[0]?.t??'empty');
    if(key!==this.planKey){this.planKey=key;this.buildPlanning();}
    this.buildSensors();
    for(const {movement,bulbs}of this.signals||[]){const aspect=signalAspect(frame.signals,movement);for(const [name,bulb]of Object.entries(bulbs))bulb.material.color.setHex(name===aspect?{red:0xff493e,amber:0xffc448,green:0x29e580}[name]:0x26343e);}
  }
  buildPlanning() {
    this.clear(this.overlay);
    this.clear(this.reachable);
    if(this.frame.city){this.buildCityPlanning();return;}
    const f=this.frame,origin=f.ego?.x??0,baseTime=f.time??0,t=f.trajectory;
    // Ground projections of actual samples, grouped by future step and lane.
    // These strips show extents, not a claim of continuous collision-free area.
    for(const [samples,color,opacity]of [[f.raw||[],0x8b98a8,.04],[f.adjusted||[],0x35bdb5,.08]]){
      const groups=new Map();for(const n of samples){if(!n.layer)continue;const key=n.layer+'/'+n.lane;if(!groups.has(key))groups.set(key,[]);groups.get(key).push(n);}
      for(const nodes of groups.values()){
        const first=nodes[0],start=Math.min(...nodes.map(n=>n.x))-(f.ego?.length||5),end=Math.max(...nodes.map(n=>n.x));
        this.block(this.reachable,(start+end)/2,.022+first.layer*.002,-laneY(first.lane),Math.max(.3,end-start),.004,2.75,color,opacity);
        this.line(this.reachable,[point(start,laneY(first.lane)-1.36,.07),point(end,laneY(first.lane)-1.36,.07),point(end,laneY(first.lane)+1.36,.07),point(start,laneY(first.lane)+1.36,.07),point(start,laneY(first.lane)-1.36,.07)],color,.3);
      }
    }
    this.reachable.visible=this.reachableEnabled;
    if(t?.x?.length>1){
      const pts=t.x.map((x,i)=>point(x,t.world_y?.[i]??laneY(t.lane[i]),.12));
      const curve=new THREE.CatmullRomCurve3(pts);
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
  buildCityPlanning(){
    const preview=this.frame.city_reachability;
    for(const [samples,color,size,opacity]of [[preview?.raw||[],0x7a8e9d,.2,.35],[preview?.feasible||[],0x13bda3,.3,.9]]){
      if(!samples.length)continue;
      const geometry=new THREE.BufferGeometry().setFromPoints(samples.filter(s=>s.time>=this.frame.time).map(s=>point(s.x,s.y,.22)));
      this.reachable.add(new THREE.Points(geometry,new THREE.PointsMaterial({color,size,transparent:true,opacity,depthWrite:false})));
    }
    this.line(this.overlay,(this.frame.ego_trace||[]).map(p=>point(p[0],p[1],.1)),0xe8a449,.9);
    this.reachable.visible=this.reachableEnabled;this.overlay.visible=this.layers;
  }
  setLayers(value){this.layers=value;this.overlay.visible=value;this.cityTrip.visible=value;}
  setReachable(value){this.reachableEnabled=value;this.reachable.visible=value;}
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
    if(preset==='overview'){if(this.network?.city){this.controls.target.set(360,0,-360);this.camera.position.set(360,900,240);}else{this.controls.target.set(500,0,0);this.camera.position.set(390,580,520);}}
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
    if(object){this.selectedId=object.userData.actorId;this.onSelect(this.selectedId);}
  }

  render(actors) {
    const now=performance.now(),elapsed=Math.min(.1,(now-(this.renderTime??now))/1000);this.renderTime=now;
    const w=this.canvas.clientWidth,h=this.canvas.clientHeight;if(!w||!h)return;
    this.updateCityPath(actors.find(a=>a.vehicle_id==='ego'));
    for(const child of this.cityTrip.children)if(child.userData.tripLabel)child.visible=this.preset==='overview';
    if(this.width!==w||this.height!==h){this.width=w;this.height=h;this.renderer.setSize(w,h,false);this.camera.aspect=w/h;this.camera.updateProjectionMatrix();}
    const ids=new Set(actors.map(a=>a.vehicle_id));
    for(const [id,mesh]of this.actorMeshes){if(!ids.has(id)){this.actors.remove(mesh);mesh.traverse(o=>{if(o.geometry&&o.geometry!==this.box)o.geometry.dispose();if(o.material&&!Array.from(this.materials.values()).includes(o.material))o.material.dispose();});this.actorMeshes.delete(id);}}
    for(const actor of actors){let mesh=this.actorMeshes.get(actor.vehicle_id);if(!mesh){mesh=this.makeActor(actor);this.actorMeshes.set(actor.vehicle_id,mesh);}
      mesh.position.copy(point(actor.x,actor.y));mesh.rotation.y=(90-actor.heading)*Math.PI/180;
      mesh.userData.halo.visible=actor.vehicle_id==='ego'||actor.vehicle_id===this.selectedId;
    }
    if(this.follow){const ego=actors.find(a=>a.vehicle_id==='ego');if(ego){
      if(this.preset==='chase'){
        const heading=ego.heading*Math.PI/180,direction=new THREE.Vector3(Math.sin(heading),0,-Math.cos(heading));
        const base=point(ego.x,ego.y),target=base.clone().addScaledVector(direction,13),camera=base.clone().addScaledVector(direction,-18);
        target.y=1;camera.y=7;
        const damping=1-Math.exp(-10*elapsed);this.controls.target.lerp(target,damping);this.camera.position.lerp(camera,damping);
      }else{
        const desired=point(ego.x+24,ego.y),delta=desired.clone().sub(this.controls.target);
        this.controls.target.add(delta);this.camera.position.add(delta);
      }
    }}
    this.controls.update();this.renderer.render(this.scene,this.camera);
  }
  updateCityPath(ego){
    this.cityPath.visible=!!this.frame.city&&this.layers&&!!ego;if(!this.cityPath.visible)return;
    const path=cityTrajectoryPoints(this.frame,ego).slice(0,512);
    for(let i=0;i<path.length;i++){
      const a=path[Math.max(0,i-1)],b=path[Math.min(path.length-1,i+1)],length=Math.hypot(b.x-a.x,b.y-a.y)||1;
      const nx=-(b.y-a.y)/length*.3,ny=(b.x-a.x)/length*.3;
      this.cityPathCoordinates.set([path[i].x+nx,.16,-path[i].y-ny,path[i].x-nx,.16,-path[i].y+ny],i*6);
    }
    this.cityPathGeometry.attributes.position.needsUpdate=true;this.cityPathGeometry.setDrawRange(0,Math.max(0,path.length-1)*6);
  }
}
