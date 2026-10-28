from pathlib import Path
import subprocess,xml.etree.ElementTree as ET
from kars.city import city_route,build_city_network
from kars.city_infrastructure import write_arrival_area
from kars.sumo_setup import binary
out=Path('outputs/parking_v5_check');out.mkdir(parents=True,exist_ok=True)
trip=city_route('n0_0','n2_0');bay=trip['arrival_bay'];write_arrival_area(out/'parking.xml',bay)
r=ET.Element('routes');ET.SubElement(r,'vType',id='car',maxSpeed='13.9',length='4.7',width='1.8',laneChangeModel='SL2015',maxSpeedLat='.65',lcAccelLat='.3')
ET.SubElement(r,'route',id='r',edges=' '.join(trip['edges']));v=ET.SubElement(r,'vehicle',id='ego',type='car',route='r',depart='0',departLane='best',departSpeed='5');ET.SubElement(v,'stop',parkingArea=bay['id'],duration='8',parking='true')
ET.ElementTree(r).write(out/'routes.xml')
cmd=[binary('sumo'),'--net-file',str(build_city_network()),'--route-files',str(out/'routes.xml'),'--additional-files',str(out/'parking.xml'),'--step-length','.1','--end','200','--parking.maneuver','true','--fcd-output',str(out/'motion.xml'),'--stop-output',str(out/'stops.xml'),'--tripinfo-output',str(out/'trips.xml'),'--no-step-log','true']
result=subprocess.run(cmd,capture_output=True,text=True,timeout=30);print('Exit',result.returncode);print(result.stderr)
if result.returncode:raise SystemExit(result.returncode)
frames=[(float(t.get('time')),v.attrib) for t in ET.parse(out/'motion.xml').getroot() for v in t if v.get('id')=='ego']
near=[(t,v) for t,v in frames if abs(float(v['x'])-bay['x'])<8 and abs(float(v['y'])-bay['y'])<8 and float(v['speed'])<.1]
print('Bay:',bay);print('Stopped samples near bay:',near[:2],near[-2:]);print((out/'stops.xml').read_text()[-1500:])
