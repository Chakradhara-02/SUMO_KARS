import math
import xml.etree.ElementTree as ET
from kars.city import build_city_network, city_route, CITY_POINTS
from kars.city_routing import CityRouter
from kars.city_safety import city_collision_risk
from kars.models import Vehicle


def test_every_source_road_is_a_straight_segment():
    network=build_city_network()
    root=ET.parse(network.parent/'metro.edges.xml').getroot()
    for edge in root:
        points=[[float(x) for x in p.split(',')] for p in edge.get('shape').split()]
        assert len(points)==2
        assert math.dist(points[0],points[1])>0
    assert any(e.get('disallow')=='truck' for e in root)


def test_every_named_destination_is_connected_to_every_other():
    for a in CITY_POINTS:
        for b in CITY_POINTS:
            if a['id']==b['id']:continue
            route=city_route(a['id'],b['id'])
            assert route['distance']>0 and route['edges']


def test_route_switch_score_matches_candidate_cost_and_journey_progress():
    router=CityRouter(build_city_network())
    candidates=router.alternatives('n0_0__n1_0','n4_4')
    for candidate in candidates:
        assert abs(router.score(candidate['edges'])-candidate['score'])<1e-7
    before=router.journey(candidates[0]['edges'],0)
    after=router.journey(candidates[0]['edges'],20)
    assert abs(before['remaining']-after['remaining']-20)<1e-7
    assert after['eta']<before['eta']
    assert after['instruction'] and after['junction_distance']>=0


def test_city_clearance_rotates_with_road_heading_and_separates_decks():
    ego=Vehicle('ego',0,0,0,'north_0',0,10,0,0,'north','','',14)
    lead=Vehicle('lead',0,0,20,'north_0',0,5,0,0,'north','','',14,length=5)
    assert city_collision_risk(ego,[ego,lead])==(15,3)
    lead.z=7
    assert city_collision_risk(ego,[lead])==(None,None)
