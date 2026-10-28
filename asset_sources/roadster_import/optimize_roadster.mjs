import fs from 'node:fs';
import {MeshoptSimplifier as M} from './helpers/meshopt_simplifier.mjs';
await M.ready;
const read=(name,T)=>{const b=fs.readFileSync(new URL(name,import.meta.url));return new T(b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength));};
const positions=read('positions.bin',Float32Array),normals=read('normals.bin',Float32Array),uv=read('uv.bin',Float32Array),indices=read('indices.bin',Uint32Array),components=read('components.bin',Uint32Array);
const attributes=new Float32Array(positions.length/3*5);for(let i=0;i<components.length;i++){attributes.set(normals.subarray(i*3,i*3+3),i*5);attributes.set(uv.subarray(i*2,i*2+2),i*5+3);}
const buckets={body:[],rear_left:[],rear_right:[],front_left:[],front_right:[]};
for(let i=0;i<indices.length;i+=3){const tri=indices.subarray(i,i+3);let key='body';if(components[tri[0]]===1)key='rear_left';else if(components[tri[0]]===2)key='rear_right';else{
 const x=(positions[tri[0]*3]+positions[tri[1]*3]+positions[tri[2]*3])/3,y=(positions[tri[0]*3+1]+positions[tri[1]*3+1]+positions[tri[2]*3+1])/3,z=(positions[tri[0]*3+2]+positions[tri[1]*3+2]+positions[tri[2]*3+2])/3;
 if(Math.abs(x)>.245&&Math.hypot(y-.146,z-.533)<.148)key=x<0?'front_left':'front_right';
 }buckets[key].push(...tri);}
const report={sourceTriangles:indices.length/3,sourceVertices:positions.length/3,parts:{},levels:{}};
for(const [name,source]of Object.entries(buckets)){report.parts[name]=source.length/3;for(const [level,bodyTarget,wheelTarget]of [['drive',30000,3500],['showroom',85000,9000]]){
 const target=name==='body'?bodyTarget:wheelTarget;
 const [result,error]=M.simplifyWithAttributes(new Uint32Array(source),positions,3,attributes,5,[.025,.025,.025,.25,.25],null,target*3,.025,['Permissive']);
 fs.writeFileSync(new URL(`${level}_${name}_indices.bin`,import.meta.url),Buffer.from(result.buffer,result.byteOffset,result.byteLength));
 report.levels[level]??={};report.levels[level][name]={triangles:result.length/3,error};console.log(level,name,result.length/3,error);
}}
fs.writeFileSync(new URL('optimization.json',import.meta.url),JSON.stringify(report,null,2));
