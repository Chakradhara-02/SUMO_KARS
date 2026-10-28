from pathlib import Path
import subprocess,xml.etree.ElementTree as ET
from kars.city import build_city_network,city_route
from kars.sumo_setup import binary
out=Path('outputs/metro_smoke');out.mkdir(parents=True,exist_ok=True)
routes=ET.Element('routes')
ET.SubElement(routes,'vType',id='car',maxSpeed='22.2',accel='2.2',decel='4.5',laneChangeModel='SL2015',maxSpeedLat='.65',lcAccelLat='.3',lcMaxSpeedLatStanding='0')
for i,(start,end) in enumerate([('n0_0','n4_4'),('n0_2','n4_2'),('n0_4','n4_0')]):
 route=city_route(start,end)
 ET.SubElement(routes,'route',id='r'+str(i),edges=' '.join(route['edges']))
 ET.SubElement(routes,'vehicle',id='ego'+str(i),type='car',route='r'+str(i),depart=str(i),departSpeed='5')
ET.ElementTree(routes).write(out/'routes.xml')
result=subprocess.run([binary('sumo'),'--net-file',str(build_city_network()),'--route-files',str(out/'routes.xml'),'--end','240','--step-length','.2','--lateral-resolution','.2','--tripinfo-output',str(out/'tripinfo.xml'),'--fcd-output',str(out/'motion.xml'),'--collision-output',str(out/'collisions.xml'),'--collision.check-junctions','true','--no-step-log','true'],capture_output=True,text=True,timeout=45)
print('SUMO exit:',result.returncode);print(result.stderr[-3000:]);print(result.stdout[-500:])
if result.returncode:raise SystemExit(result.returncode)
trips=ET.parse(out/'tripinfo.xml').getroot();print('Arrived:',len(trips.findall('tripinfo')))
print([(v.get('id'),v.get('duration')) for v in trips.findall('tripinfo')])

assert not ET.parse(out/'collisions.xml').getroot().findall('collision')
print('Recorded collision events: 0')
