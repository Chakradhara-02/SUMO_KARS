from types import SimpleNamespace
import xml.etree.ElementTree as ET
from kars.city import build_city_network,city_route
from kars.city_infrastructure import phase_countdowns,indicator_intent,road_lateral_speed,city_motion_context
from kars.city_reachability import CityReachability
from kars.models import Vehicle


def test_every_city_junction_has_complete_green_amber_all_red_cycle():
    root=ET.parse(build_city_network()).getroot();logics=root.findall('tlLogic')
    assert len(logics)==25
    for logic in logics:
        phases=logic.findall('phase')
        for i in range(0,len(phases),3):
            green,amber,clear=phases[i:i+3]
            assert float(green.get('duration'))==15 and 'g' in green.get('state').lower()
            assert float(amber.get('duration'))==3
            assert float(clear.get('duration'))==6 and set(clear.get('state'))=={'r'}
            assert all(b=='y' for a,b in zip(green.get('state'),amber.get('state')) if a.lower()=='g')


def test_red_countdown_includes_amber_and_clearance_until_green():
    phases=[SimpleNamespace(state='Gr',duration=25),SimpleNamespace(state='yr',duration=3),
            SimpleNamespace(state='rr',duration=2),SimpleNamespace(state='rG',duration=25),
            SimpleNamespace(state='ry',duration=3),SimpleNamespace(state='rr',duration=2)]
    assert phase_countdowns(phases,0,7)==[7,12]
    assert phase_countdowns(phases,2,2)==[32,2]


def test_straight_route_cancels_spurious_left_but_keeps_actual_lane_change():
    signals,reason=indicator_intent(2,'s',15,0)
    assert signals&3==0 and reason=='Continuing straight'
    signals,reason=indicator_intent(2,'s',15,.3)
    assert signals&2 and reason=='Changing lane left'
    assert indicator_intent(2,'r',20,0)[0]&3==1
    assert indicator_intent(0,'s',99,0,parking=True)[0]&2
    assert indicator_intent(2,'s',0,0,parked=True)[0]&3==0


def test_arrival_has_a_dedicated_driveway_and_off_road_parking_area():
    trip=city_route('n0_0','n4_4');bay=trip['arrival_bay']
    assert trip['edges'][-1]==trip['parking_lot']['edge']
    assert trip['destination']['x']==bay['x'] and trip['destination']['y']==bay['y']
    root=ET.parse(build_city_network()).getroot()
    lane=root.find(f"edge[@id='{bay['edge']}']/lane")
    assert float(lane.get('speed'))<5
    assert bay['z']==0 and trip['parking_lot']['z']==0


def test_safe_stationary_queue_retains_green_waiting_samples():
    model=CityReachability(build_city_network());lane='n0_0__n1_0_0'
    points=model.lanes[lane]['shape'];a,b=points[0],points[1]
    import math
    dx,dy=b[0]-a[0],b[1]-a[1];distance=math.hypot(dx,dy);dx/=distance;dy/=distance
    ego=Vehicle('ego',0,a[0]+dx*12,a[1]+dy*12,lane,0,0,0,math.degrees(math.atan2(dx,dy))%360,'n0_0__n1_0','','',13.9)
    lead=Vehicle('lead',0,ego.x+dx*7.5,ego.y+dy*7.5,lane,0,0,0,ego.heading,ego.road_id,'','',13.9,length=5)
    connection=SimpleNamespace(vehicle=SimpleNamespace(getRoute=lambda _:['n0_0__n1_0','n1_0__n2_0'],getRouteIndex=lambda _:0,getNextTLS=lambda _:[]))
    result=model.forecast(connection,ego,[ego,lead],0)
    assert result['feasible_count']>0
    assert any(n['layer']==5 and n['speed']==0 for n in result['feasible'])
    assert len(result['reference_path'])>1


