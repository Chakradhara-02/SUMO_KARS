import test from 'node:test';
import assert from 'node:assert/strict';
import {installFullscreen} from '../simulation_ui/fullscreen.js';
function fixture(){
 const classes=new Set(),handlers={},events={};
 const panel={classList:{contains:k=>classes.has(k),add:k=>classes.add(k),remove:k=>classes.delete(k)}};
 const button={addEventListener:(event,fn)=>handlers[event]=fn,setAttribute(){}};
 const doc={fullscreenElement:null,addEventListener:(event,fn)=>events[event]=fn,async exitFullscreen(){this.fullscreenElement=null;}};
 return {panel,button,doc,handlers,events};
}
test('fullscreen button enters and exits the native browser view',async()=>{
 const f=fixture();f.panel.requestFullscreen=async()=>{f.doc.fullscreenElement=f.panel;};
 installFullscreen(f.panel,f.button,f.doc);
 await f.handlers.click();assert.equal(f.doc.fullscreenElement,f.panel);assert.equal(f.button.textContent,'Exit fullscreen');
 await f.handlers.click();assert.equal(f.doc.fullscreenElement,null);assert.equal(f.button.textContent,'Fullscreen');
});
test('expanded view and Escape work when browser fullscreen is unavailable',async()=>{
 const f=fixture();installFullscreen(f.panel,f.button,f.doc);
 await f.handlers.click();assert(f.panel.classList.contains('expanded'));
 f.events.keydown({key:'Escape'});assert(!f.panel.classList.contains('expanded'));
});
