// Bind measured city telemetry to the driver HUD.
export function renderSignalHud(frame,signalElement,indicatorElement){
 indicatorElement.textContent=frame.ego?.indicator_reason || (frame.ego?'Indicator intent unavailable':'Awaiting vehicle telemetry');
 const city=frame.city,signal=city?.next_signal;
 signalElement.dataset.color='';
 if(!city){signalElement.textContent='Start a city journey for signal information';return;}
 if(city.parked){signalElement.textContent='ARRIVED';return;}
 if(!Object.hasOwn(city,'next_signal')){signalElement.textContent='Signal details unavailable in this saved run';return;}
 if(!signal){signalElement.textContent='No traffic signal ahead on this route';return;}
 const color={r:'red',y:'amber',g:'green'}[String(signal.color).toLowerCase()]||'off';
 signalElement.dataset.color=color;
 const seconds=Number.isFinite(signal.seconds)?Math.max(0,Math.ceil(signal.seconds))+' s':'timer unavailable';
 const distance=Number.isFinite(signal.distance)?' | '+Math.max(0,Math.round(signal.distance))+' m ahead':'';
 signalElement.textContent=color.toUpperCase()+' | '+seconds+distance;
}

export function cityJourneyStatus(frame,run){
 if(frame.city?.parked)return 'PARKED AT DESTINATION';
 const end=run?.status?.end_reason;
 if(end==='duration_limit')return 'JOURNEY LIMIT REACHED - DESTINATION NOT REACHED';
 if(end==='cancelled')return 'JOURNEY STOPPED BEFORE DESTINATION';
 if(run?.status?.state==='failed')return 'JOURNEY FAILED - CHECK ENGINE LOG';
 if(run?.status?.state==='paused')return 'JOURNEY PAUSED';
 return frame.ego?.speed<.2?(frame.city?.motion_context?.message?.toUpperCase()||'WAITING IN CITY TRAFFIC'):'DRIVING TO DESTINATION';
}
