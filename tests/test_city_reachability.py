from types import SimpleNamespace

from kars.city import build_city_network
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
    assert all(0<=p['speed']<=13.9 for p in preview['raw'])
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
