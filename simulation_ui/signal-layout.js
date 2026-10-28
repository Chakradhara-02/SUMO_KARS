// One gantry per incoming approach; each head retains its own SUMO link index.
export function signalLayout(network){
 const lanes=new Map((network.lanes||[]).map(l=>[l.id,l]));
 const groups=new Map(),seen=new Set();
 for(const movement of network.signals||[]){
  const lane=lanes.get(movement.lane);if(!lane||lane.internal||lane.shape.length<2)continue;
  const key=movement.id+'/'+movement.lane.replace(/_\d+$/,'');
  const unique=movement.id+'/'+movement.link+'/'+movement.lane;if(seen.has(unique))continue;seen.add(unique);
  const a=lane.shape.at(-2),b=lane.shape.at(-1),length=Math.hypot(b[0]-a[0],b[1]-a[1]);if(!length)continue;
  const tangent={x:(b[0]-a[0])/length,y:(b[1]-a[1])/length};
  if(!groups.has(key))groups.set(key,{id:movement.id,key,tangent,heads:[],lanes:[]});
  const group=groups.get(key);group.heads.push({movement,x:b[0]-tangent.x*1.5,y:b[1]-tangent.y*1.5});
  if(!group.lanes.includes(lane))group.lanes.push(lane);
 }
 for(const group of groups.values()){
  const t=group.tangent,n={x:-t.y,y:t.x};
  const movements=new Map();
  for(const head of group.heads){const direction=head.movement.direction?.toLowerCase(),kind=direction==='l'?'l':direction==='r'?'r':direction==='s'?'s':null;if(!kind)continue;if(!movements.has(kind))movements.set(kind,[]);movements.get(kind).push(head.movement);}
  const centre=group.lanes.map(l=>l.shape.at(-1)).reduce((p,q)=>({x:p.x+q[0]/group.lanes.length,y:p.y+q[1]/group.lanes.length}),{x:0,y:0});
  group.heads=['l','s','r'].filter(d=>movements.has(d)).map((direction,i,dirs)=>{
   const links=movements.get(direction),offset=((dirs.length-1)/2-i)*1.65;
   return {movement:{...links[0],direction,links:[...new Set(links.map(m=>m.link))]},x:centre.x+n.x*offset-t.x*1.5,y:centre.y+n.y*offset-t.y*1.5};
  });
  const reference=group.lanes[0].shape.at(-1),offsets=group.lanes.map(l=>{const p=l.shape.at(-1);return (p[0]-reference[0])*n.x+(p[1]-reference[1])*n.y;});
  const side=Math.max(...offsets)+group.lanes[0].width/2+1.2,far=Math.min(...offsets)-group.lanes[0].width/2;
  group.pole={x:reference[0]+n.x*side-t.x*1.5,y:reference[1]+n.y*side-t.y*1.5};
  group.beamEnd={x:reference[0]+n.x*far-t.x*1.5,y:reference[1]+n.y*far-t.y*1.5};
 }
 return [...groups.values()];
}

export function signalAspect(signals,movement){
 const state=signals?.find(s=>s.id===movement.id)?.state||'';
 const colors=(movement.links||[movement.link]).map(i=>state[i]?.toLowerCase());
 if(colors.every(c=>c==='g'))return 'green';
 if(colors.some(c=>c==='r'))return 'red';
 if(colors.some(c=>c==='y'))return 'amber';
 return 'off';
}

export function signalSeconds(signals,movement){
 const clock=signals?.find(s=>s.id===movement.id),indices=movement.links||[movement.link];
 const values=indices.map(i=>clock?.countdowns?.[i]);
 if(!values.every(Number.isFinite))return null;
 const aspects=new Set(indices.map(i=>clock?.state?.[i]?.toLowerCase()));
 if(aspects.size>1)return null;
 return Math.max(0,Math.ceil(aspects.has('r')?Math.max(...values):Math.min(...values)));
}

export function crossingLayout(network,approach){
 const t=approach.tangent,n={x:-t.y,y:t.x},reference=approach.lanes[0].shape.at(-1);
 const edge=approach.lanes[0].id.replace(/_\d+$/,''),reverse=edge.split('__').reverse().join('__');
 const other=(network.lanes||[]).filter(l=>!l.internal&&l.id.startsWith(reverse+'_'));
 const spans=approach.lanes.map(l=>{const p=l.shape.at(-1);return {offset:(p[0]-reference[0])*n.x+(p[1]-reference[1])*n.y,width:l.width};});
 for(const lane of other){const p=lane.shape[0];spans.push({offset:(p[0]-reference[0])*n.x+(p[1]-reference[1])*n.y,width:lane.width});}
 const lo=Math.min(...spans.map(s=>s.offset-s.width/2)),hi=Math.max(...spans.map(s=>s.offset+s.width/2));
 const stripes=[];
 for(let offset=lo+.35;offset<hi-.2;offset+=.85)stripes.push({x:reference[0]+n.x*offset+t.x*1.6,y:reference[1]+n.y*offset+t.y*1.6,z:reference[2]||0});
 return {stripes,width:hi-lo,tangent:t,normal:n};
}
