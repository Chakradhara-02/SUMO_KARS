import json
import math
import time
import hashlib
import platform
import traceback
from dataclasses import asdict
from pathlib import Path
import numpy as np
import pandas as pd
import traci
from .models import ROOT, State, Vehicle, Constraint, load_config
from .sumo_setup import binary, build_network
from .knowledge import KnowledgeGraph, vehicle_constraints
from .communication import Channel
from .planning import Planner, emergency
from .scenarios import ScenarioWorld, prepare_routes, prepare_additional, signal_constraints
from .control import TrajectoryTracker, collision_risk
from .storage import atomic_json, read_text_retry, read_json

SCENARIOS = ['static','semi_dynamic','dynamic','emergency','iot_delay','demo','city']
ALGORITHMS = ['kars','kars_delay','astar','rs','city']

def collect(connection, now):
    vehicles = []
    for vehicle_id in connection.vehicle.getIDList():
        domain = connection.vehicle
        tls = domain.getNextTLS(vehicle_id)
        x,y = domain.getPosition(vehicle_id)
        lane_id = domain.getLaneID(vehicle_id)
        vehicles.append(Vehicle(vehicle_id,now,x,y,lane_id,domain.getLaneIndex(vehicle_id),
                                domain.getSpeed(vehicle_id),domain.getAcceleration(vehicle_id),
                                domain.getAngle(vehicle_id),domain.getRoadID(vehicle_id),
                                tls[0][0] if tls else '',tls[0][3] if tls else '',
                                connection.lane.getMaxSpeed(lane_id),
                                length=domain.getLength(vehicle_id),width=domain.getWidth(vehicle_id),
                                lateral_position=domain.getLateralLanePosition(vehicle_id)))
    return vehicles

def road_constraints(connection, ego, now, scenario, events, config):
    constraints = [Constraint('spatial_speed',0,1000,speed=16,source='road speed'),
                   Constraint('marking',80,140,source='solid lane marking'),
                   Constraint('spatial_speed',650,800,speed=8,source='speed-limit zone'),
                   Constraint('spatial_speed',420,450,speed=5,source='crossing advisory')]
    if scenario in ('semi_dynamic','demo','iot_delay'):
        constraints.append(Constraint('spatial',280,315,lane=0,source='construction'))
        if now>=10:
            constraints.append(Constraint('spatial_temporal',360,390,lane=1,begin=10,finish=80,source='temporary roadblock'))
    if scenario=='demo' and now>=18:
        constraints.append(Constraint('spatial_speed',300,400,speed=7,source='updated speed limit'))
    constraints += signal_constraints(connection,ego,now,config['horizon']*config['dt'])
    if scenario=='emergency' and 8<=now<18:
        if 'emergency_x' not in events:
            events['emergency_x'] = ego.x+ego.speed**2/(2*abs(config['min_acceleration']))+config['safety_gap']+4
        constraints.append(Constraint('spatial_temporal',events['emergency_x'],events['emergency_x']+5,
                                      begin=8,finish=18,source='all-lane emergency blockage'))
    return constraints

def snapshot_json(plan):
    def nodes(graph):
        return [{'id':n,**asdict(graph.nodes[n]['state']),'layer':graph.nodes[n]['layer']} for n in graph]
    return {'raw':nodes(plan['raw']),'adjusted':nodes(plan['adjusted']),
            'edges':list(plan['adjusted'].edges),'chain':plan['chain'],
            'candidates':[{'lane':c['lane'],'margin':c['margin'],'cost':c['cost'],'score':c['score'],
                           'nodes':list(c['graph'])} for c in plan['candidates']],
            'selected_lane':plan['selected_lane'],'trajectory':plan['trajectory'],
            'diagnostics':plan.get('diagnostics',{}),
            'plan_time':plan['raw'].nodes[0]['state'].t,
            'removed_edges':len(plan['rejected']),'emergency':plan['emergency'],
            'emergency_reason':plan.get('emergency_reason',''),
            'controlled_stop':plan.get('controlled_stop',False),'control_reason':plan.get('control_reason','')}

