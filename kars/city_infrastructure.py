"""Static signal clocks, manoeuvre indications and off-road arrival bays."""
import math
import xml.etree.ElementTree as ET


def phase_countdowns(phases,index,remaining):
    values=[]
    for link,current in enumerate(phases[index].state):
        delay=max(0.,remaining)
        for step in range(1,len(phases)+1):
            phase=phases[(index+step)%len(phases)];color=phase.state[link].lower()
            if (current.lower()=='r' and color=='g') or (current.lower()!='r' and color!=current.lower()):break
            delay+=phase.duration
        else:delay=None
        values.append(None if delay is None else max(0,math.ceil(delay-1e-7)))
    return values


class SignalClock:
    def __init__(self,connection):
        self.programs={tid:next(p for p in connection.trafficlight.getAllProgramLogics(tid)
                               if p.programID==connection.trafficlight.getProgram(tid))
                       for tid in connection.trafficlight.getIDList()}

    def sample(self,connection,now):
        result=[]
        for tid,logic in self.programs.items():
            phase=connection.trafficlight.getPhase(tid);remaining=connection.trafficlight.getNextSwitch(tid)-now
            result.append({'id':tid,'state':connection.trafficlight.getRedYellowGreenState(tid),
                           'countdowns':phase_countdowns(logic.phases,phase,remaining),
                           'phase':phase,'next_switch':now+max(0,remaining)})
        return result


def indicator_intent(raw,direction='s',junction_distance=999,lateral_speed=0,parking=False,parked=False):
    base=raw&~7
    if parked:return base,'Parked at destination'
    if parking:return base|2,'Pulling into left curbside bay'
    if abs(lateral_speed)>.08:
        indicator=2 if lateral_speed>0 else 1
        return base|indicator,'Changing lane '+('left' if indicator&2 else 'right')
    if junction_distance<=45 and direction.lower() in ('l','r'):
        return base|(2 if direction.lower()=='l' else 1),'Turning '+('left' if direction.lower()=='l' else 'right')
    return base,'Continuing straight'


def arrival_bay(network,edge_id,destination):
    root=ET.parse(network).getroot();lane=root.find(f"edge[@id='{edge_id}']/lane[@index='0']")
    length=float(lane.get('length'));end=max(12.,length-10);start=max(2.,end-14)
    shape=[[float(v) for v in p.split(',')] for p in lane.get('shape').split()]
    total=sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(shape,shape[1:]))
    wanted=(start+end)/2/length*total;station=0
    for a,b in zip(shape,shape[1:]):
        segment=math.hypot(b[0]-a[0],b[1]-a[1]);ratio=max(0,min(1,(wanted-station)/max(.001,segment)))
        if station+segment>=wanted:
            dx,dy=(b[0]-a[0])/segment,(b[1]-a[1])/segment
            offset=float(lane.get('width','3.2'))/2+2.0
            z=(a[2] if len(a)>2 else 0)+((b[2] if len(b)>2 else 0)-(a[2] if len(a)>2 else 0))*ratio
            return {'id':'destination_bay','lane':lane.get('id'),'edge':edge_id,'start':start,'end':end,
                    'x':a[0]+(b[0]-a[0])*ratio-dy*offset,'y':a[1]+(b[1]-a[1])*ratio+dx*offset,'z':z,
                    'heading':math.degrees(math.atan2(dx,dy))%360,'name':destination['name']+' curbside arrival',
                    'length':8.,'width':3.0}
        station+=segment
    raise ValueError('Arrival lane geometry is empty')


def write_arrival_area(path,bay):
    root=ET.Element('additional')
    area=ET.SubElement(root,'parkingArea',id=bay['id'],lane=bay['lane'],startPos=str(bay['start']),
                       endPos=str(bay['end']),roadsideCapacity='0',onRoad='false',lefthand='true')
    ET.SubElement(area,'space',x=str(bay['x']),y=str(bay['y']),z=str(bay['z']),
                  width=str(bay['width']),length=str(bay['length']),angle=str((180-bay['heading'])%360))
    ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)


def road_lateral_speed(previous,current,shape):
    """World displacement projected onto geometric road-left, independent of driving side."""
    if not previous or previous['road_id']!=current.road_id or current.road_id.startswith(':'):return 0.
    dt=current.timestamp-previous['timestamp']
    if dt<=0 or len(shape)<2:return 0.
    a,b=shape[0],shape[-1];dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
    return (-dy*(current.x-previous['x'])+dx*(current.y-previous['y']))/max(.001,length)/dt


