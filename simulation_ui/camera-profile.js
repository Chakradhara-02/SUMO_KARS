export function cameraProfile(ego,decks){
 const h=ego.heading*Math.PI/180,dx=Math.sin(h),dy=Math.cos(h);
 const probes=[[ego.x,ego.y],[ego.x-dx*18,ego.y-dy*18],[ego.x+dx*10,ego.y+dy*10]];
 let ceiling=Infinity;
 for(const deck of decks||[]){
  const a=deck.a,b=deck.b,vx=b[0]-a[0],vy=b[1]-a[1],length=vx*vx+vy*vy;
  for(const [x,y] of probes){const t=Math.max(0,Math.min(1,((x-a[0])*vx+(y-a[1])*vy)/(length||1))),z=a[2]+(b[2]-a[2])*t;
   if(z>(ego.z||0)+3&&Math.hypot(x-a[0]-vx*t,y-a[1]-vy*t)<deck.width/2+.4)ceiling=Math.min(ceiling,z-.65);
  }
 }
 const underpass=Number.isFinite(ceiling);
 return {underpass,height:underpass?Math.max(1.6,Math.min(3.1,ceiling-(ego.z||0)-1.1)):7,behind:underpass?11:18,target:underpass?10:13};
}
