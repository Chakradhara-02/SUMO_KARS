import test from 'node:test';
import assert from 'node:assert/strict';
import {buildKnowledgeDiagram,diagramSVG} from '../simulation_ui/knowledge-graph.js';

const triple=(subject,predicate,object)=>({subject,predicate,object});
const network={lanes:['in','out'].flatMap(road=>[0,1,2].map(i=>({id:road+'_'+i,internal:false})))};
const frame={time:3,ego:{vehicle_id:'ego',lane_id:'out_1',road_id:'out',speed:11},
 sensing:{observations:[{id:'lead',lane:'in_1',speed:7},{id:'cross',lane:'cross_in_0',speed:4}]},
 constraints:[{source:'solid lane marking',kind:'marking',start:80,end:140},
 {source:'speed-limit zone',kind:'spatial_speed',start:650,end:800,speed:8},
 {source:'crossing advisory',kind:'spatial_speed',start:420,end:450,speed:5}],
 pipeline:{rdf_groups:{facts:[triple('in_2_left','hasType','left bound'),triple('in_2_left','boundaryOffset',1.6),
 triple('in_0_right','hasType','right bound'),triple('in_0_right','boundaryOffset',-1.6),
 triple('in_1','hasLaneMarking','solid'),triple('solid','hasType','solid'),
 triple('in_1','hasLaneMarking','dashed'),triple('dashed','hasType','dashed'),
 triple('feature_2','source','speed-limit zone'),triple('feature_2','hasBoundary','geometry_2'),
 triple('out_1','within','geometry_2')]}}};

test('Figure 6 projection preserves measured speeds, scopes, membership and RDF predicates',()=>{
 const model=buildKnowledgeDiagram(frame,network);
 assert.equal(model.nodes.find(n=>n.id==='ego-speed').facts.speed,11);
 assert.equal(model.nodes.find(n=>n.id==='solid').facts.start,80);
 assert.equal(model.nodes.find(n=>n.id==='zone-limit').facts.speed,8);
 assert.equal(model.nodes.find(n=>n.id==='crossing-limit').facts.advisory,true);
 assert.deepEqual(model.nodes.find(n=>n.id==='others').facts.members.map(v=>v.id),['lead']);
 assert(model.edges.some(e=>e.from==='ego'&&e.to==='lane_1'&&e.label==='isOn'));
 assert(model.edges.some(e=>e.from==='lane_1'&&e.to==='zone-geometry'&&e.label==='within'));
 const ids=new Set(model.nodes.map(n=>n.id));
 assert.equal(ids.size,model.nodes.length);
 assert(model.edges.every(e=>ids.has(e.from)&&ids.has(e.to)));
 assert(model.nodes.every(n=>model.edges.some(e=>e.from===n.id||e.to===n.id)));
 const svg=diagramSVG(model);
 assert(svg.includes('marker-end="url(#kg-arrow)"'));
 assert(svg.includes('hasSpeedLimitValue'));
});

test('missing snapshots and missing rules do not become invented paper facts',()=>{
 assert.equal(buildKnowledgeDiagram({},network).nodes.length,0);
 const model=buildKnowledgeDiagram({...frame,constraints:[],pipeline:{}},network);
 assert(!model.nodes.some(n=>['zone','solid','crossing','dashed'].includes(n.id)));
});
