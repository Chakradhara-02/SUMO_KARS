from pathlib import Path
p=Path('kars/city_routing.py');s=p.read_text();s=s.replace('        self.graph = nx.DiGraph()', '''        self.transitions={}
        lanes={lane.get('id'):lane for edge in root.findall('edge') for lane in edge.findall('lane')}
        for link in root.findall('connection'):
            pair=(link.get('from'),link.get('to'));via=lanes.get(link.get('via'))
            delay=0.;shape=[]
            if via is not None:
                delay=float(via.get('length'))/max(2.,float(via.get('speed')))
                shape=[[float(v) for v in p.split(',')] for p in via.get('shape').split()]
            if link.get('tl'):delay+=3.
            old=self.transitions.get(pair)
            if old is None or delay<old[0]:self.transitions[pair]=(delay,shape)
        self.costs={}
        self.graph = nx.DiGraph()''')
s=s.replace("graph[a][b]['weight'] = costs[b][3]", "graph[a][b]['weight'] = costs[b][3]+self.transitions.get((a,b),(0,[]))[0]")
s=s.replace('        results = []', '        self.costs=costs\n        results = []')
s=s.replace("                    eta = sum(costs[e][1] for e in route)", "                    eta = sum(costs[e][1] for e in route)+sum(self.transitions.get((a,b),(0,[]))[0] for a,b in zip(route,route[1:]))")
s=s.replace("                    shape = [[float(v) for v in p.split(',')] for e in route\n                             for p in self.edges[e].find('lane').get('shape').split()]", "                    shape=[]\n                    for i,e in enumerate(route):\n                        if i:shape.extend(self.transitions.get((route[i-1],e),(0,[]))[1])\n                        shape.extend([[float(v) for v in p.split(',')] for p in self.edges[e].find('lane').get('shape').split()])")
s+='''
    def score(self,route):
        """Use the identical observation snapshot and objective for switch hysteresis."""
        return sum(self.costs[e][3] for e in route)+sum(
            self.transitions.get((a,b),(0,[]))[0] for a,b in zip(route,route[1:]))
'''
p.write_text(s)
p=Path('kars/city.py');s=p.read_text();s=s.replace("    output=Path(output);rng=random.Random(seed)", "    config={**config,'simulation_dt':min(.1,config['simulation_dt'])}\n    output=Path(output);rng=random.Random(seed)")
s=s.replace("manifest.update(city_trip=trip,traffic_target=target,", "manifest.update(city_trip=trip,traffic_target=target,config=config,")
a=s.index('                    def cost(route):');b=s.index('                    if best_route',a)
s=s[:a]+s[b:];s=s.replace("<cost(current)*.88", "<router.score(current)*.88")
s=s.replace("'reason':'Lower measured traffic and distance cost'", "'reason':'Lower traffic, junction delay and distance cost'")
p.write_text(s)
p=Path('simulation_ui/scene3d.js');s=p.read_text(encoding='utf-8')
s=s.replace("network.city?360:500,-.7,network.city?-360:0,1600,1,network.city?1600:650", "network.city?430:500,-.7,network.city?-430:0,1800,1,network.city?1800:650")
s=s.replace('for(let x=-200;x<=950;x+=78)for(let y=-120;y<=950;y+=83)', 'for(let x=-150;x<=1000;x+=78)for(let y=-120;y<=1000;y+=83)')
s=s.replace("      for(const y of [340,380])for(const x of [348,372])", "      for(const y of [380,420])for(const x of [180,360,580])")
# District labels are overview aids; they do not obstruct the chase camera.
needle='    for(const junction of network.junctions||[]){'
insert='''    if(network.city)for(const district of network.districts||[]){
      const canvas=document.createElement('canvas');canvas.width=512;canvas.height=80;const ctx=canvas.getContext('2d');
      ctx.fillStyle='#ffffffdc';ctx.fillRect(0,0,512,80);ctx.fillStyle='#314d60';ctx.font='bold 26px Segoe UI';ctx.textAlign='center';ctx.fillText(district.name,256,49);
      const label=new THREE.Sprite(new THREE.SpriteMaterial({map:new THREE.CanvasTexture(canvas),depthTest:false}));
      label.position.copy(point(district.x,district.y,38));label.scale.set(110,17,1);label.userData.overviewLabel=true;this.environment.add(label);
    }
'''
s=s.replace(needle,insert+needle)
s=s.replace("      for(const child of this.cityTrip.children)if(child.userData.tripLabel)", "      for(const child of this.environment.children)if(child.userData.overviewLabel)child.visible=this.preset==='overview';\n      for(const child of this.cityTrip.children)if(child.userData.tripLabel)")
s=s.replace('this.controls.target.set(360,0,-360);this.camera.position.set(360,900,240)', 'this.controls.target.set(430,0,-430);this.camera.position.set(430,1450,450)')
s=s.replace('this.camera=new THREE.PerspectiveCamera(43,1,.1,3000)', 'this.camera=new THREE.PerspectiveCamera(43,1,.1,4500)')
s=s.replace('this.controls.maxDistance=1500', 'this.controls.maxDistance=2300')
# Raised-road edge barriers and supports are separate from drivable lane surfaces.
needle='    // Minimal roadside geometry'
barriers='''    if(network.city)for(const lane of network.lanes||[]){
      if(lane.internal||!lane.id.endsWith('_0'))continue;
      const raised=lane.shape.some(p=>(p[2]||0)>1);if(!raised)continue;
      const rail=lane.shape.map((p,i)=>{const a=lane.shape[Math.max(0,i-1)],b=lane.shape[Math.min(lane.shape.length-1,i+1)],n=Math.hypot(b[0]-a[0],b[1]-a[1])||1;return point(p[0]-(b[1]-a[1])/n*lane.width*.5,p[1]+(b[0]-a[0])/n*lane.width*.5,(p[2]||0)+.8);});
      this.line(this.environment,rail,0xb8bdc1,.95);
    }
'''
s=s.replace(needle,barriers+needle);p.write_text(s,encoding='utf-8')
p=Path('simulation_ui/app.js');s=p.read_text(encoding='utf-8');s=s.replace('camera={x:360,y:360}', 'camera={x:430,y:430}')
a=s.index('   if(network.city)for(let x=0;');b=s.index("ctx.lineCap='round';",a)
s=s[:a]+'''   if(network.city)for(const d of network.districts||[]){ctx.fillStyle=d.color;ctx.fillRect(X(d.x-50),Y(d.y+45),100*scale,90*scale);ctx.fillStyle='#526577';ctx.font='bold 10px Segoe UI';ctx.textAlign='center';ctx.fillText(d.name,X(d.x),Y(d.y));ctx.textAlign='left';}''' +s[b:]
s=s.replace("'Indian city", "'Straight-road city")
p.write_text(s,encoding='utf-8')