def test_lane_indicator_uses_physical_motion_even_if_native_bit_disagrees():
    assert indicator_intent(1,'s',100,.3)[0]&3==2
    assert indicator_intent(2,'s',100,-.3)[0]&3==1
    for shape,previous,current,left in [
        ([[0,0],[100,0]],{'x':10,'y':0,'timestamp':1,'road_id':'road'},SimpleNamespace(x=11,y=.03,timestamp=1.1,road_id='road'),True),
        ([[0,0],[0,100]],{'x':0,'y':10,'timestamp':1,'road_id':'road'},SimpleNamespace(x=.03,y=11,timestamp=1.1,road_id='road'),False),
        ([[0,0],[-100,0]],{'x':-10,'y':0,'timestamp':1,'road_id':'road'},SimpleNamespace(x=-11,y=-.03,timestamp=1.1,road_id='road'),True)]:
        speed=road_lateral_speed(previous,current,shape)
        assert (speed>0)==left
        assert indicator_intent(1 if left else 2,'s',100,speed)[0]&3==(2 if left else 1)


def test_green_approaches_are_exclusive_and_have_no_foe_connections():
    root=ET.parse(build_city_network()).getroot()
    for logic in root.findall('tlLogic'):
        links={int(c.get('linkIndex')):c for c in root.findall('connection') if c.get('tl')==logic.get('id')}
        requests={int(r.get('index')):r.get('foes')[::-1] for r in root.find("junction[@id='%s']"%logic.get('id')).findall('request')}
        served=set()
        for phase in logic.findall('phase'):
            green={i for i,c in enumerate(phase.get('state')) if c=='G'}
            if not green:continue
            assert len({links[i].get('from') for i in green})==1
            for i in green:
                served.add(i)
                assert all(requests[i][j]!='1' for j in green if j!=i)
        assert served==set(links)


def test_ground_approaches_leave_the_descending_flyover_alignment():
    root=ET.parse(build_city_network()).getroot()
    assert root.find("edge[@id='under_e__n4_2']") is None
    assert root.find("edge[@id='n0_2__under_w']") is None
    east=root.find("edge[@id='under_entry_e__n4_2']/lane")
    points=[[float(v) for v in p.split(',')] for p in east.get('shape').split()]
    assert min(p[1] for p in points)<380
    # At the old overlap location x=820, the ground approach is horizontally separated.
    a,b=points[0],points[-1];t=(820-a[0])/(b[0]-a[0]);y=a[1]+t*(b[1]-a[1])
    assert abs(y-404.8)>8


def test_waiting_context_explains_green_without_overriding_safety():
    ego=SimpleNamespace(speed=0)
    signal={'color':'G','distance':2}
    assert city_motion_context(ego,False,signal,('lead',0))['state']=='queue'
    blocked=[('lane','via',True,False,True,'G','r',20)]
    assert city_motion_context(ego,False,signal,None,blocked)['state']=='junction_clearance'
    assert city_motion_context(ego,False,signal)['state']=='starting'
    assert city_motion_context(ego,True,signal)['state']=='parked'


def test_priority_releases_red_within_15_seconds_and_preserves_clearance():
    from kars.city_infrastructure import EgoSignalPriority
    from traci import trafficlight
    base=trafficlight.Logic('0',0,0,[trafficlight.Phase(d,state) for d,state in
        [(15,'Gr'),(3,'yr'),(6,'rr'),(15,'rG'),(3,'ry'),(6,'rr')]])
    programs={'0':base};active=['0'];phase=[0]
    def install(tid,logic):programs[logic.programID]=logic
    tls=SimpleNamespace(getAllProgramLogics=lambda tid:list(programs.values()),getProgram=lambda tid:active[0],
        getRedYellowGreenState=lambda tid:'Gr',getNextSwitch=lambda tid:15,
        setProgramLogic=install,setProgram=lambda tid,value:active.__setitem__(0,value),
        setPhase=lambda tid,value:phase.__setitem__(0,value))
    con=SimpleNamespace(trafficlight=tls,vehicle=SimpleNamespace(getIDList=lambda:['ego'],
        getNextTLS=lambda vid:[('junction',1,25,'r')]))
    priority=EgoSignalPriority();changed=priority.update(con,0)
    scheduled=changed['junction'];assert active[0]=='ego_priority'
    assert [p.duration for p in scheduled.phases[:3]]==[6,3,6]
    assert phase_countdowns(scheduled.phases,0,6)[1]==15
    assert scheduled.phases[3].state=='rG'
    # No second request modifies an in-progress transition.
    assert priority.update(con,1)=={}
    con.vehicle.getNextTLS=lambda vid:[]
    assert priority.update(con,39)['junction'].programID=='0'
    assert active[0]=='0' and phase[0]==0
