import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {renderSignalHud,cityJourneyStatus} from '../simulation_ui/signal-hud.js';
const elements=()=>[{textContent:'Signal data pending',dataset:{}},{textContent:'Continuing straight'}];
test('live signal telemetry replaces the placeholder and updates indicator reason',()=>{
 const [signal,reason]=elements();
 renderSignalHud({ego:{indicator_reason:'Turning right'},city:{next_signal:{color:'r',seconds:12,distance:24.6}}},signal,reason);
 assert.equal(signal.textContent,'RED | 12 s | 25 m ahead');assert.equal(signal.dataset.color,'red');assert.equal(reason.textContent,'Turning right');
 renderSignalHud({ego:{indicator_reason:'Continuing straight'},city:{next_signal:{color:'G',seconds:7,distance:10}}},signal,reason);
 assert.equal(signal.textContent,'GREEN | 7 s | 10 m ahead');assert.equal(signal.dataset.color,'green');assert.equal(reason.textContent,'Continuing straight');
});
test('no signal, parked, preview and legacy replay have distinct honest labels',()=>{
 const [signal,reason]=elements();
 renderSignalHud({city:{next_signal:null}},signal,reason);assert.match(signal.textContent,/No traffic signal ahead/);
 renderSignalHud({city:{parked:true,next_signal:null}},signal,reason);assert.equal(signal.textContent,'ARRIVED');
 renderSignalHud({city:{}},signal,reason);assert.match(signal.textContent,/unavailable in this saved run/);
 renderSignalHud({},signal,reason);assert.match(signal.textContent,/Start a city journey/);assert.equal(signal.dataset.color,'');
});
test('dashboard render path invokes the measured HUD binding',()=>{
 const source=readFileSync(new URL('../simulation_ui/app.js',import.meta.url),'utf8');
 const driving=source.slice(source.indexOf('function renderDriving()'),source.indexOf('const stageKeys='));
 assert.match(driving,/renderSignalHud\(frame,\$\('next-signal'\),\$\('indicator-reason'\)\)/);
});


test('a timed-out city journey is distinct from successful arrival',()=>{
 const frame={ego:{speed:0},city:{parked:false}};
 assert.match(cityJourneyStatus(frame,{status:{end_reason:'duration_limit'}}),/DESTINATION NOT REACHED/);
 assert.equal(cityJourneyStatus({...frame,city:{parked:true}},{status:{end_reason:'arrived'}}),'PARKED AT DESTINATION');
 assert.equal(cityJourneyStatus(frame,{status:{state:'running'}}),'WAITING IN CITY TRAFFIC');
});