def summarize(frame, collisions, arrived, packet_channel, config):
    if frame.empty:
        raise RuntimeError('No ego samples recorded.')
    acceleration = frame.acceleration.to_numpy()
    jerk = np.diff(acceleration)/config['simulation_dt']
    clearance = frame.clearance.dropna()
    return {'success':int(arrived and collisions==0),'arrived':int(arrived),'collision_events':collisions,
            'travel_time':float(frame.timestamp.iloc[-1]-frame.timestamp.iloc[0]),
            'average_speed':float(frame.speed.mean()),'path_length':float(frame.distance.iloc[-1]-frame.distance.iloc[0]),
            'acceleration_rms':float(np.sqrt(np.mean(acceleration**2))),
            'max_acceleration':float(np.max(np.abs(acceleration))),
            'jerk_rms':float(np.sqrt(np.mean(jerk**2))) if len(jerk) else 0.,
            'max_jerk':float(np.max(np.abs(jerk))) if len(jerk) else 0.,
            'minimum_clearance':float(clearance.min()) if len(clearance) else None,
            'emergency_entries':int(((frame.emergency==1)&(frame.emergency.shift(fill_value=0)==0)).sum()),
            'rule_violations':int(frame.rule_violation.sum()),
            'planning_ms':float(frame.loc[frame.planned==1,'planning_seconds'].mean()*1000),
            'query_ms':float(frame.loc[frame.planned==1,'query_seconds'].mean()*1000),
            'rs_ms':float(frame.loc[frame.planned==1,'rs_seconds'].mean()*1000),
            'cycle_ms':float(frame.cycle_seconds.mean()*1000),
            'packets_sent':packet_channel.sent,'packets_lost':packet_channel.dropped}

