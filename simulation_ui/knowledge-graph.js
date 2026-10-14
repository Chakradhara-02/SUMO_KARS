const escape=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number=v=>Number.isFinite(Number(v))?Number(v).toFixed(1):'—';

// A Figure 6 projection of the recorded graph, focused on the ego's main road.
// Aggregate vehicle nodes keep dense traffic readable; their member IDs remain
// available in the node inspector. No paper values replace simulation values.
export function buildKnowledgeDiagram(frame,network={}){
 const triples=Object.values(frame.pipeline?.rdf_groups||{}).flat();
 const value=(s,p)=>triples.find(t=>t.subject===s&&t.predicate===p)?.object;
 const nodes=[],edges=[];
 const node=(id,label,detail,x,y,kind='entity',facts={})=>{nodes.push({id,label,detail,x,y,kind,facts});return id;};
 const edge=(from,to,label,route='horizontal')=>edges.push({from,to,label,route});
 const ego=frame.ego,observations=frame.sensing?.observations||[];
 if(!ego)return {nodes,edges,triples,road:null};
 const road='main';
 node('road','Road R0','Main road · in + out',95,270,'road',{segments:['in','out'],group:'Main-road segments grouped as R0, following Figure 6.'});
 node('ego','Ego vehicle',ego.vehicle_id,350,55,'entity',ego);
 node('ego-speed','Current speed',number(ego.speed)+' m/s',700,55,'value',{speed:ego.speed,time:frame.time});
 edge('ego','ego-speed','hasSpeed');
 const lanes=(network.lanes||[]).filter(l=>/^(in|out)_\d+$/.test(l.id)&&!l.internal);
 const laneGroup=id=>lanes.some(l=>l.id===id)?'lane_'+Number(id.split('_').at(-1)):null;
 for(const [i,index] of [2,1,0].entries()){
  const members=lanes.filter(l=>Number(l.id.split('_').at(-1))===index);if(!members.length)continue;
  const id='lane_'+index;
  node(id,'Lane '+index,members.map(l=>l.id).join(' · '),350,170+i*100,'lane',{members});
  edge(id,'road','isOn');
  if(members.some(l=>l.id===ego.lane_id))edge('ego',id,'isOn','ego-lane');
 }
 // Network lane numbering is right-to-left; use the recorded outer bounds.
 for(const [side,index,y] of [['left',2,170],['right',0,370]]){
  const lane='lane_'+index,feature='in_'+index+'_'+side;
  if(value(feature,'hasType')===side+' bound'){
   node(feature,side==='left'?'Left bound':'Right bound','Offset '+value(feature,'boundaryOffset')+' m',700,y,'boundary',{id:feature,shape:value(feature,'hasShape'),offset:value(feature,'boundaryOffset')});
   if(nodes.some(n=>n.id===lane))edge(lane,feature,'hasBoundary');
  }
 }
 const markingLinks=triples.filter(t=>t.predicate==='hasLaneMarking'&&laneGroup(t.subject));
 const dashed=markingLinks.filter(t=>value(t.object,'hasType')==='dashed');
 if(dashed.length){
  node('dashed','Dashed separators','Adjacent lane boundaries',700,270,'marking',{members:[...new Set(dashed.map(t=>t.object))],scope:'Default separators; scoped solid-line restrictions take precedence.'});
  for(const lane of new Set(dashed.map(t=>laneGroup(t.subject))))edge(lane,'dashed','hasLaneMarking');
 }
 const rules=[...new Map((frame.constraints||[]).map(c=>[c.source,c])).values()];
 const solid=rules.find(c=>c.kind==='marking');
 if(solid){
  node('solid','Solid lane marking',number(solid.start)+'–'+number(solid.end)+' m',990,270,'marking',solid);
  const links=markingLinks.filter(t=>value(t.object,'hasType')==='solid');
  const targets=links.length?links.map(t=>laneGroup(t.subject)):nodes.filter(n=>n.kind==='lane'&&(solid.lane<0||solid.lane===undefined||n.id==='lane_'+solid.lane)).map(n=>n.id);
  for(const lane of new Set(targets))edge(lane,'solid','hasLaneMarking','solid');
 }
 const zone=rules.find(c=>c.source==='speed-limit zone');
 const crossing=rules.find(c=>c.source==='crossing advisory');
 for(const [rule,key,title,y] of [[zone,'zone','Speed limit sign',495],[crossing,'crossing','Crosswalk advisory',605]]){
  if(!rule)continue;
  const feature=triples.find(t=>t.predicate==='source'&&t.object===rule.source&&t.subject.startsWith('feature_'))?.subject;
  const geometry=feature?value(feature,'hasBoundary'):null;
  node(key,title,rule.source,350,y,'feature',{id:feature,...rule});
  node(key+'-geometry',key==='zone'?'Speed-limit zone':'Crosswalk zone',number(rule.start)+'–'+number(rule.end)+' m',700,y,'geometry',{id:geometry,start:rule.start,end:rule.end,lane:rule.lane,begin:rule.begin,finish:rule.finish});
  node(key+'-limit','Speed limit',number(rule.speed)+' m/s',990,y,'value',{speed:rule.speed,advisory:key==='crossing'});
  edge(key,key+'-geometry','hasBoundary');
  edge(key,key+'-limit','hasSpeedLimitValue','limit');
  if(geometry){
   for(const from of new Set(triples.filter(t=>t.predicate==='within'&&t.object===geometry&&laneGroup(t.subject)).map(t=>laneGroup(t.subject))))edge(from,key+'-geometry','within','within');
  }
 }
 const members=observations.filter(v=>v.id!=='ego'&&/^(in|out)_\d+$/.test(v.lane));
 if(members.length){
  node('others','Other vehicles',members.length+' observed on main road',350,720,'entity',{members});
  node('other-speeds','Observed speeds',Math.min(...members.map(v=>v.speed)).toFixed(1)+'–'+Math.max(...members.map(v=>v.speed)).toFixed(1)+' m/s',700,720,'value',{speeds:members.map(v=>({id:v.id,speed:v.speed,source:v.source,timestamp:v.timestamp}))});
  edge('road','others','has','road-vehicles');edge('others','other-speeds','hasSpeed');
 }
 return {nodes,edges,triples,road,recorded:!!frame.pipeline?.rdf_groups};
}

