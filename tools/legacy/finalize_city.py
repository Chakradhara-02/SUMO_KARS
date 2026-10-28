from pathlib import Path
p=Path('tests/test_city_reachability.py');s=p.read_text().replace('from kars.city import build_city_network','from kars.models import ROOT\n\n# Fixed grid fixture for tests that assert exact historical coordinates.\ndef build_city_network():\n    return ROOT/\'sumo/network/city/indian_city.net.xml\'');p.write_text(s)
p=Path('kars/city.py');s=p.read_text().replace("('city_car',13.9", "('city_car',22.2").replace("('city_bus',11,", "('city_bus',18,").replace("('city_truck',10,", "('city_truck',16,").replace("('city_bike',12,", "('city_bike',18,")
s=s.replace("routing_engine='SUMO shortest routes + independent junction and car-following controls'", "routing_engine='Measured traffic + distance alternative routing; SUMO junction and following controls'")
p.write_text(s)
p=Path('kars/city_reachability.py');s=p.read_text().replace("min(13.9,previous['speed']+acceleration)","min(22.2,previous['speed']+acceleration)");p.write_text(s)
p=Path('simulation_ui/scene3d.js');s=p.read_text(encoding='utf-8')
s=s.replace("      mesh.position.copy(point(actor.x,actor.y,actor.z||0));mesh.rotation.y=(90-actor.heading)*Math.PI/180;", """      mesh.position.copy(point(actor.x,actor.y,actor.z||0));
      const wanted=(90-actor.heading)*Math.PI/180;
      if(!mesh.userData.posed){mesh.rotation.y=wanted;mesh.userData.posed=true;}
      else{const delta=Math.atan2(Math.sin(wanted-mesh.rotation.y),Math.cos(wanted-mesh.rotation.y));mesh.rotation.y+=delta*(1-Math.exp(-18*elapsed));}
      mesh.traverse(part=>{if(part.userData.wheel){part.rotation.z-=actor.speed*elapsed/.32;}});""")
s=s.replace("tire.rotation.x=Math.PI/2;tire.position.set", "tire.userData.wheel=true;tire.rotation.x=Math.PI/2;tire.position.set")
s=s.replace("rim.rotation.x=Math.PI/2;rim.position.copy", "rim.userData.wheel=true;rim.rotation.x=Math.PI/2;rim.position.copy")
s=s.replace("    for(const branch of preview?.route_branches||[]){", "    for(const branch of preview?.route_branches||[]){")
s=s.replace("      this.line(this.reachable,(branch.trajectory||[])", "      this.line(this.reachable,(branch.shape||[]).map(p=>point(p[0],p[1],(p[2]||0)+.12)),color,.25);\n      this.line(this.reachable,(branch.trajectory||[])")
# Elevated signal gantries and stop markings follow their incoming road deck.
s=s.replace("const {pole,beamEnd,tangent}=approach;", "const {pole,beamEnd,tangent}=approach;const deck=approach.lanes[0]?.shape.at(-1)?.[2]||0;")
s=s.replace("pole.x,3.35,-pole.y", "pole.x,3.35+deck,-pole.y").replace("(a.x+b.x)/2,6.65,(a.z+b.z)/2", "(a.x+b.x)/2,6.65+deck,(a.z+b.z)/2")
s=s.replace("point(head.x,head.y)","point(head.x,head.y,deck)")
s=s.replace("end[0]-tangent.x*3,.035,", "end[0]-tangent.x*3,deck+.035,").replace("end[0]+normal.x*offset-tangent.x*.7,.038,", "end[0]+normal.x*offset-tangent.x*.7,deck+.038,")
p.write_text(s,encoding='utf-8')
