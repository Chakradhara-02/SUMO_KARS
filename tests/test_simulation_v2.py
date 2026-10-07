import json
import threading
import time
import zipfile
import io
import pytest
from kars.models import State,Vehicle,load_config
from kars.reachable_set import propagate,online_rs,offline_rs,violates
from kars.models import Constraint
from kars.communication import Channel
from kars.knowledge import vehicle_constraints
from kars.control import collision_risk
from kars.console import RunManager,LocalServer,make_handler
from kars.simulation import atomic_json
from kars.storage import read_text_retry


def test_lane_change_reserves_both_lanes():
    config=load_config()
    first=propagate(State(0,8,1),0,2,config)
    assert first.lane_hold>0 and first.lane_origin==1
    assert propagate(first,0,1,config) is None
    assert violates(first,propagate(first,0,2,config),Constraint('spatial',9,18,1))
    third=propagate(propagate(first,0,2,config),0,2,config)
    assert third.lane_hold==0
    assert propagate(third,0,1,config) is not None


@pytest.mark.parametrize('speed',[0,4,8,12,16])
def test_rs_retains_all_reachable_lanes(speed):
    config=load_config()
    graph=online_rs(State(0,speed,1),offline_rs(config),config)
    assert {graph.nodes[n]['state'].lane for n in graph if graph.nodes[n]['layer']==config['horizon']}=={0,1,2}
    assert all(sum(graph.nodes[n]['layer']==layer for n in graph)<=config['max_states'] for layer in range(1,6))


def test_channel_reordering_and_outage():
    channel=Channel(.7,0,42,jitter=.7,outage=(3,4))
    latest=-1
    for step in range(100):
        now=step*.1
        packet=channel.transmit(now,{'time':now})
        if packet:
            assert packet['time']>=latest
            latest=packet['time']
    assert channel.out_of_order>0
    assert channel.dropped==10
    assert channel.sent==100
    assert channel.received+channel.dropped+len(channel.queue)==channel.sent


def test_sensing_real_dimensions_and_straddling():
    vehicle=Vehicle('truck',0,100,-4.0,'in_1',1,0,0,90,'in','','',16,
                    length=35,width=2.6,lateral_position=1.0)
    constraints=vehicle_constraints([vehicle],1,load_config(),True)
    assert {c.lane for c in constraints}=={1,2}
    assert constraints[0].start==55 # actual 35 m truck plus 10 m safety/age margin
    ego=Vehicle('ego',0,50,-4.,'in_1',1,10,0,90,'in','','',16)
    gap,ttc=collision_risk(ego,[ego,vehicle])
    assert gap==15 and ttc==1.5


@pytest.mark.parametrize('overrides',[{'horizon':2.5},{'simulation_dt':2},{'sensor_range':float('nan')},
                                     {'outage_begin':40,'outage_end':30},{'lane_change_duration':0}])
def test_reject_invalid_config(overrides):
    with pytest.raises(ValueError):load_config(overrides)


def test_atomic_snapshots_under_concurrent_reads(tmp_path):
    path=tmp_path/'live.json'
    atomic_json(path,{'time':0})
    errors=[]
    done=threading.Event()
    def reader():
        while not done.is_set():
            try:json.loads(read_text_retry(path))
            except Exception as error:errors.append(error)
    thread=threading.Thread(target=reader)
    thread.start()
    try:
        for i in range(100):atomic_json(path,{'time':i})
    finally:
        done.set();thread.join()
    assert not errors
    assert json.loads(path.read_text())['time']==99


def wait_for(predicate,timeout=20):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if predicate():return
        time.sleep(.05)
    raise AssertionError('Timed out waiting for simulation lifecycle')


def test_run_manager_pause_resume_replay_export(tmp_path):
    manager=RunManager(tmp_path)
    run_id=manager.start({'scenario':'static','duration':5,'realtime':1})['id']
    try:
        wait_for(lambda:manager.frame(run_id).get('time',0)>=.4)
        with pytest.raises(ValueError):manager.start({'duration':5})
        manager.command(run_id,'pause')
        wait_for(lambda:manager.describe(manager.folder(run_id))['status']['state']=='paused')
        paused=manager.frame(run_id)['time']
        time.sleep(.3)
        assert manager.frame(run_id)['time']==paused
        # A second server instance recovers the same running process from disk.
        recovered=RunManager(tmp_path)
        assert recovered.runs()[0]['alive']
        recovered.command(run_id,'run',5)
        wait_for(lambda:not manager.describe(manager.folder(run_id))['alive'])
        run=manager.runs()[0]
        assert run['status']['state']=='completed'
        assert run['manifest']['schema_version']==2
        replay=manager.frame(run_id,1.)
        assert replay['time']<=1 and replay['vehicles'] and replay['raw']
        assert max(r['timestamp'] for r in replay['history'])<=1.
        archive=zipfile.ZipFile(io.BytesIO(manager.archive(run_id)))
        assert {'ego.csv','traffic.csv','trace.jsonl','manifest.json','metrics.json','lane_changes.xml'}<=set(archive.namelist())
    finally:
        process=manager.processes[run_id]
        if process.poll() is None:
            manager.command(run_id,'stop');process.wait(timeout=15)


def test_reject_run_path_traversal(tmp_path):
    manager=RunManager(tmp_path)
    with pytest.raises(ValueError):manager.folder('../escape')
    with pytest.raises(ValueError):manager.start({'scenario':'invalid'})
    with pytest.raises(ValueError):manager.start({'duration':float('nan')})


def test_console_port_is_exclusive(tmp_path):
    handler=make_handler(RunManager(tmp_path))
    server=LocalServer(('127.0.0.1',0),handler)
    try:
        with pytest.raises(OSError):LocalServer(server.server_address,handler)
    finally:
        server.server_close()
