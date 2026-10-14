import test from 'node:test';
import assert from 'node:assert/strict';
import {comparisonKey,matchingRuns} from '../simulation_ui/planners.js';

const run=(id,algorithm='kars',changes={})=>({id,alive:false,status:{state:'completed'},
  manifest:{algorithm,scenario:'demo',seed:1,duration:25,density_period:9,started_at:1,
    config:{dt:1,realtime_factor:1,weights:{center:.1}},source_hashes:{'main.py':'abc'},
    input_hashes:{'road.net.xml':'def'},sumo_version:'1.25',...changes},
  metrics:{delay:0,loss:0,average_speed:0}});

test('matches controlled cohorts and excludes changes in seed, road, code or configuration',()=>{
  const reference=run('reference');
  const same=run('same','astar',{config:{weights:{center:.1},realtime_factor:5,dt:1}});
  const others=[run('seed','rs',{seed:2}),run('road','rs',{input_hashes:{'road.net.xml':'new'}}),
    run('code','rs',{source_hashes:{'main.py':'new'}}),run('config','rs',{config:{dt:.1}})];
  assert.equal(comparisonKey(reference),comparisonKey(same));
  assert.deepEqual(matchingRuns([reference,same,...others],reference).map(r=>r.id),['reference','same']);
});
test('does not label missing provenance, cancelled or active runs as matched results',()=>{
  const reference=run('reference');const active={...run('live','astar'),alive:true};
  const cancelled={...run('cancelled','rs'),status:{state:'cancelled'}};
  assert.equal(comparisonKey(run('old','rs',{source_hashes:null})),null);
  assert.deepEqual(matchingRuns([active,cancelled,reference],reference).map(r=>r.id),['reference']);
});
test('uses newest completed repeat per algorithm without counting repeats as separate planners',()=>{
  const reference=run('reference');const newer=run('new','kars',{started_at:5});
  assert.deepEqual(matchingRuns([reference,newer],reference).map(r=>r.id),['new']);
});
