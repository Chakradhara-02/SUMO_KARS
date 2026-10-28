from pathlib import Path
p=Path('kars/city.py');s=p.read_text();s=s.replace("            record={**ego.record()", "            actual_route=list(con.vehicle.getRoute('ego'))[max(0,con.vehicle.getRouteIndex('ego')):]\n            navigation=router.journey(actual_route,con.vehicle.getLanePosition('ego') if not ego.road_id.startswith(':') else 0)\n            if ego.road_id.startswith(':'):navigation['instruction']='Completing junction manoeuvre'\n            record={**ego.record()")
s=s.replace("'remaining':max(0,trip['distance']-record['distance'])", "**navigation")
p.write_text(s)
p=Path('simulation_ui/index.html');s=p.read_text(encoding='utf-8');needle='<p id="city-route-summary"';i=s.index(needle)
s=s[:i]+'''<div class="journey-strip" aria-label="Live journey"><div><small>REMAINING</small><b id="journey-distance">—</b></div><div><small>ESTIMATED TIME</small><b id="journey-eta">—</b></div><div><small>NEXT MANOEUVRE</small><b id="journey-turn">Choose a destination</b></div><div><small>ROUTE OPTIONS</small><b id="journey-options">—</b></div></div>'''+s[i:]
p.write_text(s,encoding='utf-8')
p=Path('simulation_ui/app.js');s=p.read_text(encoding='utf-8');needle='function renderDriving(){'
s=s.replace(needle,needle+"if(frame.city){const c=frame.city;$('journey-distance').textContent=(c.remaining/1000).toFixed(2)+' km';$('journey-eta').textContent=Number.isFinite(c.eta)?Math.ceil(c.eta/60)+' min estimate':'Measuring';$('journey-turn').textContent=(c.instruction||'Follow the route')+(Number.isFinite(c.junction_distance)?' · '+Math.round(c.junction_distance)+' m':'');$('journey-options').textContent=(c.alternatives?.length||1)+' assessed';}")
p.write_text(s,encoding='utf-8')
p=Path('simulation_ui/style.css');s=p.read_text(encoding='utf-8');s+='''
.journey-strip{display:grid;grid-template-columns:1fr 1fr 2fr 1fr;gap:12px;padding:16px;background:#eef4f6;border:1px solid #d7e2e7;border-radius:12px;margin-top:16px}
.journey-strip div{display:flex;flex-direction:column;gap:7px}.journey-strip small{font-size:9px;letter-spacing:1px;color:#6d8292}.journey-strip b{font-size:13px;color:#233f53}
@media(max-width:700px){.journey-strip{grid-template-columns:1fr 1fr}.journey-strip b{font-size:12px}}
''';p.write_text(s,encoding='utf-8')
