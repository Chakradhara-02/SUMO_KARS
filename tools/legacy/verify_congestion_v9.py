import json,time
from pathlib import Path
import traci
from kars.city import build_city_network,city_route
from kars.city_routing import CityRouter
from kars.sumo_setup import binary

router=CityRouter(build_city_network());current=city_route('n2_2','n4_0')['edges'][0]
baseline=router.alternatives(current,'n4_0')[0]
blocked=next(e for e in baseline['edges'][1:-3] if float(router.edges[e].find('lane').get('length'))>65)
label='congestion_probe_'+str(time.time_ns())
traci.start([binary('sumo'),'--net-file',str(build_city_network()),'--step-length','.1','--no-step-log','true','--time-to-teleport','-1'],label=label)
con=traci.getConnection(label)
try:
 con.route.add('queue',[blocked])
 con.route.add('probe_route',baseline['edges']);con.vehicle.add('probe_ego','probe_route',departPos='10',departLane='0',departSpeed='0');con.vehicle.setSpeed('probe_ego',0)
 for i in range(12):
  con.vehicle.add('queue_'+str(i),'queue',departPos=str(12+(i//2)*8),departLane=str(i%2),departSpeed='0')
  con.vehicle.setSpeed('queue_'+str(i),0)
 for _ in range(20):con.simulationStep()
 queue=con.edge.getLastStepHaltingNumber(blocked);assert queue>=8,queue
 alternatives=router.alternatives(current,'n4_0',con)
 chosen=alternatives[0]
 assert blocked not in chosen['edges'],(blocked,chosen)
 con.vehicle.setRoute('probe_ego',chosen['edges'])
 assert list(con.vehicle.getRoute('probe_ego'))==chosen['edges']
 report={'start':'Central Chowk','destination':'Government Hospital','blocked_edge':blocked,'measured_halted_vehicles':queue,'baseline_distance_m':baseline['distance'],'selected_distance_m':chosen['distance'],'baseline_edges':baseline['edges'],'selected_edges':chosen['edges'],'congested_route_score':router.score(baseline['edges']),'selected_route_score':chosen['score'],'selected_avoids_queue':True,'objective':'observed travel time + halted-vehicle delay + distance / 30 + junction delay'}
 assert chosen['score']<report['congested_route_score']
 report['native_reroute_applied']=True
 Path('outputs/v9_congestion_validation.json').write_text(json.dumps(report,indent=2))
 print(json.dumps(report,indent=2))
finally:con.close()
