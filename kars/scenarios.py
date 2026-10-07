"""Scenario actors exist in SUMO and affect every vehicle, not only the planner."""
import xml.etree.ElementTree as ET
import math
from .models import ROOT

SCENARIO_INFO = {
    'static': ('Road rules', 'Signalized intersection, crossing traffic and speed zones.'),
    'semi_dynamic': ('Roadworks', 'A parked maintenance truck and a temporary lane obstruction.'),
    'dynamic': ('Braking traffic', 'A lead car merges, brakes, waits and rejoins traffic.'),
    'emergency': ('Emergency recovery', 'Three physical barriers stop traffic, then clear.'),
    'iot_delay': ('Communication stress', 'Roadworks and braking with delayed, lossy roadside messages.'),
    'demo': ('Combined traffic', 'Roadworks, changing restrictions, braking and a signalized junction.'),
}


def prepare_routes(output, scenario, density):
    tree = ET.parse(ROOT / 'sumo/routes/traffic.rou.xml')
    root = tree.getroot()
    root.find("flow[@id='traffic']").set('period', str(density))
    # Obstructions use stopped vehicles with their actual physical length.
    root.insert(1, ET.Element('vType', id='barrier', accel='1', decel='4',
                             length='5', width='2.6', maxSpeed='1', guiShape='truck',
                             color='1,0.48,0.12', sigma='0'))
    actors = []
    if scenario in ('semi_dynamic', 'demo', 'iot_delay'):
        for name, front, lane, length, depart, until in [
            ('work_truck', 315, 0, 35, 0, 100000),
            ('temporary_barrier', 390, 1, 30, 10, 80),
        ]:
            # Each distinct type carries the dimensions used by TraCI sensing.
            type_id = name + '_type'
            root.insert(2, ET.Element('vType', id=type_id, accel='1', decel='4',
                                     length=str(length), width='2.6', maxSpeed='1',
                                     guiShape='truck', color='1,0.48,0.12', sigma='0'))
            vehicle = ET.Element('vehicle', id=name, type=type_id, route='main',
                                 depart=str(depart), departLane=str(lane),
                                 departPos=str(front), departSpeed='0')
            ET.SubElement(vehicle, 'stop', lane=f'in_{lane}', endPos=str(front),
                          until=str(until), duration='100000')
            actors.append(vehicle)
    # SUMO requires vehicles and flows sorted by departure time.
    moving = [n for n in list(root) if n.tag in ('vehicle', 'flow')]
    for node in moving:
        root.remove(node)
    for node in sorted(moving + actors, key=lambda n: float(n.get('depart', n.get('begin', '0')))):
        root.append(node)
    path = output / 'traffic.rou.xml'
    tree.write(path, encoding='utf-8', xml_declaration=True)
    return path


def prepare_additional(output):
    root=ET.parse(ROOT/'sumo/additional/zones.add.xml').getroot()
    # Construction is now a physical truck, rather than an always-visible patch.
    for poly in list(root):
        if poly.get('id')=='construction':
            root.remove(poly)
    for index,x in enumerate(range(35,980,35)):
        if abs(x-500)<35:
            continue
        for side,y in [('north',25),('south',-45)]:
            ET.SubElement(root,'poly',id=f'building_{index}_{side}',type='building',
                          color='0.82,0.87,0.80',fill='true',layer='-2',
                          shape=f'{x},{y} {x+25},{y} {x+25},{y+16} {x},{y+16}')
            for tree in range(3):
                tx=x+tree*9+4
                ty=16 if side=='north' else -20
                points=' '.join(f'{tx+2*math.cos(a):.2f},{ty+2*math.sin(a):.2f}'
                                for a in [i*math.pi/4 for i in range(8)])
                ET.SubElement(root,'poly',id=f'tree_{index}_{side}_{tree}',type='park',
                              color='0.62,0.75,0.55',fill='true',layer='-2',shape=points)
    path=output/'environment.add.xml'
    ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)
    return path


