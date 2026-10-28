import json
import xml.etree.ElementTree as ET
import time
import io
import zipfile

import pandas as pd
import pytest

from kars.city import build_city_network, city_route
from kars.simulation import run_simulation
from kars.console import RunManager


def test_city_network_and_selected_route():
    root=ET.parse(build_city_network()).getroot()
    assert root.get('lefthand')=='true'
    streets=[e for e in root.findall('edge') if not e.get('id').startswith(':')]
    assert len(streets)>100
    assert {len(e.findall('lane')) for e in streets}=={1,2,3}
    assert len(root.findall('tlLogic'))==25
    edges={e.get('id'):e for e in streets}
    route=city_route('n0_0','n4_4')
    assert edges[route['edges'][0]].get('from')=='n0_0'
    assert edges[route['edges'][-1]].get('to')=='arrival_n4_4'
    connections={(c.get('from'),c.get('to')) for c in root.findall('connection')}
    assert all(pair in connections for pair in zip(route['edges'],route['edges'][1:]))
    assert route['distance']>1000
    with pytest.raises(ValueError):city_route('n0_0','n0_0')
    with pytest.raises(ValueError):city_route('unknown','n4_4')


def test_dense_city_traffic_records_real_motion_and_route(tmp_path):
    metrics=run_simulation('city','city',duration=4,output=tmp_path,make_plots=False,
                           config_overrides={'city_vehicles':180})
    assert metrics['peak_vehicles']>=150
    assert metrics['collision_events']==0
    frame=json.loads((tmp_path/'live.json').read_text())
    assert frame['city']['trip']['start']['id']=='n0_0'
    assert frame['city']['trip']['destination']['id']=='n4_4'
    assert len(frame['signals'])==25
    assert frame['city']['routing_engine']=='Traffic-aware alternative routes'
    assert frame['city_reachability']['raw_count']>0
    assert frame['ego_trace']
    assert len(frame['ego_trace'][-1])==3
    assert frame['ego_trace'][-1][2]==frame['ego']['z']
    manifest=json.loads((tmp_path/'manifest.json').read_text())
    assert manifest['lane_change_model']=='SL2015'
    types=ET.parse(tmp_path/'traffic.rou.xml').getroot().findall('vType')
    assert all(t.get('lcMaxSpeedLatStanding')=='0' for t in types)
    ego=pd.read_csv(tmp_path/'ego.csv')
    assert ego.distance.iloc[-1]>ego.distance.iloc[0]
    traffic=pd.read_csv(tmp_path/'traffic.csv')
    assert traffic.road_id.nunique()>30


def test_city_ego_arrives_at_selected_destination(tmp_path):
    metrics=run_simulation('city','city',duration=600,output=tmp_path,make_plots=False,
                           config_overrides={'city_vehicles':20,'city_start':'n0_0','city_destination':'n2_0'})
    assert metrics['arrived']==1 and metrics['parked_at_destination']
    assert metrics['end_reason']=='arrived'
    frame=json.loads((tmp_path/'live.json').read_text());bay=frame['city']['arrival_bay'];ego=frame['ego']
    assert frame['city']['parked'] and ego['speed']<.01
    assert abs(ego['x']-bay['x'])<.5 and abs(ego['y']-bay['y'])<.5
    assert abs((ego['heading']-bay['heading']+180)%360-180)<1
    assert frame['city']['parking']['complete']


def test_city_pause_resume_stop_replay_and_export(tmp_path):
    manager=RunManager(tmp_path)
    run_id=manager.start({'scenario':'city','duration':20,'realtime':1,'city_vehicles':60,
                          'city_start':'n0_0','city_destination':'n2_2'})['id']
    def wait_for(predicate):
        deadline=time.monotonic()+25
        while time.monotonic()<deadline:
            if predicate():return
            time.sleep(.05)
        raise AssertionError(manager.describe(manager.folder(run_id)))
    try:
        wait_for(lambda:manager.frame(run_id).get('time',0)>=.4)
        manager.command(run_id,'pause')
        wait_for(lambda:manager.describe(manager.folder(run_id))['status']['state']=='paused')
        paused=manager.frame(run_id)['time'];time.sleep(.3)
        assert manager.frame(run_id)['time']==paused
        manager.command(run_id,'run',5)
        wait_for(lambda:manager.frame(run_id).get('time',0)>paused)
        manager.command(run_id,'stop')
        wait_for(lambda:not manager.describe(manager.folder(run_id))['alive'])
        result=manager.describe(manager.folder(run_id))
        assert result['status']['state']=='cancelled'
        assert result['manifest']['algorithm']=='city'
        replay=manager.frame(run_id,.4)
        assert replay['city']['trip']['destination']['id']=='n2_2'
        assert replay['vehicles']
        archive=zipfile.ZipFile(io.BytesIO(manager.archive(run_id)))
        assert {'ego.csv','traffic.csv','trace.jsonl','manifest.json','tripinfo.xml'}<=set(archive.namelist())
    finally:
        process=manager.processes[run_id]
        if process.poll() is None:
            manager.command(run_id,'stop');process.wait(timeout=15)
