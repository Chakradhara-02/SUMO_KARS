from pathlib import Path
p=Path('simulation_ui/scene3d.js');s=p.read_text(encoding='utf-8')
a=s.index('    if(network.city)for(let x=0;');b=s.index('    for(const junction',a)
s=s[:a]+'''    if(network.city){
      const distanceToRoad=(x,y)=>{let best=Infinity;for(const lane of network.lanes||[])for(let i=1;i<lane.shape.length;i++){
        const a=lane.shape[i-1],b=lane.shape[i],dx=b[0]-a[0],dy=b[1]-a[1],u=Math.max(0,Math.min(1,((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy||1)));
        best=Math.min(best,Math.hypot(x-a[0]-dx*u,y-a[1]-dy*u));}return best;};
      for(let x=-200;x<=950;x+=78)for(let y=-120;y<=950;y+=83){
        const px=x+Math.sin(x+y)*18,py=y+Math.cos(x-y)*18;if(distanceToRoad(px,py)<35)continue;
        const park=(Math.abs(x+y)%7)<2;
        if(park){this.block(this.environment,px,.02,-py,45,.12,45,0xc2d6b0);
          for(let i=0;i<3;i++){this.block(this.environment,px+i*9-9,1.6,-py,1,3.2,1,0x887c66);
            const tree=new THREE.Mesh(new THREE.SphereGeometry(4,8,6),this.material(0x6a956e));tree.position.set(px+i*9-9,5,-py);this.environment.add(tree);}}
        else{const height=7+Math.abs(Math.sin(x*y))*24;this.block(this.environment,px,height/2,-py,28,height,28,[0xc5cbd3,0xd3ccc3,0xb9c8cc][Math.abs(x+y)%3]);
          for(let level=4;level<height;level+=4)this.block(this.environment,px,level,-py-14.1,23,1.1,.1,0x728b9b);}
      }
      // Bridge supports sit beside the through-road, keeping its lanes clear.
      for(const y of [340,380])for(const x of [348,372])this.block(this.environment,x,3,-y,1.4,6,1.4,0xa2a9ae);
    }
''' +s[b:]
s=s.replace("mesh.rotation.x=-Math.PI/2;mesh.position.y=.015", "mesh.rotation.x=-Math.PI/2;mesh.position.y=(junction.shape.reduce((n,p)=>n+(p[2]||0),0)/junction.shape.length)+.015")
s=s.replace("(a.x+b.x)/2,-.05,(a.z+b.z)/2,length,.1,lane.width", "(a.x+b.x)/2,(a.y+b.y)/2-.05,(a.z+b.z)/2,length,.1,lane.width")
s=s.replace("road.rotation.y=-Math.atan2(b.z-a.z,b.x-a.x);", "road.quaternion.setFromUnitVectors(new THREE.Vector3(1,0,0),b.clone().sub(a).normalize());")
s=s.replace("a.x+dx*(s+1.4)-dz*lane.width/2,.028,a.z", "a.x+dx*(s+1.4)-dz*lane.width/2,a.y+(b.y-a.y)*Math.min(1,(s+1.4)/length)+.028,a.z")
s=s.replace("mark.rotation.y=road.rotation.y;", "mark.quaternion.copy(road.quaternion);")
s=s.replace("if(lane.internal||!lane.id.endsWith('_0'))continue;", "if(lane.internal||!lane.id.endsWith('_0')||lane.shape.some(p=>Math.abs(p[2]||0)>.1)||lane.shape.length>3)continue;")
s=s.replace("mesh.position.copy(point(actor.x,actor.y));", "mesh.position.copy(point(actor.x,actor.y,actor.z||0));")
s=s.replace("const base=point(ego.x,ego.y),target", "const base=point(ego.x,ego.y,ego.z||0),target").replace("target.y=1;camera.y=7;", "target.y=(ego.z||0)+1;camera.y=(ego.z||0)+7;")
# Overlay elevations are projected to the nearest road segment, keeping the underpass separate.
pos=s.index('  buildCityPlanning(){')
s=s[:pos]+'''  roadHeight(x,y,reference=0){
    let best=Infinity,height=reference;
    for(const lane of this.network?.lanes||[])for(let i=1;i<lane.shape.length;i++){
      const a=lane.shape[i-1],b=lane.shape[i],dx=b[0]-a[0],dy=b[1]-a[1],t=Math.max(0,Math.min(1,((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy||1)));
      const z=(a[2]||0)+((b[2]||0)-(a[2]||0))*t,score=Math.hypot(x-a[0]-dx*t,y-a[1]-dy*t)+Math.abs(z-reference)*.7;
      if(score<best){best=score;height=z;}}
    return height;
  }
''' +s[pos:]
s=s.replace("point(s.x,s.y,.22)","point(s.x,s.y,this.roadHeight(s.x,s.y,this.frame.ego?.z||0)+.22)")
s=s.replace("    this.line(this.overlay,(this.frame.ego_trace", "    for(const branch of preview?.route_branches||[]){\n      const color=branch.selected?0x2787ff:[0xa279db,0xe3a14d,0x2ca78c][branch.id%3];\n      this.line(this.reachable,(branch.trajectory||[]).map(p=>point(p.x,p.y,this.roadHeight(p.x,p.y,this.frame.ego?.z||0)+.3)),color,.85);\n    }\n    this.line(this.overlay,(this.frame.ego_trace")
s=s.replace("path[i].x+nx,.16,-path[i].y-ny,path[i].x-nx,.16,-path[i].y+ny", "path[i].x+nx,this.roadHeight(path[i].x,path[i].y,ego.z||0)+.16,-path[i].y-ny,path[i].x-nx,this.roadHeight(path[i].x,path[i].y,ego.z||0)+.16,-path[i].y+ny")
p.write_text(s,encoding='utf-8')
# Route diagnostics and full route alternatives are visible in both displays.
p=Path('simulation_ui/app.js');s=p.read_text(encoding='utf-8');s=s.replace("5 s preview ·", "5 s preview ·")
s=s.replace("${frame.city_reachability.feasible_count} / ${frame.city_reachability.raw_count} feasible samples", "${frame.city_reachability.feasible_count} / ${frame.city_reachability.raw_count} feasible samples · ${frame.city_reachability.route_branches?.length||1} route branches")
s=s.replace("'No feasible corridor';if(chosenVehicle)","'No feasible corridor';if(frame.city){$('candidates').innerHTML=(frame.city.alternatives||[]).map((r,i)=>`<div class=\"candidate ${r.selected?'chosen':''}\"><span>Route ${i+1}${r.selected?' · executing':''}</span><span>${(r.distance/1000).toFixed(2)} km · ${Math.round(r.eta)} s · ${r.traffic} vehicles</span></div>`).join('')||'Measuring route alternatives…';}if(chosenVehicle)")
p.write_text(s,encoding='utf-8')
