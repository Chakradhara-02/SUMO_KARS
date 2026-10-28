// SUMO vehicle-signal bits: right=1, left=2, hazard=4, brake=8.
export function turnSignals(actor={}) {
  const bits=Number(actor.signals)||0;
  return {left:!!(bits&6),right:!!(bits&5),brake:!!(bits&8)};
}

export function assistance(frame={}) {
  const ego=frame.ego;
  if(frame.city?.parked)return {level:'none',message:'Arrival complete'};
  if(!ego)return {level:'none',message:'Awaiting telemetry'};
  const speed=ego.speed||0,ttc=frame.ttc,gap=frame.clearance,signal=turnSignals(ego);
  if(speed>1 && (frame.emergency || Number.isFinite(ttc)&&ttc<1.8 || Number.isFinite(gap)&&gap<2))
    return {level:'danger',message:'Collision warning — brake',tone:880};
  if(speed>1 && Number.isFinite(ttc)&&ttc<3.5)
    return {level:'caution',message:'Closing on traffic ahead',tone:660};
  const yaw=(ego.heading||0)*Math.PI/180,fx=Math.sin(yaw),fy=Math.cos(yaw);
  if(speed>.5 && (signal.left||signal.right))for(const other of frame.vehicles||[]) {
    if(other.vehicle_id==='ego'||Math.abs((other.z||0)-(ego.z||0))>2.5)continue;
    const dx=other.x-ego.x,dy=other.y-ego.y;
    const along=dx*fx+dy*fy,left=-dx*fy+dy*fx;
    if(along>-9&&along<4&&Math.abs(left)>1.5&&Math.abs(left)<5.5&&
       (left>0&&signal.left || left<0&&signal.right))
      return {level:'caution',message:(left>0?'Left':'Right')+' blind spot occupied',tone:660};
  }
  return {level:'none',message:speed<.3?'Waiting in traffic':'Monitoring traffic'};
}

export class DriverAudio {
  constructor(){this.enabled=false;this.lastWarning=-Infinity;this.lastTick=-Infinity;}
  async toggle(){
    if(this.enabled){this.enabled=false;return false;}
    const Audio=globalThis.AudioContext||globalThis.webkitAudioContext;
    if(!Audio)throw Error('Audio is not supported in this browser');
    this.context ||= new Audio();
    await this.context.resume();this.enabled=true;return true;
  }
  tone(frequency,duration=.09,offset=0,volume=.035){
    const context=this.context;if(!this.enabled||context?.state!=='running')return;
    const oscillator=context.createOscillator(),gain=context.createGain(),start=context.currentTime+offset;
    oscillator.type='sine';oscillator.frequency.value=frequency;
    gain.gain.setValueAtTime(0,start);gain.gain.linearRampToValueAtTime(volume,start+.008);
    gain.gain.exponentialRampToValueAtTime(.0001,start+duration);
    oscillator.connect(gain);gain.connect(context.destination);oscillator.start(start);oscillator.stop(start+duration+.01);
  }
  update(frame,live,now=performance.now()){
    if(!this.enabled||!live||globalThis.document?.hidden)return;
    if(!frame.city?.parking?.complete)this.parkingChimed=false;
    else if(!this.parkingChimed){this.parkingChimed=true;this.tone(660,.12);this.tone(880,.16,.16);}
    const state=assistance(frame),signal=turnSignals(frame.ego);
    if(state.level!=='none'&&now-this.lastWarning>(state.level==='danger'?1000:2200)){
      this.lastWarning=now;this.tone(state.tone);
      if(state.level==='danger')this.tone(state.tone,.09,.17);
    }else if(state.level==='none'&&(signal.left||signal.right)&&now-this.lastTick>650){
      this.lastTick=now;this.tone(350,.025,0,.008);
    }
  }
}
