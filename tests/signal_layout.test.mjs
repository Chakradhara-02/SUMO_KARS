import test from 'node:test';
import assert from 'node:assert/strict';
import {signalLayout,signalAspect,signalSeconds,crossingLayout} from '../simulation_ui/signal-layout.js';

test('signal heads share a curbside gantry and preserve movement phases',()=>{
 const movement={id:'chowk',link:0,lane:'street_0',direction:'s'};
 const network={lanes:[{id:'street_0',width:3.2,shape:[[0,4.8],[100,4.8]]},
 {id:'street_1',width:3.2,shape:[[0,1.6],[100,1.6]]}],
 signals:[movement,{...movement},{id:'chowk',link:1,lane:'street_0',direction:'l'},
 {id:'chowk',link:2,lane:'street_1',direction:'s'}]};
 const approaches=signalLayout(network);
 assert.equal(approaches.length,1);assert.equal(approaches[0].heads.length,2);
 assert(approaches[0].pole.y>6.4);assert(approaches[0].heads.every(h=>h.x<100));
 assert(Math.abs(approaches[0].heads[0].y-approaches[0].heads[1].y)>.95);
 const signals=[{id:'chowk',state:'rGy'}];
 assert.equal(signalAspect(signals,approaches[0].heads.find(h=>h.movement.direction==='l').movement),'green');
 assert.equal(signalAspect(signals,approaches[0].heads.find(h=>h.movement.direction==='s').movement),'red');
});


test('countdown belongs to the movement and handles unavailable clocks',()=>{
 const clocks=[{id:'j',state:'rG',countdowns:[35,4.2]}];
 assert.equal(signalSeconds(clocks,{id:'j',link:0}),35);
 assert.equal(signalSeconds(clocks,{id:'j',link:1}),5);
 assert.equal(signalSeconds(clocks,{id:'j',link:2}),null);
});

test('zebra crossing spans incoming and outgoing carriageways',()=>{
 const incoming={id:'a__b_0',width:3.2,shape:[[0,1.6],[100,1.6]]};
 const network={lanes:[incoming,{id:'b__a_0',width:3.2,shape:[[100,-1.6],[0,-1.6]]}]};
 const crossing=crossingLayout(network,{tangent:{x:1,y:0},lanes:[incoming]});
 assert.equal(crossing.width,6.4);assert(crossing.stripes.some(p=>p.y<0));assert(crossing.stripes.some(p=>p.y>0));
 assert(crossing.stripes.every(p=>p.x>100));
});


test('six lane movements become three named heads with every link preserved',()=>{
 const network={lanes:[{id:'in_0',width:3.2,shape:[[0,4.8],[100,4.8]]},{id:'in_1',width:3.2,shape:[[0,1.6],[100,1.6]]}],signals:[]};
 for(let i=0;i<6;i++)network.signals.push({id:'j',link:i,lane:'in_'+Math.floor(i/3),direction:['l','s','r'][i%3]});
 const heads=signalLayout(network)[0].heads;
 assert.deepEqual(heads.map(h=>h.movement.direction),['l','s','r']);
 assert.deepEqual(heads.flatMap(h=>h.movement.links).sort(),[0,1,2,3,4,5]);
 assert.equal(signalAspect([{id:'j',state:'GGGrrr'}],heads[0].movement),'red');
 assert.equal(signalSeconds([{id:'j',state:'GGGrrr',countdowns:[3,3,3,20,20,20]}],heads[0].movement),null);
 assert.equal(signalSeconds([{id:'j',state:'rrrrrr',countdowns:[3,3,3,20,20,20]}],heads[0].movement),20);
});
