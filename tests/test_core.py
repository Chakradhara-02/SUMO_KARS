import pytest
import networkx as nx
from kars.models import State,Constraint,load_config
from kars.reachable_set import offline_rs,online_rs,propagate,rs_adjustment,violates
from kars.knowledge import KnowledgeGraph
from kars.planning import Planner,corridors,dynamic_programming,astar,optimize_trajectory,emergency
from kars.communication import Channel

@pytest.fixture
def config(): return load_config()

def test_vehicle_dynamics(config):
    state=propagate(State(0,8,1),2,1,config)
    assert state==State(9,10,1,1)
    assert propagate(State(0,0,1),-2,1,config) is None
    assert propagate(State(0,8,1),0,3,config) is None

def test_offline_online(config):
    offline=offline_rs(config)
    assert offline['transitions']
    graph=online_rs(State(0,8,1),offline,config)
    assert nx.is_directed_acyclic_graph(graph)
    assert max(graph.nodes[n]['layer'] for n in graph)==config['horizon']
    for u,v,data in graph.edges(data=True):
        assert propagate(graph.nodes[u]['state'],data['acceleration'],graph.nodes[v]['state'].lane,config)==graph.nodes[v]['state']

@pytest.mark.parametrize('kind,speed,begin,finish,expected',[
    ('spatial',0,0,10,True),('spatial_speed',5,0,10,True),
    ('spatial_speed',12,0,10,False),('spatial_temporal',0,0,2,True),
    ('spatial_temporal',0,3,5,False),('spatial_temporal_speed',5,0,2,True),
    ('spatial_temporal_speed',12,0,2,False)])
def test_four_constraint_types(kind,speed,begin,finish,expected):
    assert violates(State(0,8,1,0),State(10,10,1,1),Constraint(kind,4,6,1,speed,begin,finish))==expected

def test_marking_and_lane_specific():
    assert violates(State(0,8,1),State(10,8,2,1),Constraint('marking',4,6))
    assert not violates(State(0,8,1),State(10,8,1,1),Constraint('spatial',4,6,0))

def test_sparql():
    kg=KnowledgeGraph()
    original=Constraint('spatial_speed',0,100,speed=7,source='limit')
    kg.update([], [original],0)
    assert kg.constraints()==[original]
    kg.update([],[],1)
    assert kg.constraints()==[]

def test_all_example_queries_parse():
    from kars.models import ROOT,Vehicle
    kg=KnowledgeGraph()
    ego=Vehicle('ego',1,10,0,'in_1',1,8,0,90,'in','center','r',16)
    kg.update([ego],[Constraint('spatial_speed',0,100,speed=7,source='crossing advisory')],1)
    for query in (ROOT/'knowledge_graph/queries').glob('*.rq'):
        list(kg.dynamic.query(query.read_text()))

def test_pruning_disconnects(config):
    raw=online_rs(State(0,8,1),offline_rs(config),config)
    adjusted,_=rs_adjustment(raw,[Constraint('spatial',0,1000)])
    assert list(adjusted)==[0]

def test_corridors_dp_astar(config):
    graph=online_rs(State(0,8,1),offline_rs(config),config)
    assert len(corridors(graph,config['horizon']))==3
    dp,cost=dynamic_programming(graph,config)
    path,astar_cost=astar(graph,config)
    assert cost==pytest.approx(astar_cost)
    assert len(dp)==len(path)==config['horizon']+1
    assert all(graph.has_edge(a,b) for a,b in zip(dp,dp[1:]))

def test_trajectory(config):
    states=[State(8*i,8,1,float(i)) for i in range(6)]
    trajectory=optimize_trajectory(states,[],config)
    assert len(trajectory['x'])==6
    assert all(0<=v<=config['max_speed'] for v in trajectory['velocity'])
    for i in range(1,6):
        assert trajectory['x'][i]-trajectory['x'][i-1]==pytest.approx(
            .5*(trajectory['velocity'][i]+trajectory['velocity'][i-1])*config['dt'])

def test_emergency_recovery(config):
    planner=Planner(config)
    assert planner.plan(State(0,8,1),[Constraint('spatial',0,1000)])['emergency']
    assert not planner.plan(State(0,8,1),[])['emergency']
    assert emergency(State(0,8,1),config)<8

def test_channel_delay_loss():
    channel=Channel(1,0,1)
    assert channel.transmit(0,{'time':0}) is None
    assert channel.transmit(1,{'time':1})=={'time':0}
    assert Channel(0,1).transmit(0,{'time':0}) is None
