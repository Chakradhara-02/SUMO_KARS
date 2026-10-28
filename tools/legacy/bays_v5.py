from pathlib import Path
p=Path('kars/city.py');s=p.read_text();s=s.replace("    for name,root in [('metro.nodes.xml',nodes)","""    for place in CITY_POINTS:
        x,y,z=positions[place['id']]
        dx=55 if x<=360 else -55;dy=60 if y<=400 else -60
        dest='arrival_'+place['id'];node(dest,x+dx,y+dy,z)
        ET.SubElement(edges,'edge',id=place['id']+'__'+dest,**{'from':place['id'],'to':dest},
                      numLanes='1',width='3.4',speed='4.17',priority='1',disallow='truck bus',
                      name=place['name']+' arrival driveway',shape=f'{x},{y},{z} {x+dx},{y+dy},{z}')
    for name,root in [('metro.nodes.xml',nodes)""")
a=s.index("    tree=ET.parse(path)");b=s.index("    tree.write(path",a)
s=s[:a]+'''    tree=ET.parse(path)
    for logic in tree.getroot().findall('tlLogic'):
        greens=[p.get('state') for p in logic.findall('phase') if 'y' not in p.get('state').lower() and 'g' in p.get('state').lower()]
        for phase in list(logic.findall('phase')):logic.remove(phase)
        for state in greens:
            ET.SubElement(logic,'phase',duration='25',state=state)
            ET.SubElement(logic,'phase',duration='3',state=''.join('y' if c.lower()=='g' else 'r' for c in state))
            ET.SubElement(logic,'phase',duration='2',state='r'*len(state))
''' +s[b:]
s=s.replace("if d.get('to')!=destination:continue", "if d.get('to')!='arrival_'+destination:continue")
s=s.replace("edge_ids=[e for e in con.edge.getIDList() if not e.startswith(':')]", "edge_ids=[e for e in con.edge.getIDList() if not e.startswith(':') and '__arrival_' not in e]")
p.write_text(s)
p=Path('kars/city_routing.py');s=p.read_text();s=s.replace("        for end, edge in self.edges.items():\n            if edge.get('to') != destination:", "        goal='arrival_'+destination if any(e.get('to')=='arrival_'+destination for e in self.edges.values()) else destination\n        for end, edge in self.edges.items():\n            if edge.get('to') != goal:")
p.write_text(s)
p=Path('kars/city_infrastructure.py');s=p.read_text().replace("end=max(12.,length-22);start=max(2.,end-24)","end=max(12.,length-10);start=max(2.,end-14)")
p.write_text(s)
# Only this in-progress v5 network is regenerated; archived v4 runs are preserved.
p=Path('sumo/network/city/metro_signals_v5.net.xml')
if p.exists():p.unlink()
