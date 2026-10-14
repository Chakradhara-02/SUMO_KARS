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
  const byLane=new Map();for(const head of group.heads){if(!byLane.has(head.movement.lane))byLane.set(head.movement.lane,[]);byLane.get(head.movement.lane).push(head);}
  for(const heads of byLane.values())heads.forEach((head,i)=>{const offset=(i-(heads.length-1)/2)*.85;head.x+=n.x*offset;head.y+=n.y*offset;});
  const reference=group.lanes[0].shape.at(-1),offsets=group.lanes.map(l=>{const p=l.shape.at(-1);return (p[0]-reference[0])*n.x+(p[1]-reference[1])*n.y;});
  const side=Math.max(...offsets)+group.lanes[0].width/2+1.2,far=Math.min(...offsets)-group.lanes[0].width/2;
  group.pole={x:reference[0]+n.x*side-t.x*1.5,y:reference[1]+n.y*side-t.y*1.5};
  group.beamEnd={x:reference[0]+n.x*far-t.x*1.5,y:reference[1]+n.y*far-t.y*1.5};
 }
 return [...groups.values()];
}

export function signalAspect(signals,movement){
 const color=signals?.find(s=>s.id===movement.id)?.state[movement.link]?.toLowerCase();
 return color==='g'?'green':color==='y'?'amber':color==='r'?'red':'off';
}
