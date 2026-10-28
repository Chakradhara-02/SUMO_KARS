"""Ground-level parking facilities and bounded forward/reverse manoeuvres."""
import math

# Lot origins lie inside blocks, away from ramps and through lanes.
SITES={
 'n0_0':('n0_0',35,35),'n2_0':('n2_0',405,35),'n4_0':('n4_0',895,35),
 'n0_2':('n0_2',35,455),'n2_2':('n2_1',405,235),'n4_2':('n4_2',900,455),
 'n0_4':('n0_4',35,895),'n2_4':('n2_4',405,895),'n4_4':('n4_4',900,725),
 'city_mall':('n3_1',645,225)}


def parking_lot(place):
    host,x,y=SITES[place['id']]
    slots=[]
    for i in range(8):
        cx=x+22+i*3.4;cy=y+25
        slots.append({'id':f'A{i+1}','x':cx,'y':cy,'z':0.,'heading':180.,'length':6.,'width':3.1,
                      'occupied':i in (1,4,6),'front_x':cx,'front_y':cy-2.35})
    return {'id':place['id'],'name':place['name'],'host':host,'x':x,'y':y,'z':0.,
            'bounds':[x,y,x+78,y+66],'aisle_y':y+12,'slots':slots,
            'edge':f"park_{place['id']}_aisle__arrival_{place['id']}",
            'kind':'mall' if place['id']=='city_mall' else 'destination car park'}


def choose_slot(lot,slot_id):
    slot=next((s for s in lot['slots'] if s['id']==slot_id),None)
    if slot is None:raise ValueError('Unknown parking bay')
    if slot['occupied']:raise ValueError('This bay is occupied. Choose an empty bay.')
    return slot


def slot_bay(lot,slot):
    return {'id':'destination_bay','slot_id':slot['id'],'edge':lot['edge'],'lane':lot['edge']+'_0',
            'x':slot['front_x'],'y':slot['front_y'],'z':0.,'heading':180.,'length':6.,'width':3.1,
            'name':lot['name']+' bay '+slot['id'],'start':3.,'end':12.}


def _bezier(points,t):
    a,b,c,d=points;u=1-t
    x=u**3*a[0]+3*u*u*t*b[0]+3*u*t*t*c[0]+t**3*d[0]
    y=u**3*a[1]+3*u*u*t*b[1]+3*u*t*t*c[1]+t**3*d[1]
    dx=3*u*u*(b[0]-a[0])+6*u*t*(c[0]-b[0])+3*t*t*(d[0]-c[0])
    dy=3*u*u*(b[1]-a[1])+6*u*t*(c[1]-b[1])+3*t*t*(d[1]-c[1])
    return x,y,dx,dy


def footprint(pose,width=2.05,length=4.7):
    h=math.radians(pose['heading']);fx,fy=math.sin(h),math.cos(h);nx,ny=-fy,fx
    return [(pose['x']-fx*d+nx*side*width/2,pose['y']-fy*d+ny*side*width/2) for d,side in [(0,-1),(0,1),(length,1),(length,-1)]]


def overlaps(a,b):
    for poly in (a,b):
        for i in range(2):
            dx,dy=poly[i+1][0]-poly[i][0],poly[i+1][1]-poly[i][1]
            aa=[-dy*x+dx*y for x,y in a];bb=[-dy*x+dx*y for x,y in b]
            if min(max(aa),max(bb))<=max(min(aa),min(bb))+.001:return False
    return True


def parking_path(lot,slot,start):
    """Front-bumper poses: pull forward, pause, reverse on a 5 m radius, dock."""
    target=choose_slot(lot,slot['id']);r=5.;k=.55228475;cx=target['x'];ay=lot['aisle_y']
    # Work at the vehicle centre and reconstruct its front bumper afterwards.
    angle=math.radians(start.get('heading',90));sx,sy=start['x']-2.35*math.sin(angle),start['y']-2.35*math.cos(angle);points=[]
    def add(x,y,heading,gear,stage):
        h=math.radians(heading);points.append({'x':x+2.35*math.sin(h),'y':y+2.35*math.cos(h),
          'z':0.,'heading':heading%360,'gear':gear,'stage':stage})
    distance=max(0,cx+r-sx)
    for i in range(max(2,math.ceil(distance/.12))+1):
        t=i/max(2,math.ceil(distance/.12));blend=min(1,distance*t/3);blend=blend*blend*(3-2*blend);yaw=start.get('heading',90)+((90-start.get('heading',90)+180)%360-180)*blend;add(sx+(cx+r-sx)*t,sy+(ay-sy)*blend,yaw,'D','positioning')
    add(cx+r,ay,90,'R','reversing')
    curve=[(cx+r,ay),(cx+r-k*r,ay),(cx,ay+r-k*r),(cx,ay+r)]
    for i in range(1,81):
        x,y,dx,dy=_bezier(curve,i/80);add(x,y,math.degrees(math.atan2(-dx,-dy)),'R','reversing')
    for i in range(1,math.ceil((target['y']-ay-r)/.1)+1):
        n=math.ceil((target['y']-ay-r)/.1);add(cx,ay+r+(target['y']-ay-r)*i/n,180,'R','aligning')
    # Validate the swept rectangular footprint against occupied bays and lot boundary.
    for p in points:
        corners=footprint(p)
        if not all(lot['bounds'][0]+.5<x<lot['bounds'][2]-.5 and lot['bounds'][1]+.5<y<lot['bounds'][3]-.5 for x,y in corners):
            raise ValueError('Parking manoeuvre exceeds the lot boundary')
        # Occupied cars are 4.7 x 1.8 m, facing the same aisle.
        for other in lot['slots']:
            if not other['occupied']:continue
            if overlaps(corners,footprint({'x':other['front_x'],'y':other['front_y'],'heading':180},width=1.8)):
                raise ValueError('Parking path intersects an occupied bay')
    return points


