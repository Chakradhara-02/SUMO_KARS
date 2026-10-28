import fs from 'node:fs';
import {performance} from 'node:perf_hooks';
import {localReachability} from '../simulation_ui/local-reachability.js';
const ego={vehicle_id:'ego',x:100,y:4.8,z:0,heading:90,speed:12,speed_limit:13.9,length:4.7,width:1.8,road_id:'east',lane_id:'east_0',acceleration:0};
const actors=[ego,...Array.from({length:599},(_,i)=>({...ego,vehicle_id:'traffic_'+i,x:ego.x+((i%30)-15)*32,y:ego.y+(Math.floor(i/30)-10)*32+16,speed:6}))];
const frame={time:10,ego,city:{trip:{edges:['east']},route_shape:[[100,4.8],[300,4.8]]},city_reachability:{trajectory:[]},sensing:{range:120}};
const network={lanes:[{id:'east_0',shape:[[0,4.8,0],[2000,4.8,0]],width:3.2},{id:'east_1',shape:[[0,1.6,0],[2000,1.6,0]],width:3.2}]};
for(let i=0;i<15;i++)localReachability(frame,actors,network);
const durations=[];let result;
for(let i=0;i<60;i++){const begin=performance.now();result=localReachability(frame,actors,network);durations.push(performance.now()-begin);}
durations.sort((a,b)=>a-b);
const report={actors:actors.length,iterations:durations.length,median_ms:durations[30],p95_ms:durations[57],max_ms:durations.at(-1),safe_points:result.safe.length,offline_points:result.offline.length};
console.log(JSON.stringify(report));
if(process.argv[2]){fs.mkdirSync(new URL('../artifacts/performance/',import.meta.url),{recursive:true});fs.writeFileSync(new URL('../artifacts/performance/'+process.argv[2],import.meta.url),JSON.stringify(report,null,2));}

