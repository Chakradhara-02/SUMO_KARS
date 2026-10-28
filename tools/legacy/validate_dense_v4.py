from pathlib import Path
import random,subprocess,xml.etree.ElementTree as ET
import sumolib
from kars.city import build_city_network
from kars.sumo_setup import binary
out=Path('outputs/v4_dense_validation');out.mkdir(parents=True,exist_ok=True)
network=build_city_network();net=sumolib.net.readNet(str(network));edges=[e for e in net.getEdges() if e.allows('passenger')]
ring=[e for e in edges if e.getID().startswith('r') and '__r' in e.getID()]
rng=random.Random(71);routes=ET.Element('routes')
for name,kind in [('car','passenger'),('truck','truck')]:
 ET.SubElement(routes,'vType',id=name,vClass=kind,maxSpeed='22.2' if name=='car' else '16',accel='2.2',decel='4.5',sigma='.25',laneChangeModel='SL2015',maxSpeedLat='.65',lcAccelLat='.3',lcMaxSpeedLatStanding='0')
inserted=0
for i in range(180):
 kind='truck' if i%12==0 else 'car';pool=ring if kind=='truck' else edges
 for attempt in range(15):
  a,b=rng.sample(pool,2);path,cost=net.getFastestPath(a,b,vClass='truck' if kind=='truck' else 'passenger')
  if path:break
 else:continue
 ET.SubElement(routes,'route',id=f'r{i}',edges=' '.join(e.getID() for e in path))
 ET.SubElement(routes,'vehicle',id=f'{kind}_{i}',type=kind,route=f'r{i}',depart=str(i*.12),departLane='best',departSpeed='max');inserted+=1
ET.ElementTree(routes).write(out/'routes.xml')
result=subprocess.run([binary('sumo'),'--net-file',str(network),'--route-files',str(out/'routes.xml'),'--end','300','--step-length','.1','--lateral-resolution','.2','--collision.check-junctions','true','--collision-output',str(out/'collisions.xml'),'--tripinfo-output',str(out/'tripinfo.xml'),'--tripinfo-output.write-unfinished','true','--no-step-log','true'],capture_output=True,text=True,timeout=60)
(out/'engine.log').write_text(result.stdout+'\n'+result.stderr)
print('SUMO exit:',result.returncode,'vehicles:',inserted)
if result.returncode:print(result.stderr);raise SystemExit(result.returncode)
collisions=ET.parse(out/'collisions.xml').getroot().findall('collision');trips=ET.parse(out/'tripinfo.xml').getroot().findall('tripinfo')
arrived=[t for t in trips if float(t.get('arrival','-1'))>=0]
print('Arrived:',len(arrived),'recorded:',len(trips),'collisions:',len(collisions));print(result.stderr[-1600:])
assert not collisions