def protected_signal_programs(root):
    """One conflict-free incoming approach at a time, including protected right turns."""
    for logic in root.findall('tlLogic'):
        junction=root.find("junction[@id='%s']"%logic.get('id'))
        requests={int(r.get('index')):r.get('foes')[::-1] for r in junction.findall('request')}
        groups={}
        for link in root.findall('connection'):
            if link.get('tl')==logic.get('id'):groups.setdefault(link.get('from'),set()).add(int(link.get('linkIndex')))
        size=max(i for ids in groups.values() for i in ids)+1
        for phase in list(logic.findall('phase')):logic.remove(phase)
        for incoming,ids in sorted(groups.items()):
            # Generated junctions use one request index per controlled link.
            for a in ids:
                for b in ids:
                    if a!=b and requests.get(a,'')[b:b+1]=='1':
                        raise ValueError('Conflicting links in protected approach '+incoming)
            green=''.join('G' if i in ids else 'r' for i in range(size))
            ET.SubElement(logic,'phase',duration='15',state=green,name=incoming)
            ET.SubElement(logic,'phase',duration='3',state=''.join('y' if i in ids else 'r' for i in range(size)))
            ET.SubElement(logic,'phase',duration='6',state='r'*size)


def city_motion_context(ego,parked,signal,leader=None,next_links=()):
    if parked:return {'state':'parked','message':'Vehicle secured in destination bay'}
    if ego.speed>.3:return {'state':'driving','message':'Following the selected route'}
    if leader and leader[0] and 0<=leader[1]<10:
        return {'state':'queue','message':'Waiting for the vehicle ahead','leader_id':leader[0],'gap':leader[1]+2.5}
    if signal and signal['distance']<40:
        color=signal['color'].lower()
        if color in ('r','y'):return {'state':'red_light','message':'Waiting for the signal to release this approach'}
        if color=='g':
            if next_links and (not next_links[0][3] or next_links[0][4]):return {'state':'junction_clearance','message':'Green - waiting for a clear junction or exit'}
            return {'state':'starting','message':'Green - preparing to move'}
    return {'state':'stopped','message':'Waiting for a safe gap in traffic'}


class EgoSignalPriority:
    """Grant ego's protected approach within 15 s of a nearby red request.

    Shorten only the remaining conflicting green. Preserve its 3 s yellow and
    6 s all-red clearance, then restore the normal protected program.
    """
    def __init__(self):
        self.active={}

    def update(self,connection,now):
        import copy
        from traci import trafficlight
        changed={};tls=connection.trafficlight
        for tid,(original,end,resume) in list(self.active.items()):
            if now>=end-1e-7:
                tls.setProgramLogic(tid,original);tls.setProgram(tid,original.programID)
                tls.setPhase(tid,resume);changed[tid]=original;del self.active[tid]
        if 'ego' not in connection.vehicle.getIDList():return changed
        upcoming=connection.vehicle.getNextTLS('ego')
        if not upcoming:return changed
        tid,link,distance,color=upcoming[0]
        if tid in self.active or not 0<=distance<=60 or color.lower()!='r':return changed
        original=next(p for p in tls.getAllProgramLogics(tid) if p.programID==tls.getProgram(tid))
        if original.type!=0:return changed
        target=next((i for i,p in enumerate(original.phases) if p.state[link]=='G'),None)
        if target is None:return changed
        current=tls.getRedYellowGreenState(tid);remaining=max(.1,tls.getNextSwitch(tid)-now)
        phases=[]
        if any(c.lower()=='g' for c in current):
            phases.append(trafficlight.Phase(min(6.,remaining),current))
            phases.append(trafficlight.Phase(3.,''.join('y' if c.lower()=='g' else c for c in current)))
            phases.append(trafficlight.Phase(6.,'r'*len(current)))
        elif 'y' in current.lower():
            phases.extend([trafficlight.Phase(min(3.,remaining),current),trafficlight.Phase(6.,'r'*len(current))])
        else:phases.append(trafficlight.Phase(min(6.,remaining),'r'*len(current)))
        wait=sum(p.duration for p in phases)
        for offset in range(3):
            phase=copy.deepcopy(original.phases[(target+offset)%len(original.phases)])
            phase.next=();phases.append(phase)
        program=trafficlight.Logic('ego_priority',0,0,phases)
        tls.setProgramLogic(tid,program);tls.setProgram(tid,program.programID);tls.setPhase(tid,0)
        changed[tid]=program
        self.active[tid]=(original,now+sum(p.duration for p in phases),(target+3)%len(original.phases))
        return changed