def _run_simulation(scenario='demo',algorithm='kars_delay',seed=1,duration=None,gui=False,
                   delay=None,loss=None,output=None,control_file=None,make_plots=True,density=9,
                   config_overrides=None):
    if scenario not in SCENARIOS or algorithm not in ALGORITHMS:
        raise ValueError('Unknown scenario or algorithm')
    config = load_config(config_overrides)
    duration = config['duration'] if duration is None else duration
    output = Path(output) if output else ROOT/'outputs'/f'{scenario}_{algorithm}_seed{seed}'
    output.mkdir(parents=True,exist_ok=True)
    if not (ROOT/'sumo/network/road.net.xml').exists():
        build_network()
    use_channel = scenario=='iot_delay' or delay is not None or loss is not None
    channel = Channel(config['delay'] if delay is None and use_channel else (delay or 0),
                      config['packet_loss'] if loss is None and use_channel else (loss or 0),seed,
                      jitter=config['delay_jitter'],outage=(config['outage_begin'],config['outage_end']))
    planner, kg = Planner(config,algorithm), KnowledgeGraph()
    from .reachable_set import offline_rs
    offline_rs(config,output/'offline_transitions.json')
    label = f'kars_{time.time_ns()}'
    routes = prepare_routes(output,scenario,density)
    additional = prepare_additional(output)
    traci.start([binary('sumo-gui' if gui else 'sumo'),'-c',str(ROOT/'sumo/configs/demo.sumocfg'),
                 '--route-files',str(routes),'--additional-files',str(additional),'--seed',str(seed),'--end',str(duration),
                 '--step-length',str(config['simulation_dt']),'--collision.check-junctions','true',
                 '--lanechange.duration',str(config['lane_change_duration']),
                 '--lanechange-output',str(output/'lane_changes.xml'),
                 '--tripinfo-output',str(output/'tripinfo.xml'),
                 '--tripinfo-output.write-unfinished','true',
                 '--start','--quit-on-end'],label=label)
    connection = traci.getConnection(label)
    manifest=read_json(output/'manifest.json')
    manifest.update(sumo_version=connection.getVersion()[1],
                    actual_delay=channel.delay,actual_loss=channel.loss,
                    input_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in (ROOT/'sumo/network/road.net.xml',routes,additional)})
    atomic_json(output/'manifest.json',manifest)
    traffic_rows, ego_rows, plans = [], [], []
    events, collisions, arrived, last_plan_time = {}, 0, False, -10.
    world = ScenarioWorld(scenario,config,events)
    tracker = TrajectoryTracker(config)
    live_snapshot = {}
    trace = (output/'trace.jsonl').open('w',encoding='utf-8')
    realtime_factor = config['realtime_factor']
    stopped = False
    emergency_blocked = False
    last_signature, active_plan, current_constraints = None, None, []
    target_speed, target_lane = 8.,1
    query_seconds = planning_seconds = rs_seconds = 0.
    try:
        while connection.simulation.getTime()<duration and connection.simulation.getMinExpectedNumber()>0:
            if control_file and Path(control_file).exists():
                command = read_text_retry(Path(control_file)).strip()
                try:
                    control_data = json.loads(command)
                    command = control_data['action']
                    realtime_factor = max(0.,float(control_data.get('realtime_factor',realtime_factor)))
                except (ValueError,TypeError,KeyError):
                    pass
                if command=='stop':
                    stopped = True
                    break
                if command=='pause':
                    atomic_json(output/'status.json',{'state':'paused','time':connection.simulation.getTime()})
                    time.sleep(.1)
                    continue
            begin = time.perf_counter()
            connection.simulationStep()
            now = connection.simulation.getTime()
            collisions += sum('ego' in (c.collider,c.victim) for c in connection.simulation.getCollisions())
            if 'ego' in connection.simulation.getArrivedIDList():
                arrived = True
                break
            vehicles = collect(connection,now)
            ego = next((v for v in vehicles if v.vehicle_id=='ego'),None)
            if ego is None:
                continue
            if 'initialized' not in events:
                connection.vehicle.setLaneChangeMode('ego',512)
                # Retain SUMO's independent collision, braking, signal and right-of-way safety.
                connection.vehicle.setSpeedMode('ego',31)
                if gui and connection.gui.getIDList():
                    view = connection.gui.getIDList()[0]
                    connection.gui.trackVehicle(view,'ego')
                    connection.gui.setZoom(view,1200.)
                events['initialized'] = True
            world.step(connection,now,ego)
            # Removed actors must disappear from the same sensor cycle.
            vehicles = [v for v in vehicles if v.vehicle_id in connection.vehicle.getIDList()]
            road = road_constraints(connection,ego,now,scenario,events,config)
            obstacle_information=json.dumps([asdict(c) for c in road if c.kind in ('spatial','spatial_temporal')])
            for vehicle in vehicles:
                vehicle.obstacle_information=obstacle_information
            traffic_rows += [v.record() for v in vehicles]
            packet = channel.transmit(now,{'vehicles':vehicles,'constraints':road,'time':now})
            age = now-packet['time'] if packet else now
            uncertainty = algorithm=='kars_delay'
            local = [v for v in vehicles if math.hypot(v.x-ego.x,v.y-ego.y)<=config['sensor_range']]
            local_ids = {v.vehicle_id for v in local}
            fused = local + ([v for v in packet['vehicles'] if v.vehicle_id not in local_ids
                             and math.hypot(v.x-ego.x,v.y-ego.y)>config['sensor_range']] if packet else [])
            remote = vehicle_constraints(fused,now,config,uncertainty,ego)
            # Map rules and nearby infrastructure are available locally. Distant events
            # arrive only via IoT; replanning cannot see undelivered event changes.
            local_road = [c for c in road if c.kind in ('marking','spatial_speed') and c.source!='updated speed limit'
                          or c.start-ego.x<=config['sensor_range'] and c.end>=ego.x]
            local_sources = {c.source for c in local_road}
            distant_road = [c for c in packet['constraints'] if c.source not in local_sources
                            and not c.source.startswith('traffic light')] if packet else []
            delivered_constraints = local_road + distant_road + remote
            communication_degraded = uncertainty and (packet is None or age>config['stale_timeout'])
            if communication_degraded:
                # Missing remote packets alone are not a physical emergency.
                # Keep the stopping distance inside the available local sensing range.
                visibility_speed = min(config['max_speed'],math.sqrt(
                    2*abs(config['min_acceleration'])*max(0.,config['sensor_range']-config['safety_gap'])))
                delivered_constraints.append(Constraint('spatial_speed',ego.x,ego.x+1000,
                                                        speed=visibility_speed,source='local visibility speed cap'))
            signature = tuple((c.kind,c.source,c.speed,c.start,c.end) for c in delivered_constraints
                              if c.source not in {v.vehicle_id for v in fused})
            changed = signature!=last_signature
            planned = now-last_plan_time>=config['dt']-1e-7 or changed
            if planned:
                last_plan_time, last_signature = now,signature
                if packet and 'braked' in events and packet['time']>=events['braked']:
                    if any(v.vehicle_id=='lead' and v.acceleration<-.5 for v in packet['vehicles']):
                        events.setdefault('remote_reaction_time',now-events['braked'])
                if 'braked' in events and any(v.vehicle_id=='lead' and v.acceleration<-.5 for v in fused):
                    events.setdefault('knowledge_reaction_time',now-events['braked'])
                if algorithm in ('kars','kars_delay'):
                    kg.update(fused,delivered_constraints,now)
                    current_constraints = kg.constraints()
                    query_seconds = kg.query_seconds
                else:
                    # Baselines get exactly the same delivered packet without RDF conversion.
                    current_constraints = delivered_constraints
                    query_seconds = 0.
                active_plan = planner.plan(tracker.planning_state(ego,now),current_constraints)
                planning_seconds, rs_seconds = active_plan['planning_seconds'],active_plan['rs_seconds']
                stopping_distance = ego.speed**2/(2*abs(config['min_acceleration']))
                imminent = any(c.kind in ('spatial','spatial_temporal') and c.lane==-1
                               and c.begin<=now<=c.finish and c.end>=ego.x
                               and c.start-ego.x<=stopping_distance+config['safety_gap']+5
                               for c in current_constraints)
                full_block_active = any(c.kind in ('spatial','spatial_temporal') and c.lane == -1
                                        and c.begin<=now<c.finish and c.end>=ego.x for c in current_constraints)
                emergency_blocked = full_block_active and (imminent or emergency_blocked)
                if emergency_blocked:
                    active_plan['emergency'] = True
                    active_plan['trajectory'] = None
                    active_plan['controlled_stop'] = False
                    active_plan['control_reason'] = ''
                    active_plan['emergency_reason'] = 'Active all-lane obstacle inside the stopping envelope; waiting until it clears.'
                if active_plan['trajectory']:
                    target_speed = active_plan['trajectory']['velocity'][1]
                    target_lane = active_plan['trajectory']['lane'][1]
                snapshot = snapshot_json(active_plan)
                snapshot.update({'time':now,'age':age,'constraints':[asdict(c) for c in current_constraints],
                                 'triples':len(kg.static)+len(kg.dynamic),'ego':ego.record(),
                                 'local_vehicles':len(local),'remote_vehicles':len(fused)-len(local),
                                 'planning_ms':planning_seconds*1000,'query_ms':query_seconds*1000})
                uses_query = algorithm in ('kars','kars_delay')
                snapshot['pipeline'] = {
                    'query_used':uses_query,'static_triples':len(kg.static),
                    'dynamic_triples':len(kg.dynamic) if uses_query else 0,
                    'query':(ROOT/'knowledge_graph/queries/constraints.rq').read_text() if uses_query else '',
                    'query_rows':kg.rows[:6] if uses_query else [],
                    'rdf_groups':kg.evidence() if uses_query else {},
                }
                plans.append(snapshot)
                live_snapshot = snapshot.copy()
            if active_plan and active_plan['emergency']:
                target_speed = emergency(State(ego.x,ego.speed,ego.lane,now),config)
            commands = tracker.command(connection,ego,now,target_speed,target_lane,
                                       bool(active_plan and active_plan['emergency']))
            clearance, ttc = collision_risk(ego,vehicles)
            physical_blocks = [c for c in road if c.kind in ('spatial','spatial_temporal') and c.lane in (-1,ego.lane)
                               and c.begin<=now<=c.finish and c.end>=ego.x]
            if physical_blocks:
                clearance = min([c.start-ego.x for c in physical_blocks]+([clearance] if clearance is not None else []))
            violation = any(c.kind in ('spatial_speed','spatial_temporal_speed') and c.start<=ego.x<=c.end
                            and c.begin<=now<=c.finish and ego.speed>c.speed+.5 for c in road)
            violation |= any(c.start<=ego.x<=c.end for c in physical_blocks)
            ego_rows.append({**ego.record(),'distance':connection.vehicle.getDistance('ego'),'clearance':clearance,
                             'emergency':int(active_plan['emergency']) if active_plan else 0,'planned':int(planned),
                             'planning_seconds':planning_seconds,'query_seconds':query_seconds,'rs_seconds':rs_seconds,
                             'knowledge_age':age,'rule_violation':int(violation),
                             'cycle_seconds':time.perf_counter()-begin,'ttc':ttc,**commands})
            signals = [{'id':tls,'state':connection.trafficlight.getRedYellowGreenState(tls),
                        'next_switch':connection.trafficlight.getNextSwitch(tls)}
                       for tls in connection.trafficlight.getIDList()]
            live_snapshot.update(time=now,ego=ego.record(),vehicles=[v.record() for v in vehicles],
                                 age=age,clearance=clearance,ttc=ttc,commands=commands,signals=signals,
                                 packets={'sent':channel.sent,'lost':channel.dropped,'received':channel.received,
                                          'out_of_order':channel.out_of_order,'queued':len(channel.queue)},
                                 timeline=world.timeline,world_constraints=[asdict(c) for c in road],
                                 history=[{k:r[k] for k in ('timestamp','speed','acceleration','clearance','knowledge_age')}
                                          for r in ego_rows[-300:]],
                                 sensing={'range':config['sensor_range'],'packet_time':packet['time'] if packet else None,
                                          'degraded':communication_degraded,
                                          'local_ids':sorted(local_ids),
                                          'remote_ids':[v.vehicle_id for v in fused if v.vehicle_id not in local_ids],
                                          'observations':[{'id':v.vehicle_id,'x':v.x,'y':v.y,'speed':v.speed,
                                                           'lane':v.lane_id,'timestamp':v.timestamp,
                                                           'source':'onboard' if v.vehicle_id in local_ids else 'IoT'} for v in fused[:32]]},
                                 emergency=bool(active_plan and active_plan['emergency']),
                                 emergency_reason=active_plan.get('emergency_reason','') if active_plan else '')
            atomic_json(output/'live.json',live_snapshot)
            atomic_json(output/'status.json',{'state':'running','time':now})
            # Streaming frames remain usable even if a run is interrupted.
            trace.write(json.dumps({k:live_snapshot[k] for k in ('time','ego','vehicles','signals',
                                    'age','clearance','ttc','commands','emergency','emergency_reason','sensing','world_constraints','timeline','packets')})+'\n')
            trace.flush()
            if realtime_factor > 0:
                remaining = config['simulation_dt']/realtime_factor - (time.perf_counter()-begin)
                if remaining > 0:
                    time.sleep(min(remaining,1.))
    finally:
        trace.close()
        connection.close()
    frame = pd.DataFrame(ego_rows)
    frame['jerk'] = frame.acceleration.diff().fillna(0)/config['simulation_dt']
    frame.to_csv(output/'ego.csv',index=False)
    pd.DataFrame(traffic_rows).to_csv(output/'traffic.csv',index=False)
    (output/'plans.json').write_text(json.dumps(plans))
    final_trajectory=next((p['trajectory'] for p in reversed(plans) if p['trajectory']),None)
    if final_trajectory:
        pd.DataFrame({k:v for k,v in final_trajectory.items() if isinstance(v,list)}).to_csv(output/'trajectory.csv',index=False)
    kg.export(output)
    metrics = summarize(frame,collisions,arrived,channel,config)
    metrics.update({'scenario':scenario,'algorithm':algorithm,'seed':seed,'delay':channel.delay,
                    'loss':channel.loss,'density_period':density,'sumo_safety_enabled':True,
                    'knowledge_reaction_time':events.get('knowledge_reaction_time'),
                    'remote_reaction_time':events.get('remote_reaction_time'),
                    'packets_received':channel.received,'packets_out_of_order':channel.out_of_order,
                    'jitter':channel.jitter,'physical_obstacles':scenario in ('semi_dynamic','demo','iot_delay','emergency'),
                    'continuous_lane_changes':True,'local_sensor_range':config['sensor_range'],
                    'minimum_ttc':float(frame.ttc.min()) if frame.ttc.notna().any() else None,
                    'speed_tracking_rmse':float(np.sqrt(np.mean(frame.speed_tracking_error**2))),
                    'lane_changes':int((frame.lane.diff().fillna(0)!=0).sum()),
                    'final_time':float(frame.timestamp.iloc[-1]),
                    'end_reason':'arrived' if arrived else 'cancelled' if stopped else 'duration_limit'})
    atomic_json(output/'events.json',events)
    atomic_json(output/'timeline.json',world.timeline)
    atomic_json(output/'metrics.json',metrics)
    if make_plots:
        from .visualization import plot_run
        plot_run(output)
    print(f'{scenario}/{algorithm}: arrived={arrived}, collisions={collisions}, output={output}',flush=True)
    return metrics


