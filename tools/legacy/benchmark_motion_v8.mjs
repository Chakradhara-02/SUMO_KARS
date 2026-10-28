import fs from 'node:fs';
import {interpolateActors as current} from './simulation_ui/motion.js';
import {interpolateActors as previous} from '../release_check_v7/SUMO_KARS_Bridge_City_V7/simulation_ui/motion.js';
const results=[];
for(const count of [100,350,600]){
 const samples=[0,500,1000,1500].map(at=>({at,frame:{vehicles:Array.from({length:count},(_,i)=>({vehicle_id:'car_'+i,x:i*7+at*.01,y:i%3*3.2,heading:90,speed:10,road_id:'road',length:4.7,width:1.8,z:0}))}}));
 function measure(fn){for(let i=0;i<10;i++)fn(samples,750);const start=performance.now();for(let i=0;i<200;i++)fn(samples,750);return performance.now()-start;}
 const oldMs=measure(previous),newMs=measure(current);results.push({vehicles:count,iterations:200,previous_ms:oldMs,current_ms:newMs,speedup:oldMs/newMs});
}
fs.writeFileSync('outputs/v8_motion_benchmark.json',JSON.stringify(results,null,2));console.log(results);
