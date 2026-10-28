from types import SimpleNamespace

from kars.models import ROOT

# Fixed grid fixture for tests that assert exact historical coordinates.
def build_city_network():
    return ROOT/'sumo/network/city/indian_city.net.xml'
from kars.city_reachability import CityReachability
from kars.models import Vehicle


def connection(red=False):
    phase=SimpleNamespace(state='r',duration=100)
    logic=SimpleNamespace(programID='0',type=0,phases=[phase])
    return SimpleNamespace(vehicle=SimpleNamespace(
        getRoute=lambda _:['n0_0__n1_0','n1_0__n2_0'],getRouteIndex=lambda _:0,
        getNextTLS=lambda _:[('chowk',0,20,'r')] if red else []),
        trafficlight=SimpleNamespace(getAllProgramLogics=lambda _:[logic],getProgram=lambda _:'0',
                                     getPhase=lambda _:0,getNextSwitch=lambda _:100))


def ego(speed=8):
    return Vehicle('ego',0,15,4.8,'n0_0__n1_0_0',0,speed,0,90,'n0_0__n1_0','','',13.9)


def test_reachable_samples_follow_left_hand_streets_and_branch_dynamics():
    model=CityReachability(build_city_network());e=ego()
    preview=model.forecast(connection(),e,[e],0)
    assert preview['raw_count']>0 and preview['feasible_count']>0
    assert all(0<=p['y']<=6.4 for p in preview['raw'])
    assert all(0<=p['speed']<=13.9 for p in preview['feasible'])
    trajectory=preview['trajectory']
    assert trajectory[0]['x']==e.x and trajectory[0]['y']==e.y
    assert trajectory[-1]['x']>trajectory[0]['x']
    assert preview['executed_by']=='SUMO'


def test_red_light_removes_states_crossing_the_stop_line():
    model=CityReachability(build_city_network());e=ego()
    preview=model.forecast(connection(True),e,[e],0)
    assert preview['feasible_count']<preview['raw_count']
    assert all(p['distance']<=17+1e-6 for p in preview['feasible'])
    stopped=ego(0);stopped.y=4.2;con=connection(True);con.vehicle.getNextTLS=lambda _:[('chowk',0,2,'r')]
    waiting=model.forecast(con,stopped,[stopped],0)
    assert all(p['distance']==0 for p in waiting['feasible'])
    assert all(abs(p['y']-stopped.y)<1e-9 for p in waiting['feasible'])


def test_observed_obstacle_prunes_swept_future_motion():
    model=CityReachability(build_city_network());e=ego()
    blocker=Vehicle('stopped_bus',0,40,4.8,e.lane_id,0,0,0,90,e.road_id,'','',13.9,length=11)
    preview=model.forecast(connection(),e,[e,blocker],0)
    assert preview['feasible_count']<preview['raw_count']
    assert all(not (29<p['x']<45 and abs(p['y']-4.8)<1.5) for p in preview['feasible'])


def test_preview_turn_uses_internal_junction_lane_geometry():
    model=CityReachability(build_city_network());e=ego(5);e.x=165
    con=connection();con.vehicle.getRoute=lambda _:['n0_0__n1_0','n1_0__n1_1']
    preview=model.forecast(con,e,[e],0)
    turning=[p for p in preview['feasible'] if p['y']>10]
    assert turning
    assert all(170<p['x']<180 for p in turning)
    assert any(p['lane_id'].startswith(':') for p in preview['raw'])


def test_preview_preserves_the_observed_lane_change_direction():
    model=CityReachability(build_city_network());e=ego(6)
    e.y=4.2;e.heading=94;e.lateral_position=.6
    preview=model.forecast(connection(),e,[e],0)
    assert preview['trajectory'][-1]['y']<e.y


def test_every_rejected_sample_has_an_explanation_and_safe_ancestors():
    model=CityReachability(build_city_network());e=ego()
    preview=model.forecast(connection(True),e,[e],0)
    assert not preview['unsafe']
    assert preview['restricted']
    assert all(p['reasons'] and not p['valid'] for p in preview['restricted'])
    assert all(p['valid'] and not p['reasons'] for p in preview['feasible'])
    assert any('signal' in reason for p in preview['restricted'] for reason in p['reasons'])


def test_comfort_objective_avoids_unnecessary_acceleration_switches():
    model=CityReachability(build_city_network());e=ego(8)
    preview=model.forecast(connection(),e,[e],0)
    path=preview['trajectory']
    speeds=[next(p['speed'] for p in path if abs(p['time']-t)<1e-8) for t in range(6)]
    acceleration=[b-a for a,b in zip(speeds,speeds[1:])]
    assert all(abs(a)<=4 for a in acceleration)
    assert not any(a*b<0 for a,b in zip(acceleration,acceleration[1:]))
    assert preview['optimization']['selected_cost'] is not None


def test_red_points_require_a_nearby_vehicle_conflict_not_a_rule_rejection():
    model=CityReachability(build_city_network());e=ego()
    clear=model.forecast(connection(),e,[e],0)
    assert not clear['unsafe']
    assert not model.forecast(connection(True),e,[e],0)['unsafe']
    blocker=Vehicle('bus',0,40,4.8,e.lane_id,0,0,0,90,e.road_id,'','',13.9,length=11)
    blocked=model.forecast(connection(),e,[e,blocker],0)
    assert blocked['unsafe']
    assert all(n['blocked_by']==['bus'] and n['hazard_point']['x']<=n['x'] for n in blocked['unsafe'])
    assert not model.forecast(connection(),e,[e,blocker],0,sensor_range=10)['unsafe']
    blocker.z=7
    assert not model.forecast(connection(),e,[e,blocker],0)['unsafe']


def test_an_off_path_vehicle_does_not_turn_clear_motion_red():
    model=CityReachability(build_city_network());e=ego()
    other=Vehicle('other_road',0,35,35,e.lane_id,0,0,0,90,e.road_id,'','',13.9)
    assert not model.forecast(connection(),e,[e,other],0)['unsafe']
