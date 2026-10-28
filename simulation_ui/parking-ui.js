import {mountShowroom} from './parking-showroom.js';
const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export function parkingView(frame,trip,selected){
 const lot=frame.city?.trip?.parking_lot||trip?.parking_lot,state=frame.city?.parking;if(!lot)return null;
 const stage=state?.stage||'approaching',locked=!!state?.active&&stage!=='waiting_selection',slot=state?.slot_id||selected;
 const labels={approaching:'Choose an empty bay',waiting_selection:'Select a bay to begin',positioning:'Moving forward into position',reversing:'Reversing into your bay',aligning:'Straightening inside the bay',parked:'Parked securely'};
 const slots=lot.slots.map(s=>`<button type="button" data-parking-slot="${s.id}" class="parking-slot ${s.occupied?'occupied':''} ${slot===s.id?'selected':''}" ${s.occupied||locked?'disabled':''} aria-pressed="${slot===s.id}">${s.id}<small>${s.occupied?'Occupied':slot===s.id?'Selected':'Empty'}</small></button>`).join('');
 const shapes=lot.slots.map(s=>`<g data-parking-slot="${s.id}" role="button" tabindex="${s.occupied||locked?-1:0}" aria-label="${s.id} ${s.occupied?'occupied':'empty'}"><rect x="${s.x-lot.x-s.width/2}" y="${40-(s.y-lot.y)-s.length/2}" width="${s.width}" height="${s.length}" rx=".3" fill="${s.occupied?'#68727d':slot===s.id?'#2bd4a3':'#223c48'}" stroke="#8aa0aa" stroke-width=".15"/><text x="${s.x-lot.x}" y="${40-(s.y-lot.y)+.5}" font-size="1.7" fill="white" text-anchor="middle">${s.id}</text></g>`).join('');
 const path=(state?.path||[]).map(p=>(p.x-lot.x)+','+(40-(p.y-lot.y))).join(' ');
 const e=frame.ego,h=(e?.heading||0)*Math.PI/180,cx=e?e.x-2.35*Math.sin(h)-lot.x:0,cy=e?40-(e.y-2.35*Math.cos(h)-lot.y):0;
 const car=state?.active&&e?`<g transform="translate(${cx},${cy}) rotate(${e.heading})"><rect x="-.9" y="-2.35" width="1.8" height="4.7" rx=".45" fill="#f4fbff" stroke="#acd2df" stroke-width=".12"/><rect x="-.65" y="-.9" width="1.3" height="1.6" rx=".2" fill="#263c4c"/></g>`:'';
 return {lot,stage,locked,slots,html:`<div class="parking-title"><span>${state?.complete?'✓ PARKING COMPLETE':'AUTO PARK'}</span><b>${escape(lot.name)} ${slot?'· '+slot:''}</b><strong class="parking-gear">${state?.gear||'D'}</strong></div><svg class="parking-map" viewBox="0 0 78 40" aria-label="Parking lot and measured ego position"><rect width="78" height="40" rx="2" fill="#122735"/><path d="M3 28 H70 V5 H3" fill="none" stroke="#597786" stroke-width=".35" stroke-dasharray="2 2"/>${shapes}<polyline points="${path}" fill="none" stroke="#62b9ff" stroke-width=".55" stroke-dasharray="1.2 .8"/>${car}</svg><div class="parking-phase">${labels[stage]||stage}</div><div class="parking-progress"><i style="width:${Math.round((state?.progress||0)*100)}%"></i></div>`};
}
export function installParkingUI({document:doc,onSelect}){
 const choice=doc.getElementById('parking-choice'),console=doc.getElementById('parking-console');let key='',html='',disposeShowroom=null,minimized=false,closed=false,wasActive=false;
 const restore=doc.createElement('button');restore.type='button';restore.className='parking-restore';restore.textContent='Show parking';restore.hidden=true;console.parentElement.append(restore);
 function visibility(){console.classList.toggle('parking-minimized',minimized);console.classList.toggle('parking-closed',closed);restore.hidden=!closed||console.hidden;}
 console.addEventListener('click',event=>{const action=event.target.closest('[data-parking-panel]')?.dataset.parkingPanel;if(!action)return;if(action==='close'){closed=true;}else minimized=!minimized;visibility();});
 restore.addEventListener('click',()=>{closed=false;minimized=false;visibility();});
 async function select(event){const item=event.target.closest('[data-parking-slot]');if(!item||item.disabled||item.getAttribute('tabindex')==='-1')return;try{await onSelect(item.dataset.parkingSlot);}catch(error){doc.getElementById('parking-help').textContent=error.message;}}
 choice.addEventListener('click',select);console.addEventListener('click',select);console.addEventListener('keydown',event=>{if((event.key==='Enter'||event.key===' ')&&event.target.closest('[data-parking-slot]')){event.preventDefault();select(event);}});
 return (frame,trip,selected)=>{const view=parkingView(frame,trip,selected),active=!!frame.city?.parking?.active;choice.hidden=!view;console.hidden=!view||!active;
  if(active&&!wasActive){closed=false;minimized=false;}wasActive=active;restore.hidden=!closed||!active;visibility();
  if(!view){disposeShowroom?.();disposeShowroom=null;html='';return;}
  const next=JSON.stringify([view.lot.id,view.stage,frame.city?.parking?.slot_id,selected,view.locked]);
  if(next!==key){key=next;doc.getElementById('parking-slots').innerHTML=view.slots;doc.getElementById('parking-help').textContent=view.stage==='parked'?'Parking complete. Start a new journey to choose another bay.':view.locked?'Bay locked while the car manoeuvres.':'Choose a green/empty bay now or on arrival. Occupied bays cannot be selected.';}
  if(!console.hidden&&!closed){console.dataset.stage=view.stage;
   if(html!==view.html){disposeShowroom?.();disposeShowroom=null;html=view.html;console.innerHTML=view.html;
    console.querySelector('.parking-title').insertAdjacentHTML('beforeend','<div class="parking-window-controls"><button type="button" data-parking-panel="minimize" aria-label="Minimize or expand parking display" title="Minimize / expand">&#8722;</button><button type="button" data-parking-panel="close" aria-label="Close parking display" title="Close">&#215;</button></div>');
    if(view.stage==='parked'){const map=console.querySelector('.parking-map');map.outerHTML='<div class="parking-showroom"><canvas aria-label="Animated parked ego vehicle"></canvas><div class="car-controls"><span>Loading Roadster...</span></div><p>Vehicle secured · Explore your car</p></div><details class="parked-bays"><summary>View parking bay</summary>'+map.outerHTML+'</details>';disposeShowroom=mountShowroom(console.querySelector('.parking-showroom'));}
   }
  }else if(console.hidden&&disposeShowroom){disposeShowroom();disposeShowroom=null;html='';}
 };
}
