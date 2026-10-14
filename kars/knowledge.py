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
                    # SUMO numbers lanes from right to left. Outer boundaries
                    # follow the network shape; interior separators are dashed.
                    for side, outer in [('right',index==0),('left',index==len(lanes)-1)]:
                        feature=K[f"{lane.get('id')}_{side}"]
                        self.static.add((node,K.hasBoundary if outer else K.hasLaneMarking,feature))
                        self.static.add((feature,RDF.type,K.RoadBoundary if outer else K.LaneMarking))
                        self.static.add((feature,K.hasType,Literal(side+' bound' if outer else 'dashed')))
                        self.static.add((feature,K.hasShape,Literal(lane.get('shape'))))
                        offset=float(lane.get('width','3.2'))/2*(1 if side=='left' else -1)
                        self.static.add((feature,K.boundaryOffset,Literal(offset)))
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
            self.dynamic.add((subject, K.isOn, K[vehicle.lane_id]))
            self.dynamic.add((K[vehicle.road_id],K.has,subject))
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
            # Semantic features describe the same delivered constraints used by
            # SPARQL and pruning, so delayed IoT facts retain their provenance.
            if constraint.kind=='marking' or constraint.kind in ('spatial_speed','spatial_temporal_speed'):
                feature=K[f'feature_{i}']
                geometry=K[f'geometry_{i}']
                crossing=constraint.source=='crossing advisory'
                marking=constraint.kind=='marking'
                self.dynamic.add((feature,RDF.type,K.LaneMarking if marking else K.PedCrossing if crossing else K.SpeedLimitSign))
                self.dynamic.add((feature,K.hasBoundary,geometry))
                self.dynamic.add((feature,K.restricts,subject))
                self.dynamic.add((geometry,RDF.type,K.LaneSlice if marking else K.SpeedLimitZone))
                for key in ('start','end','lane','begin','finish'):
                    self.dynamic.add((geometry,K[key],Literal(getattr(constraint,key))))
                if marking:
                    self.dynamic.add((feature,K.hasType,Literal('solid')))
                else:
                    self.dynamic.add((feature,K.hasSpeedLimitValue,Literal(constraint.speed)))
                    self.dynamic.add((geometry,K.hasSpeedLimit,Literal(constraint.speed)))
                self.dynamic.add((feature,K.source,Literal(constraint.source)))
                for lane in range(3) if constraint.lane<0 else [constraint.lane]:
                    for road in ('in','out'):
                        lane_node=K[f'{road}_{lane}']
                        shape=self.static.value(lane_node,K.hasShape)
                        if shape is None:
                            continue
                        xs=[float(point.split(',')[0]) for point in str(shape).split()]
                        if max(xs)<constraint.start or min(xs)>constraint.end:
                            continue
                        self.dynamic.add((lane_node,K.hasLaneMarking if marking else K.within,feature if marking else geometry))
                if not marking:
                    for vehicle in vehicles:
                        if vehicle.road_id in ('in','out') and constraint.start<=vehicle.x<=constraint.end and (constraint.lane<0 or constraint.lane==vehicle.lane):
                            self.dynamic.add((K[vehicle.vehicle_id],K.within,geometry))
        self.dynamic.add((K.snapshot, K.timestamp, Literal(observed_time)))

    def evidence(self):
        """Bounded, deterministic examples of each relationship family."""
        groups={name:[] for name in ('Lane membership','Road boundaries','Lane markings',
                                    'Speed zones and crossings','Vehicle speeds','Signals','Planner constraints')}
        def record(s,p,o):
            return {'subject':str(s).split('#')[-1],'predicate':str(p).split('#')[-1],
                    'object':str(o).split('#')[-1] if str(o).startswith(str(K)) else str(o)}
        for graph in (self.dynamic,self.static):
            for s,p,o in sorted(graph,key=lambda t:tuple(map(str,t))):
                category=None
                if p in (K.isOn,K.locatedAt,K.has): category='Lane membership'
                elif p==K.hasBoundary or (s,RDF.type,K.RoadBoundary) in graph: category='Road boundaries'
                elif p==K.hasLaneMarking or (s,RDF.type,K.LaneMarking) in graph: category='Lane markings'
                elif p in (K.within,K.hasSpeedLimit,K.hasSpeedLimitValue,K.restricts) or any((s,RDF.type,t) in graph for t in (K.SpeedLimitZone,K.SpeedLimitSign,K.PedCrossing,K.LaneSlice)): category='Speed zones and crossings'
                elif p==K.hasSpeed: category='Vehicle speeds'
                elif p==K.hasCurrentColor: category='Signals'
                limit=128 if category in ('Road boundaries','Lane markings','Speed zones and crossings') else 36
                if category and len(groups[category])<limit:
                    groups[category].append(record(s,p,o))
        # One full restriction per source prevents repeated predicted occupancy
        # rows from hiding infrastructure restrictions in the evidence panel.
        sources=set()
        for subject in sorted(self.dynamic.subjects(RDF.type,K.Constraint),key=lambda s:int(str(s).rsplit('_',1)[-1])):
            source=self.dynamic.value(subject,K.source)
            if source in sources or len(sources)>=12: continue
            sources.add(source)
            groups['Planner constraints'].extend(record(*triple) for triple in sorted(
                self.dynamic.triples((subject,None,None)),key=lambda t:str(t[1])) if triple[1]!=RDF.type)
        return groups

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

def vehicle_constraints(vehicles, now, config, uncertainty=False, ego=None):
    result = []
    for v in vehicles:
        if v.vehicle_id == 'ego' or v.road_id not in ('in','out'):
            continue
        age = max(0., now-v.timestamp)
        # A known follower behind the ego rear bumper must not prevent forward
        # escape from its inflated future margin. Keep its occupancy for lane
        # transitions; SUMO independently enforces the follower's headway.
        following = ego is not None and v.lane==ego.lane and v.x<=ego.x-ego.length
        kind = 'rear_occupancy' if following else 'spatial_temporal'
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
                result.append(Constraint(kind, lower-v.length-margin,
                                         x+margin, lane, begin=now+future-.5*config['dt'],
                                         finish=now+future+.5*config['dt'], source=v.vehicle_id))
    return result
