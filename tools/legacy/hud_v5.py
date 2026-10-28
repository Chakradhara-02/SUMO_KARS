from pathlib import Path
p=Path('kars/city_infrastructure.py');s=p.read_text().replace("if abs(lateral_speed)>.08 and raw&3:\n        return base|(raw&3),'Changing lane '+('left' if raw&2 else 'right')", "if abs(lateral_speed)>.08:\n        indicator=(raw&3) or (2 if lateral_speed>0 else 1)\n        return base|indicator,'Changing lane '+('left' if indicator&2 else 'right')");p.write_text(s)
p=Path('simulation_ui/index.html');s=p.read_text(encoding='utf-8').replace('20261015-straight-city-v4','20261015-signals-city-v5')
s=s.replace('<span id="adas-state"', '<span id="indicator-reason" class="indicator-reason">Continuing straight</span><span id="next-signal" class="next-signal">Signal data pending</span><span id="adas-state"')
s=s.replace('Blue: road-aligned trajectory preview', 'Blue: navigation route and available motion preview')
p.write_text(s,encoding='utf-8')
p=Path('simulation_ui/app.js');s=p.read_text(encoding='utf-8')
s=s.replace("$('drive-speed').textContent=e?fmt(e.speed*3.6,0):'-';", """$('drive-speed').textContent=e?fmt(e.speed*3.6,0):'-';
 const ns=frame.city?.next_signal;$('indicator-reason').textContent=e?.indicator_reason||'No turn indication';
 $('next-signal').textContent=frame.city?.parked?'PARKED IN DESTINATION BAY':ns?({r:'RED',y:'AMBER',g:'GREEN'}[ns.color?.toLowerCase()]||'SIGNAL')+' · '+(ns.seconds===null?'--':ns.seconds)+' s · '+Math.max(0,Math.round(ns.distance))+' m':'No signal on the immediate approach';
 $('next-signal').dataset.aspect=ns?.color?.toLowerCase()||'off';""")
s=s.replace("currentRun()?.metrics.arrived?'DESTINATION REACHED'", "frame.city?.parked?'PARKED AT DESTINATION':currentRun()?.metrics.arrived?'DESTINATION REACHED'")
s=s.replace("`${frame.city_reachability.feasible_count} /", "`${frame.city_reachability.feasible_count} /")
s=s.replace("${frame.city_reachability.route_branches?.length||1} route branches", "${frame.city_reachability.route_branches?.length||1} route branches${frame.city_reachability.feasible_count===0?' · no feasible motion forecast; blue is route guidance':''}")
p.write_text(s,encoding='utf-8')
p=Path('simulation_ui/style.css');s=p.read_text(encoding='utf-8');s+='''
.next-signal{padding:6px 12px;background:#17364dec;color:white;border-radius:6px;font-size:12px;font-weight:700;white-space:nowrap}
.next-signal[data-aspect="r"]{background:#a72c2a}.next-signal[data-aspect="g"]{background:#177950}.next-signal[data-aspect="y"]{background:#f0bd3b;color:#302813}
.indicator-reason{font-size:10px;color:#183c50;background:#ffffffec;padding:3px 8px;border-radius:5px}
''';p.write_text(s,encoding='utf-8')
