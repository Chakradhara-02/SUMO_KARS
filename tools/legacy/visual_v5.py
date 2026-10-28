from pathlib import Path
p=Path('kars/city_infrastructure.py');s=p.read_text().replace("angle=str(90-bay['heading'])", "angle=str((180-bay['heading'])%360)");p.write_text(s)
p=Path('kars/city.py');s=p.read_text();s=s.replace("'destination':next(p for p in CITY_POINTS if p['id']==destination)","'destination':{**next(p for p in CITY_POINTS if p['id']==destination),'x':bay['x'],'y':bay['y'],'z':bay['z']}")
p.write_text(s)
p=Path('simulation_ui/scene3d.js');s=p.read_text(encoding='utf-8').replace("import {signalLayout,signalAspect}","import {signalLayout,signalAspect,signalSeconds,crossingLayout}")
s=s.replace("this.block(group,0,5.85,0,.55,1.5,.32", "this.block(group,0,5.85,0,.8,1.9,.4").replace('SphereGeometry(.17,8,8)','SphereGeometry(.25,12,10)')
s=s.replace("this.signals.push({movement:head.movement,bulbs});", """const clockCanvas=document.createElement('canvas');clockCanvas.width=160;clockCanvas.height=96;
          const clockContext=clockCanvas.getContext('2d'),clockTexture=new THREE.CanvasTexture(clockCanvas);
          const countdown=new THREE.Sprite(new THREE.SpriteMaterial({map:clockTexture,depthTest:false}));
          countdown.position.set(0,4.05,.5);countdown.scale.set(1.8,1.05,1);group.add(countdown);
          this.signals.push({movement:head.movement,bulbs,clockContext,clockTexture,lastClock:''});""")
a=s.index('          ctx.fillStyle=\'#17212b\';ctx.fillRect(0,0,64,64);') if "          ctx.fillStyle='#17212b';ctx.fillRect(0,0,64,64);" in s else -1
# Replace legacy control characters used as arrows with real Unicode arrow escapes.
s=s.replace("?'\\x1b':head.movement.direction?.toLowerCase()==='r'?'\\x1a':'\\x18'", "?'\\u2190':head.movement.direction?.toLowerCase()==='r'?'\\u2192':'\\u2191'")
s=s.replace(chr(27),'\\u2190').replace(chr(26),'\\u2192').replace(chr(24),'\\u2191')
start=s.index('          for(let offset=-lane.width/2+.25;');end=s.index('\n          }',start)+12
s=s[:start]+s[end:]
needle='    if(network.city&&network.left_hand){'
insert="""    if(network.city)for(const approach of signalLayout(network)){
      const crossing=crossingLayout(network,approach);
      for(const p of crossing.stripes){const stripe=this.block(this.environment,p.x,p.z+.055,-p.y,.48,.035,3.2,0xfff9df);stripe.rotation.y=Math.atan2(crossing.normal.y,crossing.normal.x);}
    }
"""
s=s.replace(needle,insert+needle)
old="    for(const {movement,bulbs}of this.signals||[]){const aspect=signalAspect(frame.signals,movement);for(const [name,bulb]of Object.entries(bulbs))bulb.material.color.setHex(name===aspect?{red:0xff493e,amber:0xffc448,green:0x29e580}[name]:0x26343e);}"
new="""    for(const item of this.signals||[]){const {movement,bulbs}=item,aspect=signalAspect(frame.signals,movement);
      for(const [name,bulb]of Object.entries(bulbs))bulb.material.color.setHex(name===aspect?{red:0xff493e,amber:0xffc448,green:0x29e580}[name]:0x26343e);
      const seconds=signalSeconds(frame.signals,movement),key=aspect+'/'+seconds;
      if(item.lastClock!==key){item.lastClock=key;const ctx=item.clockContext;ctx.fillStyle='#101b22';ctx.fillRect(0,0,160,96);ctx.fillStyle={red:'#ff6258',green:'#4cff94',amber:'#ffd04c'}[aspect]||'#8c9aa0';ctx.font='bold 70px monospace';ctx.textAlign='center';ctx.fillText(seconds===null?'--':String(seconds),80,73);item.clockTexture.needsUpdate=true;}
    }"""
assert old in s;s=s.replace(old,new)
# Preview points must be readable at normal chase-camera distances.
s=s.replace("0x13bda3,.3,.9", "0x14d789,.65,1")
s=s.replace("new THREE.PointsMaterial({color,size,transparent:true,opacity,depthWrite:false})", "new THREE.PointsMaterial({color,size,transparent:true,opacity,depthWrite:false,depthTest:false})")
s=s.replace("    this.clear(this.cityTrip);if(!trip)return;", """    this.clear(this.cityTrip);if(!trip)return;
    const bay=trip.arrival_bay;
    if(bay){const a=bay.heading*Math.PI/180,dx=Math.sin(a),dy=Math.cos(a),cx=bay.x-dx*2.4,cy=bay.y-dy*2.4;
      const pad=this.block(this.cityTrip,cx,(bay.z||0)+.025,-cy,11,.08,3.5,0x789a91);pad.rotation.y=(90-bay.heading)*Math.PI/180;
      const walk=this.block(this.cityTrip,cx-dy*3.3,(bay.z||0)+.11,-cy-dx*3.3,16,.22,2.3,0xd9cdb8);walk.rotation.y=pad.rotation.y;
      for(const offset of [-1.65,1.65]){const line=this.block(this.cityTrip,cx-dy*offset,(bay.z||0)+.075,-cy-dx*offset,10,.03,.1,0xffffff);line.rotation.y=pad.rotation.y;}
    }""")
p.write_text(s,encoding='utf-8')
