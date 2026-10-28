// One joined surface per lane avoids rectangular cracks on curved roads.
export function roadRibbon(shape,width){
  const positions=[],indices=[];
  for(let i=0;i<shape.length;i++){
    const a=shape[Math.max(0,i-1)],p=shape[i],b=shape[Math.min(shape.length-1,i+1)];
    const normal=(u,v)=>{const dx=v[0]-u[0],dy=v[1]-u[1],n=Math.hypot(dx,dy)||1;return[-dy/n,dx/n];};
    const before=normal(a,p),after=normal(p,b);
    if(i===0){before[0]=after[0];before[1]=after[1];}
    if(i===shape.length-1){after[0]=before[0];after[1]=before[1];}
    const n=Math.hypot(before[0]+after[0],before[1]+after[1])||1;
    const nx=(before[0]+after[0])/n,ny=(before[1]+after[1])/n;
    const half=(width/2+.015)/Math.max(.65,nx*after[0]+ny*after[1]);
    positions.push(p[0]+nx*half,(p[2]||0)-.01,-p[1]-ny*half,
                   p[0]-nx*half,(p[2]||0)-.01,-p[1]+ny*half);
    if(i){const j=(i-1)*2;indices.push(j,j+1,j+2,j+1,j+3,j+2);}
  }
  return {positions,indices};
}


export function roadPitch(shape,x,y){
 let best=Infinity,pitch=0;
 for(let i=1;i<(shape||[]).length;i++){
  const a=shape[i-1],b=shape[i],dx=b[0]-a[0],dy=b[1]-a[1],length=Math.hypot(dx,dy);if(!length)continue;
  const t=Math.max(0,Math.min(1,((x-a[0])*dx+(y-a[1])*dy)/(length*length))),distance=Math.hypot(x-a[0]-dx*t,y-a[1]-dy*t);
  if(distance<best){best=distance;pitch=Math.atan2((b[2]||0)-(a[2]||0),length);}
 }
 return pitch;
}