def run_simulation(scenario='demo',algorithm='kars_delay',seed=1,duration=None,gui=False,
                   delay=None,loss=None,output=None,control_file=None,make_plots=True,density=9,
                   config_overrides=None):
    """Persist provenance and lifecycle, including launch and runtime failures."""
    config = load_config(config_overrides)
    if duration is not None and (not math.isfinite(duration) or duration <= 0):
        raise ValueError('Duration must be finite and positive')
    if scenario=='city':algorithm='city'
    if density <= 0:
        raise ValueError('Traffic insertion period must be positive')
    folder = Path(output) if output else ROOT/'outputs'/f'{scenario}_{algorithm}_seed{seed}'
    folder.mkdir(parents=True,exist_ok=True)
    # A new run cannot inherit a previous run's completion or live frame.
    for filename in ('metrics.json','live.json','status.json'):
        (folder/filename).unlink(missing_ok=True)
    manifest = {'schema_version':2,'scenario':scenario,'algorithm':algorithm,'seed':seed,
                'duration':duration or config['duration'],'density_period':density,
                'delay':delay,'loss':loss,'config':config,'started_at':time.time(),
                'python':platform.python_version(),'sumo_binary':binary('sumo'),
                'source_hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in [ROOT/'main.py',*sorted((ROOT/'kars').glob('*.py'))]},
                'config_sha256':hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()}
    if scenario=='city':manifest.update(city_network='indian_city.net.xml',traffic_side='left')
    atomic_json(folder/'manifest.json',manifest)
    atomic_json(folder/'status.json',{'state':'starting','time':0.})
    try:
        if scenario=='city':
            from .city import run_city
            result=run_city(folder,config,seed,duration or config['duration'],gui,control_file)
        else:
            if algorithm=='city':raise ValueError('City routing requires the city scenario')
            result = _run_simulation(scenario,algorithm,seed,duration,gui,delay,loss,folder,
                                     control_file,make_plots,density,config_overrides)
        atomic_json(folder/'status.json',{'state':'cancelled' if result['end_reason']=='cancelled' else 'completed',
                                         'time':result['final_time'],'end_reason':result['end_reason']})
        manifest=read_json(folder/'manifest.json',manifest)
        manifest.update(finished_at=time.time(),end_reason=result['end_reason'])
        atomic_json(folder/'manifest.json',manifest)
        return result
    except Exception as error:
        atomic_json(folder/'status.json',{'state':'failed','error':str(error)})
        (folder/'error.log').write_text(traceback.format_exc())
        raise
