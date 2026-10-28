import math,json
import pytest
from kars.parking import parking_lot,choose_slot,parking_path,ParkingController
from kars.city import CITY_POINTS,city_route,build_city_network
from kars.simulation import run_simulation


def test_all_destinations_use_ground_level_connected_car_parks():
    import xml.etree.ElementTree as ET
    root=ET.parse(build_city_network()).getroot()
    assert any(p['name']=='City Mall' for p in CITY_POINTS)
    for place in CITY_POINTS:
        lot=parking_lot(place)
        assert lot['z']==0 and len([s for s in lot['slots'] if not s['occupied']])==5
        assert root.find("edge[@id='%s']"%lot['edge']) is not None
        assert root.find("edge[@id='arrival_%s__park_%s_turn']"%(place['id'],place['id'])) is not None
        trip=city_route('n4_0' if place['id']!='n4_0' else 'n0_0',place['id'])
        assert trip['arrival_bay']['z']==0


@pytest.mark.parametrize('slot_id',['A1','A3','A4','A6','A8'])
def test_controller_parks_inside_selected_slot_with_forward_reverse_and_bounded_motion(slot_id):
    lot=parking_lot(next(p for p in CITY_POINTS if p['id']=='city_mall'))
    controller=ParkingController(lot,slot_id);controller.start({'x':lot['x']+20,'y':lot['aisle_y'],'heading':90})
    poses=[]
    for _ in range(3000):
        pose=controller.step(.1);poses.append(dict(pose))
        if controller.done:break
    assert controller.done
    assert {'D','R','P'}<=set(p.get('gear','D') for p in poses)
    target=choose_slot(lot,slot_id);assert abs(poses[-1]['x']-target['front_x'])<.001
    assert abs(poses[-1]['y']-target['front_y'])<.001 and poses[-1]['heading']==180
    for a,b in zip(poses,poses[1:]):
        assert math.hypot(b['x']-a['x'],b['y']-a['y'])<.2
        assert abs((b['heading']-a['heading']+180)%360-180)<3
    # All planned turning states respect a passenger-car turning radius.
    reverse=[p for p in controller.path if p['stage']=='reversing']
    for a,b in zip(reverse,reverse[1:]):
        ds=math.hypot(b['x']-a['x'],b['y']-a['y']);angle=math.radians(abs(b['heading']-a['heading']))
        if angle>.001:assert ds/angle>4.5


def test_occupied_bays_are_rejected_and_manual_selection_waits():
    lot=parking_lot(next(p for p in CITY_POINTS if p['id']=='city_mall'))
    with pytest.raises(ValueError,match='occupied'):choose_slot(lot,'A2')
    controller=ParkingController(lot);start={'x':lot['x']+20,'y':lot['aisle_y'],'heading':90}
    controller.start(start)
    for _ in range(20):assert controller.step(.1)==start
    controller.select('A6');controller.step(.1)
    assert controller.stage=='positioning'
    with pytest.raises(ValueError,match='already'):controller.select('A3')


def test_native_selected_mall_slot_has_reverse_motion_and_exact_final_pose(tmp_path):
    metrics=run_simulation('city','city',duration=700,output=tmp_path,make_plots=False,
       config_overrides={'city_vehicles':20,'city_start':'n4_0','city_destination':'city_mall','city_parking_slot':'A4'})
    assert metrics['parked_at_destination'] and metrics['parking_slot']=='A4' and metrics['collision_events']==0
    frame=json.loads((tmp_path/'live.json').read_text());pose=frame['ego'];bay=metrics['arrival_bay']
    assert abs(pose['x']-bay['x'])<.05 and abs(pose['y']-bay['y'])<.05
    assert pose['heading']==180 and abs(pose['z'])<.01
    frames=[json.loads(line) for line in (tmp_path/'trace.jsonl').open()]
    red=[f['city']['next_signal'] for f in frames if f['city'].get('next_signal') and
         f['city']['next_signal']['color'].lower()=='r' and 0<=f['city']['next_signal']['distance']<=60]
    assert red and all(s['seconds'] is not None and s['seconds']<=15 for s in red)
    parking=[f for f in frames if f['city']['parking']['active']]
    assert any(f['ego']['speed']<-.1 for f in parking)
    assert any(f['ego']['speed']>.3 for f in parking)
    assert parking[-1]['city']['parking']['gear']=='P'


def test_parking_starts_at_observed_heading_without_an_entry_snap():
    lot=parking_lot(next(p for p in CITY_POINTS if p['id']=='city_mall'))
    start={'x':lot['x']+20,'y':lot['aisle_y'],'heading':86.8}
    path=parking_path(lot,choose_slot(lot,'A4'),start)
    assert abs(path[0]['x']-start['x'])<1e-8 and abs(path[0]['y']-start['y'])<1e-8
    assert path[0]['heading']==86.8
    assert max(abs(b['heading']-a['heading']) for a,b in zip(path,path[1:]))<2


def test_snapshot_exposes_remaining_path_and_preserves_final_target():
    lot=parking_lot(next(p for p in CITY_POINTS if p['id']=='city_mall'))
    controller=ParkingController(lot,'A4');controller.start({'x':lot['x']+20,'y':lot['aisle_y'],'heading':90})
    for _ in range(100):controller.step(.1)
    snapshot=controller.snapshot()
    assert snapshot['path_index']==controller.index
    assert snapshot['remaining_path']==controller.path[max(0,controller.index-15):controller.index+100:2]
    assert snapshot['path'][-1]==controller.path[-1]
