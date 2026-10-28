from pathlib import Path
p=Path('kars/models.py');s=p.read_text();p.write_text(s)
p=Path('kars/city.py');s=p.read_text().replace('tc.VAR_NEXT_TLS,tc.VAR_POSITION3D)','tc.VAR_NEXT_TLS,tc.VAR_POSITION3D,tc.VAR_SIGNALS)').replace('z=data[tc.VAR_POSITION3D][2]))','z=data[tc.VAR_POSITION3D][2],signals=data.get(tc.VAR_SIGNALS,0)))');p.write_text(s)
p=Path('kars/simulation.py');s=p.read_text().replace('lateral_position=domain.getLateralLanePosition(vehicle_id)))','lateral_position=domain.getLateralLanePosition(vehicle_id),signals=domain.getSignals(vehicle_id)))');p.write_text(s)
p=Path('simulation_ui/scene3d.js');s=p.read_text(encoding='utf-8');s="import {createWheel,advanceWheel} from './vehicle-wheels.js';\nimport {turnSignals} from './driver-assist.js';\nimport {roadRibbon} from './road-surface.js';\n"+s
start=s.index('    for(const x of [-l*.2,-l*.8])for(const z of ');end=s.index('    for(const z of [-w*.32,w*.32])',start)
s=s[:start]+'''      group.userData.wheels=[];
      for(const x of [-l*.2,-l*.8])for(const z of actor.vehicle_id.startsWith('city_auto_')&&x>-l*.3?[0]:[-w*.48,w*.48]){
        const wheel=createWheel(x,z,.32,this.material(0x20262d),this.material(0x9aa9b7),x>-l*.3);
        group.add(wheel);group.userData.wheels.push(wheel);
      }
      group.userData.indicators=[];
      for(const side of ['left','right'])for(const x of [-.08,-l+.08]){
        const material=new THREE.MeshStandardMaterial({color:0x6b512d,emissive:0xff9a12,emissiveIntensity:0});
        const lamp=new THREE.Mesh(new THREE.BoxGeometry(.12,.13,.19),material);
        lamp.position.set(x,.68,(side==='left'?-1:1)*w*.43);group.add(lamp);
        group.userData.indicators.push({side,lamp});
      }
''' +s[end:]
s=s.replace('      mesh.traverse(part=>{if(part.userData.wheel)part.rotation.z-=actor.speed*elapsed/.32;});', '''      const previousHeading=mesh.userData.previousHeading??actor.heading;
      const change=((actor.heading-previousHeading+540)%360)-180;
      const steer=Math.max(-.42,Math.min(.42,-change*Math.PI/180/(Math.max(.03,elapsed)*Math.max(2,actor.speed))*((actor.length||4.7)*.6)));
      mesh.userData.previousHeading=actor.heading;
      mesh.userData.steering=(mesh.userData.steering||0)+(steer-(mesh.userData.steering||0))*(1-Math.exp(-8*elapsed));
      for(const wheel of mesh.userData.wheels||[])advanceWheel(wheel,actor.speed,elapsed,mesh.userData.steering);
      const signals=turnSignals(actor),blink=Math.floor((this.frame.time||0)*2)%2===0;
      for(const {side,lamp} of mesh.userData.indicators||[]){const on=signals[side]&&blink;lamp.material.emissiveIntensity=on?2:0;lamp.material.color.setHex(on?0xffac28:0x6b512d);}''')
s=s.replace('      for(let i=1;i<lane.shape.length;i++){\n        const a=point(...lane.shape[i-1])', '''      const ribbon=roadRibbon(lane.shape,lane.width),surface=new THREE.BufferGeometry();
      surface.setAttribute('position',new THREE.Float32BufferAttribute(ribbon.positions,3));surface.setIndex(ribbon.indices);surface.computeVertexNormals();
      this.environment.add(new THREE.Mesh(surface,this.material(network.city?0x697780:0xd2d7de)));
      for(let i=1;i<lane.shape.length;i++){
        const a=point(...lane.shape[i-1])''')
s=s.replace("        const road=this.block(this.environment,(a.x+b.x)/2,(a.y+b.y)/2-.05,(a.z+b.z)/2,length,.1,lane.width,network.city?0x8f9ba8:0xd2d7de);", "        const road={quaternion:new THREE.Quaternion()};")
p.write_text(s,encoding='utf-8')
