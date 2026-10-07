"""Static ontology plus cycle-specific dynamic RDF, queried by real SPARQL."""
from dataclasses import asdict
import time
import xml.etree.ElementTree as ET
from rdflib import Graph, Namespace, Literal, RDF, XSD
from rdflib.plugins.sparql import prepareQuery
from .models import Constraint, ROOT

K = Namespace('https://sumo-kars.local/traffic#')

class KnowledgeGraph:
    def __init__(self):
        self.static = Graph().parse(ROOT / 'knowledge_graph/ontology/traffic.ttl')
        self.dynamic = Graph()
        self.query_seconds = 0.
        self.rows = []
        self.constraint_query = prepareQuery((ROOT/'knowledge_graph/queries/constraints.rq').read_text())
        network=ROOT/'sumo/network/road.net.xml'
        if network.exists():
            for edge in ET.parse(network).getroot().findall('edge'):
                if edge.get('id','').startswith(':'):
                    continue
                road=K[edge.get('id')]
                self.static.add((road,RDF.type,K.Road))
                lanes=edge.findall('lane')
                for index,lane in enumerate(lanes):
                    node=K[lane.get('id')]
                    for triple in [(node,RDF.type,K.Lane),(node,K.isOn,road),
                                   (node,K.hasSpeedLimit,Literal(float(lane.get('speed')))),
                                   (node,K.hasShape,Literal(lane.get('shape')))]:
                        self.static.add(triple)
                    if index>0:
                        self.static.add((node,K.hasRightLane,K[lanes[index-1].get('id')]))
                    if index+1<len(lanes):
                        self.static.add((node,K.hasLeftLane,K[lanes[index+1].get('id')]))
            for link in ET.parse(network).getroot().findall('connection'):
                start=K[link.get('from')+'_'+link.get('fromLane')]
                end=K[link.get('to')+'_'+link.get('toLane')]
                self.static.add((start,K.hasNextLane,end))
                self.static.add((end,K.hasPreviousLane,start))

    def update(self, vehicles, constraints, observed_time):
        self.dynamic = Graph()
        self.dynamic.bind('k', K)
        for vehicle in vehicles:
            subject = K[vehicle.vehicle_id]
            self.dynamic.add((subject, RDF.type, K.Vehicle))
            if vehicle.vehicle_id=='ego':
                self.dynamic.add((subject,RDF.type,K.EgoVehicle))
            for key, value in vehicle.record().items():
                self.dynamic.add((subject, K[key], Literal(value)))
            self.dynamic.add((subject, K.locatedAt, K[vehicle.lane_id]))
            self.dynamic.add((subject, K.hasSpeed, Literal(vehicle.speed)))
            if vehicle.traffic_light:
                # A signal may be green for one movement and red for another.
                signal=K[vehicle.traffic_light + '_' + vehicle.lane_id]
                self.dynamic.add((signal,RDF.type,K.TrafficLight))
                self.dynamic.add((signal,K.hasCurrentColor,Literal(vehicle.traffic_light_state)))
        for i, constraint in enumerate(constraints):
            subject = K[f'constraint_{i}']
            self.dynamic.add((subject, RDF.type, K.Constraint))
            for key, value in asdict(constraint).items():
                self.dynamic.add((subject, K[key], Literal(value)))
        self.dynamic.add((K.snapshot, K.timestamp, Literal(observed_time)))

    def constraints(self):
        begin = time.perf_counter()
        rows = list(self.dynamic.query(self.constraint_query))
        self.query_seconds = time.perf_counter() - begin
        self.rows = [dict(zip(['kind','start','end','lane','speed','begin','finish','source'],
                             [x.toPython() for x in row])) for row in rows]
        return [Constraint(**row) for row in self.rows]

    def export(self, folder):
        self.static.serialize(folder/'static.ttl', format='turtle')
        self.dynamic.serialize(folder/'dynamic.ttl', format='turtle')

def vehicle_constraints(vehicles, now, config, uncertainty=False):
    result = []
    for v in vehicles:
        if v.vehicle_id == 'ego' or v.road_id not in ('in','out'):
            continue
        age = max(0., now-v.timestamp)
        margin = config['safety_gap'] + (config['uncertainty_growth']*age if uncertainty else 0)
        for step in range(config['horizon'] + 1):
            future = step*config['dt']
            # Extension: conservatively include braking and constant-speed predictions.
            x = v.x + v.speed*(future + (age if uncertainty else 0))
            total = future + age
            decel = abs(config['min_acceleration'])
            braking_time = min(total, v.speed / decel)
            lower = v.x + v.speed * braking_time - .5 * decel * braking_time**2 if uncertainty else x
            # A vehicle straddling a lane boundary occupies both lanes.
            lanes = [v.lane]
            if abs(v.lateral_position) > (config['lane_width'] - v.width) / 2:
                adjacent = v.lane + (1 if v.lateral_position > 0 else -1)
                if 0 <= adjacent < config['lanes']:
                    lanes.append(adjacent)
            for lane in lanes:
                result.append(Constraint('spatial_temporal', lower-v.length-margin,
                                         x+margin, lane, begin=now+future-.5*config['dt'],
                                         finish=now+future+.5*config['dt'], source=v.vehicle_id))
    return result
