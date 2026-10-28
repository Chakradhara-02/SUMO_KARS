import fs from 'node:fs';
import {interpolateActors} from './simulation_ui/motion.js';
const samples=JSON.parse(fs.readFileSync(process.argv[2]||'outputs/v7_saved_motion.json','utf8'));
function corners(v){const a=v.heading*Math.PI/180,fx=Math.sin(a),fy=Math.cos(a),nx=-fy,ny=fx,l=v.length,w=v.width/2;return [[0,-1],[0,1],[l,1],[l,-1]].map(([d,s])=>[v.x-fx*d+nx*s*w,v.y-fy*d+ny*s*w]);}
function intersects(a,b){const aa=corners(a),bb=corners(b);for(const p of [aa,bb])for(let i=0;i<2;i++){const dx=p[i+1][0]-p[i][0],dy=p[i+1][1]-p[i][1],proj=q=>q.map(([x,y])=>-dy*x+dx*y),x=proj(aa),y=proj(bb);if(Math.min(Math.max(...x),Math.max(...y))-Math.max(Math.min(...x),Math.min(...y))<.01)return false;}return true;}
const result={nativeOverlaps:0,renderedOverlaps:0,examples:[]};
function check(actors,type,time){const ego=actors.find(v=>v.vehicle_id==='ego');if(!ego)return;for(const v of actors){if(v===ego||Math.abs(v.z-ego.z)>2||Math.hypot(v.x-ego.x,v.y-ego.y)>15)continue;if(intersects(ego,v)){result[type]++;if(result.examples.length<8)result.examples.push({type,time,ego,other:v});}}}
for(let i=1;i<samples.length-2;i++){
 check(samples[i].frame.vehicles,'nativeOverlaps',samples[i].at/1000);
 for(const t of [.25,.5,.75]){const time=samples[i].at+(samples[i+1].at-samples[i].at)*t;check(interpolateActors(samples.slice(i-1,i+3),time),'renderedOverlaps',time/1000);}
}
fs.writeFileSync(process.argv[3]||'outputs/v7_overlap_audit_before.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));
