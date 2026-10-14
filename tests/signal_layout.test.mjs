import test from 'node:test';
import assert from 'node:assert/strict';
import {signalLayout,signalAspect} from '../simulation_ui/signal-layout.js';

test('signal heads share a curbside gantry and preserve movement phases',()=>{
 const movement={id:'chowk',link:0,lane:'street_0',direction:'s'};
 const network={lanes:[{id:'street_0',width:3.2,shape:[[0,4.8],[100,4.8]]},
 {id:'street_1',width:3.2,shape:[[0,1.6],[100,1.6]]}],
 signals:[movement,{...movement},{id:'chowk',link:1,lane:'street_0',direction:'l'},
 {id:'chowk',link:2,lane:'street_1',direction:'s'}]};
 const approaches=signalLayout(network);
 assert.equal(approaches.length,1);assert.equal(approaches[0].heads.length,3);
 assert(approaches[0].pole.y>6.4);assert(approaches[0].heads.every(h=>h.x<100));
 assert.notEqual(approaches[0].heads[0].y,approaches[0].heads[1].y);
 const signals=[{id:'chowk',state:'rGy'}];
 assert.equal(signalAspect(signals,approaches[0].heads[0].movement),'red');
 assert.equal(signalAspect(signals,approaches[0].heads[1].movement),'green');
 assert.equal(signalAspect(signals,approaches[0].heads[2].movement),'amber');
});
