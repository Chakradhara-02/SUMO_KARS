import json
import pytest
from kars.models import State, Vehicle, Constraint, load_config
from kars.planning import Planner
from kars.simulation import snapshot_json
from kars.control import TrajectoryTracker
from kars.reachable_set import propagate, violates


def test_replanning_preserves_committed_lane_occupancy():
    config=load_config()
    tracker=TrajectoryTracker(config)
    tracker.lane_target,tracker.lane_origin,tracker.lane_started=2,1,0
    ego=Vehicle('ego',1,20,-4.3,'in_1',1,8,0,90,'in','','',16,lateral_position=.5)
    state=tracker.planning_state(ego,1)
    assert (state.lane,state.lane_origin,state.lane_hold)==(2,1,1.5)
    nxt=propagate(state,0,2,config)
    assert violates(state,nxt,Constraint('spatial',22,25,lane=1))
    assert violates(state,nxt,Constraint('spatial',22,25,lane=2))
    assert propagate(state,0,1,config) is None
    # Measured completion releases the source lane reservation.
    ego.lane=2;ego.lateral_position=0
    assert tracker.planning_state(ego,2).lane_origin==-1


@pytest.mark.parametrize('algorithm',['kars','kars_delay','astar','rs'])
def test_diagnostics_survive_serialization_and_reflect_constraint_coverage(algorithm):
    plan=Planner(load_config(),algorithm).plan(State(0,8,1,3),[
        Constraint('spatial',25,40,lane=0,source='workzone'),
        Constraint('spatial_speed',0,100,speed=12,source='limit')])
    frame=json.loads(json.dumps(snapshot_json(plan),allow_nan=False))
    d=frame['diagnostics']
    assert d['plan_time']==frame['plan_time']==3
    assert d['raw_nodes']==len(frame['raw'])
    assert d['feasible_edges']==len(frame['edges'])
    assert sum(layer['raw'] for layer in d['layers'])==d['raw_nodes']
    assert d['constraints_used']==(1 if algorithm=='rs' else 2)
    assert set(d['timings_ms'])=={'generation','adjustment','corridors','search','optimization'}
    assert all(value>=0 for value in d['timings_ms'].values())
    assert d['solver']==('A*' if algorithm=='astar' else 'Dynamic programming')


def test_blocked_plan_diagnostics_have_no_infinite_costs():
    plan=Planner(load_config()).plan(State(0,8,1),[Constraint('spatial',0,1000,source='block')])
    frame=json.loads(json.dumps(snapshot_json(plan),allow_nan=False))
    assert frame['emergency']
    assert frame['diagnostics']['selected_cost'] is None
    assert frame['diagnostics']['optimization_status']=='no feasible path'
    assert frame['diagnostics']['rejection_reasons']['block']>0
