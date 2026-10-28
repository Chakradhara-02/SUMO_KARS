from pathlib import Path
p=Path('simulation_ui/app.js');s=p.read_text(encoding='utf-8');s="import {DriverAudio,assistance,turnSignals} from './driver-assist.js';\n"+s
s=s.replace("let parameters={", "const driverAudio=new DriverAudio();\nlet parameters={")
s=s.replace("function animate(now){const elapsed", "function animate(now){const driverLive=!replay&&!!currentRun()?.alive&&currentRun()?.status.state==='running'&&!frameFetchFailed&&now-receivedAt<2000&&!$('live-view').hidden;driverAudio.update(frame,driverLive,now);const lights=turnSignals(frame.ego),blink=Math.floor((frame.time||0)*2)%2===0;for(const side of ['left','right'])$('indicator-'+side).classList.toggle('lit',!!lights[side]&&blink);const alert=assistance(frame);$('adas-state').textContent=alert.message;$('adas-state').dataset.level=alert.level;const elapsed")
s=s.replace("$('sensor-toggle').onclick=", "$('sound-toggle').onclick=async()=>{try{const on=await driverAudio.toggle();$('sound-toggle').textContent=on?'Sound on':'Enable sound';$('sound-toggle').setAttribute('aria-pressed',String(on));$('sound-toggle').classList.toggle('selected',on);if(on)driverAudio.tone(500,.06);}catch(e){toast(e.message);}};\n$('sensor-toggle').onclick=")
p.write_text(s,encoding='utf-8')
p=Path('simulation_ui/index.html');s=p.read_text(encoding='utf-8').replace('20261015-metro-v2','20261015-driver-ux-v3')
s=s.replace('<button id="sensor-toggle"', '<button id="sound-toggle" class="chip" aria-pressed="false" title="Optional indicator ticks and traffic warning tones">Enable sound</button><button id="sensor-toggle"')
s=s.replace('<div class="drive-hud"><div>', '<div class="driver-alerts"><div class="turn-indicators" aria-label="Measured turn signals"><span id="indicator-left" aria-label="Left indicator">&#9664;</span><span id="indicator-right" aria-label="Right indicator">&#9654;</span></div><span id="adas-state" role="status" aria-live="polite">Monitoring traffic</span></div><div class="drive-hud"><div>')
p.write_text(s,encoding='utf-8')
p=Path('simulation_ui/style.css');s=p.read_text(encoding='utf-8');s+='''
.driver-alerts{position:absolute;top:44px;left:50%;transform:translateX(-50%);display:flex;flex-direction:column;align-items:center;gap:6px;pointer-events:none;z-index:4}
.turn-indicators{display:flex;gap:64px;background:#142330db;padding:7px 16px;border-radius:30px;color:#526274;font-size:22px}
.turn-indicators .lit{color:#ffb331;text-shadow:0 0 12px #ffb331}
#adas-state{background:#f5faf5ed;color:#345851;padding:5px 12px;border-radius:12px;font-size:11px;white-space:nowrap}
#adas-state[data-level="danger"]{background:#b92923;color:white}
#adas-state[data-level="caution"]{background:#ffdf9f;color:#674011}
''';p.write_text(s,encoding='utf-8')