class ScenarioWorld:
    def __init__(self, scenario, config, events):
        self.scenario, self.config, self.events = scenario, config, events
        self.timeline = []

    def log(self, now, kind, message, **details):
        self.timeline.append(dict(time=now, kind=kind, message=message, **details))

    def step(self, connection, now, ego):
        ids = set(connection.vehicle.getIDList())
        for actor in ('work_truck', 'temporary_barrier'):
            if actor in ids and actor not in self.events:
                connection.vehicle.setLaneChangeMode(actor, 512)
                connection.vehicle.setSpeed(actor, 0)
                self.events[actor] = now
                self.log(now, 'obstruction', actor.replace('_', ' ') + ' active', actor=actor)
        if now >= 80 and 'temporary_barrier' in ids:
            connection.vehicle.remove('temporary_barrier')
            self.log(now, 'clearance', 'Temporary lane obstruction removed')
        if self.scenario in ('dynamic', 'demo', 'iot_delay') and now >= 12 and 'braked' not in self.events:
            if 'lead' in ids:
                connection.vehicle.setLaneChangeMode('lead', 512)
                connection.vehicle.changeLane('lead', 1, 10.)
                connection.vehicle.slowDown('lead', 0., 4.)
                self.events['braked'] = now
                self.log(now, 'braking', 'Lead car merges into lane 1 and brakes')
        if 'braked' in self.events and now >= 16 and 'held' not in self.events and 'lead' in ids:
            connection.vehicle.setSpeed('lead', 0.)
            self.events['held'] = now
            self.log(now, 'stopped', 'Lead car holding position')
        if 'braked' in self.events and now >= 22 and 'released' not in self.events and 'lead' in ids:
            connection.vehicle.setSpeed('lead', -1)
            self.events['released'] = now
            self.log(now, 'recovery', 'Lead car rejoins traffic')
        if self.scenario == 'demo' and now >= 18 and 'speed_update' not in self.events:
            self.events['speed_update'] = now
            self.log(now, 'restriction', 'Upcoming 300–400 m zone changes to 7 m/s')
        if self.scenario == 'emergency' and now >= 8 and 'emergency_x' not in self.events:
            front = ego.x + ego.speed ** 2 / (2 * abs(self.config['min_acceleration'])) + self.config['safety_gap'] + 9
            self.events['emergency_x'] = front - 5
            for lane in range(self.config['lanes']):
                actor = f'emergency_barrier_{lane}'
                connection.vehicle.add(actor, 'main', typeID='barrier', depart='now',
                                       departLane=str(lane), departPos=str(front), departSpeed='0')
                connection.vehicle.setLaneChangeMode(actor, 512)
                connection.vehicle.setStop(actor, 'in', pos=front, laneIndex=lane, duration=100000.)
                connection.vehicle.setSpeed(actor, 0.)
            self.log(now, 'emergency', 'Physical barriers deployed across all three lanes', x=front)
        if self.scenario == 'emergency' and now >= 18 and 'barriers_cleared' not in self.events:
            for actor in ids:
                if actor.startswith('emergency_barrier_'):
                    connection.vehicle.remove(actor)
            self.events['barriers_cleared'] = now
            self.log(now, 'recovery', 'All emergency barriers removed; route reopened')


def signal_constraints(connection, ego, now, horizon):
    """Use the actual static signal phase schedule, scoped to ego's movement."""
    from .models import Constraint
    next_tls = connection.vehicle.getNextTLS('ego')
    if not next_tls:
        return []
    tls_id, link, distance, color = next_tls[0]
    if distance < 0:
        return []
    stop = ego.x + distance - 3
    logic = next((p for p in connection.trafficlight.getAllProgramLogics(tls_id)
                  if p.programID == connection.trafficlight.getProgram(tls_id)), None)
    if logic is None or logic.type != 0:
        return [Constraint('spatial_temporal_speed', stop, stop+30, speed=0,
                           begin=now, finish=now+horizon, source='traffic light '+color)] if color.lower() in ('r', 'y') else []
    phase = connection.trafficlight.getPhase(tls_id)
    begin, end = now, connection.trafficlight.getNextSwitch(tls_id)
    result = []
    while begin <= now + horizon:
        state = logic.phases[phase].state[link]
        if state.lower() in ('r', 'y'):
            result.append(Constraint('spatial_temporal_speed', stop, stop+30, speed=0,
                                     begin=begin, finish=end, source=f'traffic light {tls_id} link {link} {state}'))
        begin = end
        phase = (phase + 1) % len(logic.phases)
        end = begin + logic.phases[phase].duration
    return result
