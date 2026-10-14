from rdflib import Literal, RDF

from kars.knowledge import K, KnowledgeGraph
from kars.models import Constraint, Vehicle


def test_network_boundaries_follow_sumo_lane_order():
    kg=KnowledgeGraph()
    assert (K.in_0,K.hasBoundary,K.in_0_right) in kg.static
    assert (K.in_2,K.hasBoundary,K.in_2_left) in kg.static
    assert float(kg.static.value(K.in_0_right,K.boundaryOffset))==-1.6
    assert float(kg.static.value(K.in_2_left,K.boundaryOffset))==1.6
    assert (K.in_1,K.hasLaneMarking,K.in_1_left) in kg.static


def test_semantic_features_keep_the_delivered_restrictions_and_query():
    kg=KnowledgeGraph()
    ego=Vehicle('ego',1,430,-4.8,'in_1',1,8,0,90,'in','center','r',16)
    other=Vehicle('other',1,440,-8,'in_0',0,6,0,90,'in','','',16)
    rules=[Constraint('marking',80,140,source='solid lane marking'),
           Constraint('spatial_speed',650,800,speed=8,source='speed-limit zone'),
           Constraint('spatial_speed',420,450,speed=5,source='crossing advisory')]
    kg.update([ego,other],rules,1)
    assert sorted(kg.constraints(),key=lambda c:c.source)==sorted(rules,key=lambda c:c.source)
    assert (K.feature_0,K.hasType,Literal('solid')) in kg.dynamic
    assert (K.in_1,K.hasLaneMarking,K.feature_0) in kg.dynamic
    assert (K.out_1,K.hasLaneMarking,K.feature_0) not in kg.dynamic
    assert (K.feature_1,K.hasSpeedLimitValue,Literal(8)) in kg.dynamic
    assert (K.feature_2,RDF.type,K.PedCrossing) in kg.dynamic
    assert (K.ego,K.within,K.geometry_2) in kg.dynamic
    assert (K.ego,K.within,K.geometry_1) not in kg.dynamic
    assert (K.other,K.isOn,K.in_0) in kg.dynamic
    assert (K['in'],K.has,K.other) in kg.dynamic
    evidence=kg.evidence()
    assert all(evidence[name] for name in evidence)
    assert any(t['predicate']=='hasType' and t['object']=='solid' for t in evidence['Lane markings'])
    assert {t['object'] for t in evidence['Planner constraints'] if t['predicate']=='source'}=={c.source for c in rules}
    kg.update([],[],2)
    assert not kg.evidence()['Planner constraints']
    assert not list(kg.dynamic.subjects(RDF.type,K.SpeedLimitSign))
