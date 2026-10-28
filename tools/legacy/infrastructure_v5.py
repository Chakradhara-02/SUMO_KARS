from pathlib import Path
p=Path('kars/city.py');s=p.read_text().replace("CITY_NETWORK_VERSION = 'metro_straight_v4'","CITY_NETWORK_VERSION = 'metro_signals_v5'")
s=s.replace('0<x<4 and 0<y<4)', 'True)')
needle="    return path\n\n\ndef city_route"
assert needle in s
s=s.replace(needle,"""    tree=ET.parse(path)
    for logic in tree.getroot().findall('tlLogic'):
        for phase in list(logic.findall('phase')):
            state=phase.get('state');phase.set('duration','3' if 'y' in state.lower() else '25' if 'g' in state.lower() else '2')
            if 'y' in state.lower():logic.insert(list(logic).index(phase)+1,ET.Element('phase',duration='2',state='r'*len(state)))
    tree.write(path,encoding='utf-8',xml_declaration=True)
    return path


def city_route""")
s=s.replace("    distance=sum(math.hypot", "    from .city_infrastructure import arrival_bay\n    bay=arrival_bay(build_city_network(),best[1][-1],next(p for p in CITY_POINTS if p['id']==destination))\n    distance=sum(math.hypot")
s=s.replace("'edges':best[1],'distance':distance,'shape':shape}", "'edges':best[1],'distance':distance,'shape':shape,'arrival_bay':bay}")
p.write_text(s)
p=Path('kars/console.py');s=p.read_text().replace("'metro_straight_v4.net.xml':'metro_straight_v4.net.xml'", "'metro_straight_v4.net.xml':'metro_straight_v4.net.xml','metro_signals_v5.net.xml':'metro_signals_v5.net.xml'").replace("if version=='metro_straight_v4.net.xml'", "if version=='metro_signals_v5.net.xml'").replace("'straight_city_v4'","'signal_city_v5'");p.write_text(s)
p=Path('kars/simulation.py');s=p.read_text().replace("city_network='metro_straight_v4.net.xml'","city_network='metro_signals_v5.net.xml'");p.write_text(s)
p=Path('kars/models.py');s=p.read_text().replace('    signals: int = 0','    signals: int = 0\n    indicator_reason: str = \'\'');p.write_text(s)
