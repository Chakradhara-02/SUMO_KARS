import test from 'node:test';
import assert from 'node:assert/strict';
import {FrameQuality} from '../simulation_ui/frame-quality.js';

test('sustained slow frames lower render resolution within a bounded floor',()=>{
 const q=new FrameQuality();for(let i=0;i<300;i++)q.update(50,i*50,1.5);
 assert(q.ratio<1.5);assert(q.ratio>=.65);
});

test('quality stays stable on normal frames and recovers slowly after overload',()=>{
 const q=new FrameQuality();for(let i=0;i<120;i++)q.update(16.7,i*16.7,1);
 assert.equal(q.ratio,1);
 for(let i=0;i<160;i++)q.update(50,2000+i*50,1);
 const low=q.ratio;
 for(let i=0;i<1200;i++)q.update(16,10000+i*16,1);
 assert(q.ratio>low);assert(q.ratio<=1);
});
