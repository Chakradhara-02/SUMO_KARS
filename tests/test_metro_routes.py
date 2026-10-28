from types import SimpleNamespace
import xml.etree.ElementTree as ET

from kars.city import build_city_network
from kars.city_routing import CityRouter
from kars.city_reachability import CityReachability
from kars.models import Vehicle


def test_grade_separation_and_expressway_connectivity():
    root = ET.parse(build_city_network()).getroot()
    nodes = {j.get('id'): j for j in root.findall('junction')}
    assert float(nodes['n2_2'].get('z')) == 7
    under = root.find("edge[@id='under_w__under_e']/lane")
    assert all(len(p.split(',')) < 3 or float(p.split(',')[2]) == 0 for p in under.get('shape').split())
    ring = root.find("edge[@id='r0__r1']")
    assert len(ring.findall('lane')) == 3
    assert float(ring.find('lane').get('speed')) > 22
    router = CityRouter(build_city_network())
    routes = router.alternatives('n0_0__n1_0', 'n4_4')
    assert len(routes) == 3
    for route in routes:
        assert all(router.graph.has_edge(a, b) for a, b in zip(route['edges'], route['edges'][1:]))


def test_live_congestion_changes_selected_route_without_disconnecting_it():
    router = CityRouter(build_city_network())
    baseline = router.alternatives('n0_0__n1_0', 'n4_4')[0]
    blocked = baseline['edges'][3]
    edge = SimpleNamespace(getLastStepVehicleNumber=lambda e: 30 if e == blocked else 0,
                           getLastStepHaltingNumber=lambda e: 25 if e == blocked else 0,
                           getTraveltime=lambda e: 300 if e == blocked else 10)
    alternatives = router.alternatives('n0_0__n1_0', 'n4_4', SimpleNamespace(edge=edge))
    assert blocked not in alternatives[0]['edges']
    assert alternatives[0]['edges'][0] == baseline['edges'][0]
    assert router.edges[alternatives[0]['edges'][-1]].get('to') == 'arrival_n4_4'


def test_new_curved_network_forecasts_measured_pose_and_route_branches():
    model = CityReachability(build_city_network())
    route = CityRouter(build_city_network()).alternatives('n0_0__n1_0', 'n4_4')
    lane = 'n0_0__n1_0_0'
    points = model.lanes[lane]['shape']
    a, b = points[0], points[1]
    import math
    heading = math.degrees(math.atan2(b[0]-a[0], b[1]-a[1])) % 360
    ego = Vehicle('ego', 0, a[0], a[1], lane, 0, 6, 0, heading, 'n0_0__n1_0', '', '', 13.9)
    connection = SimpleNamespace(vehicle=SimpleNamespace(getRoute=lambda _: route[0]['edges'],
                                  getRouteIndex=lambda _: 0, getNextTLS=lambda _: []))
    for candidate in route:
        preview = model.forecast(connection, ego, [ego], 0, route_override=candidate['edges'])
        assert preview['feasible_count'] > 0
        assert preview['trajectory'][0]['x'] == ego.x
        assert preview['trajectory'][0]['y'] == ego.y
        assert all(math.isfinite(n['x']) and math.isfinite(n['y']) for n in preview['raw'])