export function diagramSVG(model,selected=null){
 const byId=new Map(model.nodes.map(n=>[n.id,n]));
 const edges=model.edges.map((e,i)=>{
  const a=byId.get(e.from),b=byId.get(e.to);if(!a||!b)return '';
  let d,x,y;
  if(e.route==='ego-lane'){d=`M${a.x-65},${a.y+22} H245 V${b.y} H${b.x-76}`;x=244;y=(a.y+b.y)/2;}
  else if(e.route==='road-vehicles'){d=`M${a.x},${a.y+28} V${b.y} H${b.x-86}`;x=a.x;y=650;}
  else if(e.route==='limit'){const rail=a.y+45;d=`M${a.x},${a.y+27} V${rail} H${b.x} V${b.y+27}`;x=555;y=rail;}
  else if(e.route==='within'){const rail=1105;d=`M${a.x+76},${a.y+20} C${a.x+100},${a.y+65} ${a.x+115},440 ${rail},440 V${b.y-40} H875 V${b.y} H${b.x+96}`;x=rail-27;y=b.y-44;}
  else if(e.route==='solid'){const rail=420;d=`M${a.x+76},${a.y+12} H490 V${rail} H${b.x} V${b.y+27}`;x=850;y=rail;}
  else {const right=b.x>a.x;const start=a.x+(right?76:-76),end=b.x+(right?-90:76);d=`M${start},${a.y} C${(start+end)/2},${a.y} ${(start+end)/2},${b.y} ${end},${b.y}`;x=(start+end)/2;y=(a.y+b.y)/2;}
  return `<g class="kg-edge"><path d="${d}" marker-end="url(#kg-arrow)"/><rect x="${x-e.label.length*3.4-5}" y="${y-17}" width="${e.label.length*6.8+10}" height="20" rx="5"/><text x="${x}" y="${y-3}" text-anchor="middle">${escape(e.label)}</text><title>${escape(e.from+' → '+e.label+' → '+e.to)}</title></g>`;
 }).join('');
 const nodes=model.nodes.map(n=>{
  const shape=n.kind==='lane'?`<path d="M-76,0 L-59,-28 H59 L76,0 L59,28 H-59 Z"/>`:['entity','value','geometry'].includes(n.kind)?'<ellipse rx="90" ry="29"/>':'<rect x="-90" y="-29" width="180" height="58" rx="9"/>';
  return `<g transform="translate(${n.x},${n.y})" class="kg-node kg-${n.kind} ${selected===n.id?'is-selected':''}" data-kg-node="${escape(n.id)}" role="button" tabindex="0" aria-label="Inspect ${escape(n.label)}">${shape}<text text-anchor="middle" y="-3">${escape(n.label)}</text><text class="kg-subtitle" text-anchor="middle" y="16">${escape(n.detail)}</text><title>${escape(n.id+' · '+n.detail)}</title></g>`;
 }).join('');
 return `<svg class="kg-diagram" viewBox="0 0 1160 780" role="group" aria-label="Figure 6 inspired traffic knowledge graph"><defs><marker id="kg-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8 Z" fill="#64879c"/></marker></defs>${edges}${nodes}</svg>`;
}