class ParkingController:
    def __init__(self,lot,slot_id=None):
        self.lot=lot;self.slot_id=slot_id;self.path=[];self.index=0;self.progress=0.;self.speed=0.;self.pause=0.;self.done=False;self.active=False;self.stage='approaching';self.pose=None
        if slot_id:choose_slot(lot,slot_id)

    def select(self,slot_id):
        choose_slot(self.lot,slot_id)
        if self.active and self.stage!='waiting_selection':raise ValueError('Parking manoeuvre has already started')
        self.slot_id=slot_id

    def start(self,pose):
        self.active=True;self.pose=dict(pose);self.stage='waiting_selection'
        if self.slot_id:self._plan()

    def _plan(self):
        self.path=parking_path(self.lot,choose_slot(self.lot,self.slot_id),self.pose);self.stage='positioning';self.pause=1.0

    def step(self,dt):
        if not self.active or self.done:return self.pose
        if self.stage=='waiting_selection':
            if not self.slot_id:return self.pose
            self._plan()
        if self.pause>0:self.pause=max(0,self.pause-dt);self.speed=0.;self.pose['speed']=0.;return self.pose
        if self.index>=len(self.path)-1:
            self.done=True;self.stage='parked';self.speed=0.;self.pose.update(gear='P',stage='parked');return self.pose
        current=self.path[self.index];nxt=self.path[self.index+1]
        gear=current['gear']
        if self.pose.get('gear',gear)!=gear:
            self.pose['gear']=gear;self.pause=1.4;self.speed=0.;return self.pose
        # Acceleration/deceleration limits and an explicit stop before changing gear.
        remain=0.
        for a,b in zip(self.path[self.index:],self.path[self.index+1:]):
            if a['gear']!=gear:break
            remain+=math.hypot(b['x']-a['x'],b['y']-a['y'])
        desired=min(1.4 if gear=='D' else .85,math.sqrt(max(.02,2*.7*remain)))
        self.speed=max(0.,min(self.speed+.5*dt,desired));self.progress+=self.speed*dt
        while self.index<len(self.path)-1:
            a,b=self.path[self.index:self.index+2];segment=math.hypot(b['x']-a['x'],b['y']-a['y'])
            if self.progress<segment:break
            if a['gear']!=b['gear']:
                self.index+=1;self.progress=0.;self.pause=1.4;self.speed=0.;break
            self.progress-=segment;self.index+=1
        if self.index>=len(self.path)-1:self.pose=dict(self.path[-1]);return self.pose
        a,b=self.path[self.index:self.index+2];length=math.hypot(b['x']-a['x'],b['y']-a['y']);t=min(1,self.progress/max(.001,length));angle=(b['heading']-a['heading']+180)%360-180
        self.pose={**a,'x':a['x']+(b['x']-a['x'])*t,'y':a['y']+(b['y']-a['y'])*t,'heading':(a['heading']+angle*t)%360,'speed':self.speed if a['gear']=='D' else -self.speed}
        self.stage=a['stage'];return self.pose

    def snapshot(self):
        return {'lot_id':self.lot['id'],'slot_id':self.slot_id,'stage':self.stage,'gear':'P' if self.done else self.pose.get('gear','D') if self.pose else 'D',
                'progress':1. if self.done else self.index/max(1,len(self.path)-1),'active':self.active,'complete':self.done,
                'slots':self.lot['slots'],'path':(self.path[::6]+[self.path[-1]]) if self.active and self.path else [],
                'path_index':self.index,'remaining_path':self.path[max(0,self.index-15):self.index+100:2] if self.active else []}
