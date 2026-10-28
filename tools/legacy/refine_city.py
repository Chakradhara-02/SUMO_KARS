from pathlib import Path
p=Path('tests/motion.test.mjs');s=p.read_text();s=s.replace("assert(Math.abs(mid.x-10)<1e-6);assert(Math.abs(mid.y-1.6)<1e-6);", "const yaw=mid.heading*Math.PI/180,axle=4.7*.78;\n assert(Math.abs((mid.x-Math.sin(yaw)*axle)-(10-axle))<1e-6);\n assert(Math.abs((mid.y-Math.cos(yaw)*axle)-1.6)<1e-6);")
s += '''
test('measured elevations interpolate through an underpass ramp',()=>{
 const a=sample(0,0),b=sample(500,5);a.frame.vehicles[0].z=0;b.frame.vehicles[0].z=4;
 assert.equal(interpolateActors([a,b],250)[0].z,2);
});
''';p.write_text(s)
p=Path('tests/test_city.py');s=p.read_text().replace('assert len(streets)==80','assert len(streets)>100').replace("assert all(len(e.findall('lane'))==2 for e in streets)","assert {len(e.findall('lane')) for e in streets}=={2,3}")
s=s.replace("assert frame['city']['routing_engine']=='SUMO city routing'", "assert frame['city']['routing_engine']=='Traffic-aware alternative routes'")
p.write_text(s)
p=Path('simulation_ui/scene3d.js');s=p.read_text(encoding='utf-8')
s=s.replace('    this.network=network;this.clear(this.environment);','''    this.network=network;this.clear(this.environment);
    this.heightCells=new Map();
    for(const lane of network.lanes||[])for(let i=1;i<lane.shape.length;i++){
      const a=lane.shape[i-1],b=lane.shape[i];
      for(let x=Math.floor(Math.min(a[0],b[0])/60)-1;x<=Math.floor(Math.max(a[0],b[0])/60)+1;x++)
      for(let y=Math.floor(Math.min(a[1],b[1])/60)-1;y<=Math.floor(Math.max(a[1],b[1])/60)+1;y++){
        const key=x+','+y;if(!this.heightCells.has(key))this.heightCells.set(key,[]);this.heightCells.get(key).push([a,b]);}}
''')
s=s.replace("    for(const lane of this.network?.lanes||[])for(let i=1;i<lane.shape.length;i++){\n      const a=lane.shape[i-1],b=lane.shape[i],dx=", "    for(const [a,b] of this.heightCells?.get(Math.floor(x/60)+','+Math.floor(y/60))||[]){\n      const dx=")
p.write_text(s,encoding='utf-8')
