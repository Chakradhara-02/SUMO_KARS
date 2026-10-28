from pathlib import Path
p=Path('simulation_ui/motion.js');s=p.read_text()
s=s.replace('  let left=samples[0],right=samples.at(-1);','  let left=samples[0],right=samples.at(-1),leftIndex=0;')
s=s.replace('left=samples[i-1];right=samples[i];break;','left=samples[i-1];right=samples[i];leftIndex=i-1;break;')
s=s.replace('    const angle=', '    const z=(p.z||0)+((v.z||0)-(p.z||0))*ratio;\n    const angle=')
s=s.replace('      const a=p.heading*Math.PI/180,b=v.heading*Math.PI/180,t=ratio;\n      const m0={x:Math.sin(a)*distance,y:Math.cos(a)*distance},m1={x:Math.sin(b)*distance,y:Math.cos(b)*distance};', '''      const a=p.heading*Math.PI/180,b=v.heading*Math.PI/180,t=ratio;
      // Interpolate rear axles, then reconstruct the front bumper. Rotation about
      // the measured front bumper makes the rear of the car visibly skate sideways.
      const wheelbase=(v.length||4.7)*.78;
      const p0={x:p.x-Math.sin(a)*wheelbase,y:p.y-Math.cos(a)*wheelbase};
      const p1={x:v.x-Math.sin(b)*wheelbase,y:v.y-Math.cos(b)*wheelbase};
      const span=Math.hypot(p1.x-p0.x,p1.y-p0.y);
      let m0={x:Math.sin(a)*span,y:Math.cos(a)*span},m1={x:Math.sin(b)*span,y:Math.cos(b)*span};
      const previous=(samples[leftIndex-1]?.frame.vehicles||[]).find(q=>q.vehicle_id===v.vehicle_id);
      const next=(samples[leftIndex+2]?.frame.vehicles||[]).find(q=>q.vehicle_id===v.vehicle_id);
      // Central secants keep lane-change steering continuous across sample seams.
      if(Math.abs(angle)<12&&p.road_id===v.road_id){
        const tangent=(q,r)=>{const dx=r.x-q.x,dy=r.y-q.y,n=Math.hypot(dx,dy)||1;return{x:dx/n*span,y:dy/n*span};};
        if(previous&&previous.road_id===p.road_id)m0=tangent(previous,v);
        if(next&&next.road_id===v.road_id)m1=tangent(p,next);
      }''')
s=s.replace('h0*p.x+h1*m0.x+h2*v.x+h3*m1.x','h0*p0.x+h1*m0.x+h2*p1.x+h3*m1.x').replace('h0*p.y+h1*m0.y+h2*v.y+h3*m1.y','h0*p0.y+h1*m0.y+h2*p1.y+h3*m1.y')
s=s.replace('(6*t*t-6*t)*p.x','(6*t*t-6*t)*p0.x').replace('(-6*t*t+6*t)*v.x','(-6*t*t+6*t)*p1.x').replace('(6*t*t-6*t)*p.y','(6*t*t-6*t)*p0.y').replace('(-6*t*t+6*t)*v.y','(-6*t*t+6*t)*p1.y')
s=s.replace('      return {...v,x,y,heading:(Math.atan2(dx,dy)*180/Math.PI+360)%360,speed};','''      const yaw=Math.atan2(dx,dy);
      return {...v,x:x+Math.sin(yaw)*wheelbase,y:y+Math.cos(yaw)*wheelbase,z,
        heading:(yaw*180/Math.PI+360)%360,speed};''')
s=s.replace('return {...v,x:p.x+', 'return {...v,z,x:p.x+')
p.write_text(s)
p=Path('kars/city_reachability.py');s=p.read_text().replace("[[float(v) for v in p.split(',')] for p in lane.get('shape').split()]", "[[float(v) for v in p.split(',')[:2]] for p in lane.get('shape').split()]");p.write_text(s)
p=Path('simulation_ui/scene3d.js');s=p.read_text().replace("this.cityPathGeometry.attributes.position.needsUpdate=true;", "this.cityPathGeometry.attributes.position.needsUpdate=true;")
# Road-height queries occur for several hundred preview points per frame: cache lane segments.
s=s.replace('    this.network=network;this.clear(this.environment);', '    this.network=network;this.clear(this.environment);')
p.write_text(s)
