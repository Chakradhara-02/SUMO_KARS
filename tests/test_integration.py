from kars.simulation import run_simulation
from kars.models import ROOT
import pandas as pd

def test_sumo_closed_loop(tmp_path):
    metrics=run_simulation('static','kars',duration=4,output=tmp_path,make_plots=False)
    assert metrics['collision_events']==0
    assert metrics['average_speed']>0
    assert metrics['query_ms']>0
    for file in ['ego.csv','traffic.csv','dynamic.ttl','plans.json','metrics.json','manifest.json','trace.jsonl','tripinfo.xml']:
        assert (tmp_path/file).exists()
    traffic=pd.read_csv(tmp_path/'traffic.csv')
    ego=traffic[traffic.vehicle_id=='ego']
    assert ego.speed.iloc[0]>0
    assert ego.x.iloc[-1]>ego.x.iloc[0]
    assert ego.traffic_light.notna().any()
    assert 'obstacle_information' in traffic

def test_dashboard_loads():
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_file(str(ROOT/'dashboard.py')).run(timeout=20)
    assert not app.exception

def test_dynamic_braking_event(tmp_path):
    metrics=run_simulation('dynamic','kars',duration=23,output=tmp_path,make_plots=False)
    traffic=pd.read_csv(tmp_path/'traffic.csv')
    lead=traffic[(traffic.vehicle_id=='lead')&(traffic.timestamp>=17)&(traffic.timestamp<=21)]
    assert not lead.empty
    assert lead.speed.max()<.01
    assert (lead.lane==1).all()
    turning=traffic[(traffic.vehicle_id=='lead')&(traffic.timestamp>=12)&(traffic.timestamp<=16)]
    assert turning.y.nunique()>3 # continuous measured lane-change motion
    assert metrics['knowledge_reaction_time'] is not None
    assert 0<=metrics['knowledge_reaction_time']<1.5

def test_emergency_braking_and_resume(tmp_path):
    metrics=run_simulation('emergency','kars_delay',duration=21,output=tmp_path,make_plots=False)
    frame=pd.read_csv(tmp_path/'ego.csv')
    assert metrics['collision_events']==0
    assert metrics['rule_violations']==0
    assert metrics['emergency_entries']>0
    assert frame[(frame.timestamp>=16)&(frame.timestamp<18)].speed.max()<.01
    assert frame[frame.timestamp>=20].speed.max()>1
    traffic=pd.read_csv(tmp_path/'traffic.csv')
    barriers=traffic[traffic.vehicle_id.str.startswith('emergency_barrier_')]
    assert set(barriers.lane)=={0,1,2}
    assert barriers.speed.max()==0
    assert barriers.timestamp.max()<18
