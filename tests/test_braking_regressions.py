import json
from kars.models import load_config, State, Constraint
from kars.reachable_set import propagate
from kars.planning import Planner
from kars.console import RunManager
from kars.models import Vehicle
from kars.knowledge import vehicle_constraints, KnowledgeGraph
from kars.reachable_set import violates


def test_fractional_speed_can_stop_without_reversing():
    config=load_config()
    for speed in (.2,.7,1.3,3.9):
        next_state=propagate(State(0,speed,1),-4,1,config)
        assert next_state.v==0
        assert next_state.x==speed*config['dt']/2


def test_safe_stop_before_block_is_not_no_path_emergency():
    config=load_config()
    for algorithm in ('kars','astar'):
        plan=Planner(config,algorithm).plan(State(0,.7,1),[
            Constraint('spatial',3,30,source='barrier')])
        assert not plan['emergency']
        assert any(data['layer']==config['horizon'] and data['state'].v==0
                   for _,data in plan['adjusted'].nodes(data=True))
        assert max(plan['trajectory']['x'])<3


def test_real_block_has_explicit_reason():
    plan=Planner(load_config()).plan(State(0,8,1),[
        Constraint('spatial',0,1000,source='physical barrier')])
    assert plan['emergency']
    assert 'physical barrier' in plan['emergency_reason']


def test_safe_prefix_is_controlled_stop_rather_than_emergency():
    for algorithm in ('kars','astar'):
        plan=Planner(load_config(),algorithm).plan(State(0,8,1),[
            Constraint('spatial_temporal',0,1000,begin=1.5,source='future closure')])
        assert plan['controlled_stop']
        assert not plan['emergency']
        assert len(plan['chain'])==2
        assert plan['trajectory']['velocity'][1]<8
        assert plan['diagnostics']['executed_horizon']==1


def test_rear_margin_does_not_block_forward_escape_but_guards_lane_change():
    config=load_config()
    ego=Vehicle('ego',0,30,-4.8,'in_1',1,0,0,90,'in','','',16)
    follower=Vehicle('follower',0,23,-4.8,'in_1',1,5,0,90,'in','','',16)
    constraints=vehicle_constraints([ego,follower],0,config,True,ego)
    assert all(c.kind=='rear_occupancy' for c in constraints)
    kg=KnowledgeGraph();kg.update([ego,follower],constraints,0)
    assert kg.constraints()==constraints
    guard=next(c for c in constraints if c.begin<=0<=c.finish)
    assert not violates(State(30,0,1),State(31,2,1,1),guard)
    assert violates(State(30,0,0),State(31,2,1,1,1.5,0),guard)
    assert not Planner(config).plan(State(30,0,1),constraints)['emergency']


def test_completed_run_does_not_resurrect_recycled_pid(tmp_path,monkeypatch):
    folder=tmp_path/'saved';folder.mkdir()
    (folder/'launch.json').write_text(json.dumps({'pid':123}))
    (folder/'status.json').write_text(json.dumps({'state':'completed'}))
    monkeypatch.setattr('kars.console.process_alive',lambda pid:True)
    assert not RunManager(tmp_path).describe(folder)['alive']
