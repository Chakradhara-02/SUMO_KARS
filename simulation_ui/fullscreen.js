export function installFullscreen(panel,button,doc=globalThis.document,onResize=()=>{}){
 const expanded=()=>doc.fullscreenElement===panel||panel.classList.contains('expanded');
 const update=()=>{const active=expanded();button.textContent=active?'Exit fullscreen':'Fullscreen';button.setAttribute('aria-pressed',String(active));onResize();};
 button.addEventListener('click',async()=>{
  if(doc.fullscreenElement===panel)await doc.exitFullscreen();
  else if(panel.classList.contains('expanded'))panel.classList.remove('expanded');
  else try{if(!panel.requestFullscreen)throw Error('unsupported');await panel.requestFullscreen();}catch{panel.classList.add('expanded');}
  update();
 });
 doc.addEventListener('fullscreenchange',update);
 doc.addEventListener('keydown',event=>{if(event.key==='Escape'&&panel.classList.contains('expanded')){panel.classList.remove('expanded');update();}});
 update();
}
