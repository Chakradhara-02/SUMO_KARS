import test from 'node:test';
import assert from 'node:assert/strict';
import {bridgeLayout} from '../simulation_ui/bridge-geometry.js';
test('bridge combines opposite carriageways, with solid barriers and piers outside the underpass',()=>{
 const lanes=[];
 for(const [edge,sign] of [['a__b',1],['b__a',-1]])for(let i=0;i<2;i++){
  const y=sign*(1.6+3.2*i),shape=sign>0?[[0,y,7],[150,y,7]]:[[150,y,7],[0,y,7]];
  lanes.push({id:edge+'_'+i,width:3.2,shape});
 }
 lanes.push({id:'below_0',width:6.4,shape:[[0,0,0],[150,0,0]]});
 const b=bridgeLayout({lanes});assert.equal(b.decks.length,1);assert.equal(b.decks[0].width,12.8);
 assert.equal(b.rails.length,2);assert(b.rails.every(r=>r.height>=.9));assert(b.posts.length>20);
 assert(b.piers.length>=4);assert(b.piers.every(p=>Math.abs(p.y)>8));assert(b.caps.every(c=>c.a[2]>5));
});
test('ground roads do not acquire bridge structures',()=>{
 const b=bridgeLayout({lanes:[{id:'a__b_0',width:3.2,shape:[[0,0,0],[100,0,0]]}]});
 assert.equal(b.decks.length,0);assert.equal(b.piers.length,0);
});
