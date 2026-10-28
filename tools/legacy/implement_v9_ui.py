from pathlib import Path

root=Path(__file__).parent
def edit(name,old,new):
 p=root/name;s=p.read_text(encoding='utf-8');assert old in s,(name,old[:90]);p.write_text(s.replace(old,new),encoding='utf-8')

edit('simulation_ui/scene3d.js',"import {TrafficInstances", "import {createEgoVehicle} from './vehicle-model.js';\nimport {landmarkStyle} from './city-scenery.js';\nimport {TrafficInstances")
edit('simulation_ui/scene3d.js','ego:0xfafcff','ego:0x1267de')
edit('simulation_ui/scene3d.js','[0xc5cbd3,0xd3ccc3,0xb9c8cc]','[0x7199b8,0xd7a06f,0x87b29f,0xa796bf,0xc88c8c]')
edit('simulation_ui/scene3d.js','[Math.abs(x+y)%3]','[Math.abs(x+y)%5]')
edit('simulation_ui/scene3d.js',"for(const lot of lots){const x=lot.x,y=lot.y;", "for(const lot of lots){const x=lot.x,y=lot.y,style=landmarkStyle(lot);")
edit('simulation_ui/scene3d.js',"lot.kind==='mall'?0xcdd9e0:0xbcccd2",'style.wall')
edit('simulation_ui/scene3d.js','46,4,.15,0x43697c','46,4,.15,style.accent')
old="const sign=new THREE.Sprite(new THREE.SpriteMaterial({map:new THREE.CanvasTexture(canvas)}));sign.position.set(x+39,lot.kind==='mall'?15:9,-y-46);sign.scale.set(28,4,1);this.environment.add(sign);"
new="const sign=new THREE.Mesh(new THREE.PlaneGeometry(46,5),new THREE.MeshBasicMaterial({map:new THREE.CanvasTexture(canvas),transparent:true,depthWrite:false}));sign.position.set(x+39,lot.kind==='mall'?10:5,-y-46.85);this.environment.add(sign);"
edit('simulation_ui/scene3d.js',old,new)
p=root/'simulation_ui/scene3d.js';s=p.read_text(encoding='utf-8');a=s.index('    this.roundedBody(group,-l/2');b=s.index('      group.userData.indicators=[];',a)
s=s[:a]+"    if(!ego){\n"+s[a:b]+"    }else{const model=createEgoVehicle(l,w);group.add(model);group.userData.wheels=model.userData.wheels;}\n"+s[b:];p.write_text(s,encoding='utf-8')
edit('simulation_ui/parking-showroom.js','camera.position.set(4.6,2.6,5.8)','camera.position.set(4.6,2.6,-5.8)')
edit('simulation_ui/parking-showroom.js','goals.door*1.05','-goals.door*1.05')

edit('simulation_ui/parking-ui.js','const escape=',"import {mountShowroom} from './parking-showroom.js';\nconst escape=")
edit('simulation_ui/parking-ui.js','let key=\'\';',"let key='',html='',disposeShowroom=null;")
edit('simulation_ui/parking-ui.js',"if(!view)return;", "if(!view){disposeShowroom?.();disposeShowroom=null;html='';return;}")
old="if(!console.hidden){console.dataset.stage=view.stage;console.innerHTML=view.html;}"
new="""if(!console.hidden){console.dataset.stage=view.stage;
   if(html!==view.html){disposeShowroom?.();disposeShowroom=null;html=view.html;console.innerHTML=view.html;
    if(view.stage==='parked'){const map=console.querySelector('.parking-map');map.outerHTML='<div class="parking-showroom"><canvas aria-label="Animated parked ego vehicle"></canvas><div class="car-controls"><button data-car-panel="door" aria-pressed="false">Driver door</button><button data-car-panel="hood" aria-pressed="false">Front boot</button><button data-car-panel="boot" aria-pressed="false">Boot</button></div><p>Vehicle secured · Explore your car</p></div><details class="parked-bays"><summary>View parking bay</summary>'+map.outerHTML+'</details>';disposeShowroom=mountShowroom(console.querySelector('.parking-showroom'));}
   }
  }else if(disposeShowroom){disposeShowroom();disposeShowroom=null;html='';}"""
edit('simulation_ui/parking-ui.js',old,new)
edit('simulation_ui/app.js',"import {cityTrajectoryPoints}","import {drawCityLots} from './city-scenery.js';\nimport {cityTrajectoryPoints}")
edit('simulation_ui/app.js',"if(showReachable){for(const [samples,color,stroke]", "if(network.city)drawCityLots(ctx,network.parking_lots,X,Y,scale);\n if(showReachable){for(const [samples,color,stroke]")
edit('simulation_ui/app.js',"'Parking manoeuvre · checked private-lot path'","(frame.city.parking.complete?'Parking complete · '+frame.city.parking.slot_id:'Automatic parking · '+(frame.city.parking.slot_id||'Choose a bay'))")
edit('simulation_ui/app.js',"' assessed';}","' routes · traffic + distance';}")
edit('simulation_ui/index.html','20261017-parking-city-v8','20261017-flow-city-v9')
