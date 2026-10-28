from pathlib import Path
p=Path('kars/city.py');s=p.read_text().replace("CITY_NETWORK_VERSION = 'metro_v2'", "CITY_NETWORK_VERSION = 'metro_v3'")
s=s.replace('            u,v=positions[start],positions[end]', '            u,v=positions[a],positions[b]')
s=s.replace("            ET.SubElement(edges,'edge',id=start+'__'+end", "            if start!=a:shape.reverse()\n            ET.SubElement(edges,'edge',id=start+'__'+end")
s=s.replace("curved=(x+y)%3==1", "curved=False")
p.write_text(s)
p=Path('kars/simulation.py');s=p.read_text().replace("city_network='metro_v2.net.xml'", "city_network='metro_v3.net.xml'");p.write_text(s)
p=Path('kars/console.py');s=p.read_text();old="    city_path=ROOT/'sumo/network/city/city.net.xml' if version=='legacy' else build_city_network() if scenario=='city' else None"
new="""    city_path=None
    if scenario=='city':
        known={'legacy':'city.net.xml','indian_city.net.xml':'indian_city.net.xml',
               'metro_v2.net.xml':'metro_v2.net.xml','metro_v3.net.xml':'metro_v3.net.xml'}
        if version and version not in known:raise ValueError('Unknown city network version')
        city_path=ROOT/'sumo/network/city'/known[version] if version else build_city_network()
        if version=='metro_v3.net.xml' and not city_path.exists():city_path=build_city_network()"""
assert old in s;s=s.replace(old,new);p.write_text(s)
p=Path('simulation_ui/app.js');s=p.read_text(encoding='utf-8');s=s.replace(" const key=next+(legacy?'-legacy':'');if(key===networkKind)return;", " const version=next==='city'&&!cityPreview?(legacy?'legacy':currentRun()?.manifest.city_network):null;\n const key=next+(version?'-'+version:'');if(key===networkKind)return;")
s=s.replace("(legacy?'&version=legacy':'')", "(version?'&version='+encodeURIComponent(version):'')")
p.write_text(s,encoding='utf-8')
