// Physical bridge structure follows the SUMO lane elevations.
const mix=(a,b,t)=>a.map((v,i)=>v+((b[i]||0)-v)*t);
export function bridgeLayout(network){
 const roads=new Map(),ground=(network.lanes||[]).filter(l=>!l.internal&&l.shape.every(p=>(p[2]||0)<1));
 for(const lane of network.lanes||[]){
  if(lane.internal||!lane.shape.some(p=>(p[2]||0)>1))continue;
  const key=lane.id.replace(/_\d+$/,'').split('__').sort().join('__');
  if(!roads.has(key))roads.set(key,[]);roads.get(key).push(lane);
 }
 const decks=[],rails=[],posts=[],piers=[],caps=[];
 const clear=(x,y)=>ground.every(l=>l.shape.slice(1).every((b,i)=>{const a=l.shape[i],dx=b[0]-a[0],dy=b[1]-a[1],t=Math.max(0,Math.min(1,((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy||1)));return Math.hypot(x-a[0]-dx*t,y-a[1]-dy*t)>l.width/2+1.5;}));
 for(const [id,lanes] of roads){
  const ref=lanes[0].shape,aligned=lanes.map(l=>Math.hypot(l.shape[0][0]-ref[0][0],l.shape[0][1]-ref[0][1])<Math.hypot(l.shape.at(-1)[0]-ref[0][0],l.shape.at(-1)[1]-ref[0][1])?l.shape:[...l.shape].reverse());
  const a=[0,1,2].map(i=>aligned.reduce((s,p)=>s+(p[0][i]||0),0)/lanes.length),b=[0,1,2].map(i=>aligned.reduce((s,p)=>s+(p.at(-1)[i]||0),0)/lanes.length);
  const width=lanes.reduce((s,l)=>s+l.width,0),length=Math.hypot(b[0]-a[0],b[1]-a[1]);if(!length)continue;
  const nx=-(b[1]-a[1])/length,ny=(b[0]-a[0])/length;
  let start=0,end=1;if(a[2]<.8)start=(.8-a[2])/(b[2]-a[2]);if(b[2]<.8)end=(.8-a[2])/(b[2]-a[2]);
  const from=mix(a,b,start),to=mix(a,b,end);decks.push({id,a:from,b:to,width,thickness:.65});
  for(const side of [-1,1]){
   const offset=side*(width/2+.15),shift=p=>[p[0]+nx*offset,p[1]+ny*offset,p[2]];
   rails.push({a:shift(from),b:shift(to),width:.32,height:.9});
   for(let d=start*length;d<=end*length;d+=8){const p=shift(mix(a,b,d/length));posts.push({x:p[0],y:p[1],z:p[2],height:1.25});}
  }
  for(let d=22;d<length-16;d+=42){
   const p=mix(a,b,d/length);if(p[2]<4.5)continue;
   const offset=width/2+2.1,points=[-1,1].map(s=>({x:p[0]+nx*s*offset,y:p[1]+ny*s*offset}));
   if(!points.every(q=>clear(q.x,q.y)))continue;
   for(const q of points)piers.push({...q,height:p[2]-1.2});
   caps.push({a:[points[0].x,points[0].y,p[2]-1],b:[points[1].x,points[1].y,p[2]-1],width:2,height:.6});
  }
 }
 return {decks,rails,posts,piers,caps};
}
