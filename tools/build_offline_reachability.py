"""Precompute obstacle-independent bicycle motion primitives before app runtime."""
from pathlib import Path
import json,math
ROOT=Path(__file__).resolve().parents[1]
SPEEDS=[0,1,2,4,6,8,10,12,14,18,22]
ACCELERATIONS=[-4,0,2]
STEERING=[-.28,-.18,-.09,0,.09,.18,.28]
clamp=lambda value,low,high:max(low,min(high,value))
records=[]
for direction in [1,-1]:
 for initial_speed in SPEEDS if direction==1 else [0,1,2]:
  for initial_acceleration in ACCELERATIONS:
   branches=[]
   for target_a in ACCELERATIONS:
    for target_steer in STEERING:
     for profile in ['arc'] if target_steer==0 else ['arc','lane_change']:
      length=4.7;wheelbase=length*.6;dt=.1;horizon=3
      x=-length/2;y=0.;yaw=math.pi/2;speed=initial_speed;accel=initial_acceleration;steer=0.
      points=[[0,0,0,90,direction*speed]]
      for step in range(1,31):
       accel+=clamp(target_a-accel,-4*dt,4*dt)
       limit=1.4 if direction<0 else 22.2
       next_speed=max(0,speed+accel*dt)
       if next_speed>limit:next_speed=max(limit,speed-4*dt) if speed>limit else limit
       goal=target_steer*math.cos(math.pi*(step-1)*dt/horizon) if profile=='lane_change' else target_steer
       steer+=clamp(goal-steer,-.18*dt,.18*dt)
       maximum=math.atan(2.5*wheelbase/max(1,next_speed**2));bounded=clamp(steer,-maximum,maximum)
       v=(speed+next_speed)/2;change=direction*v/wheelbase*math.tan(bounded)*dt;mid=yaw+change/2
       x+=direction*v*math.sin(mid)*dt;y+=direction*v*math.cos(mid)*dt;yaw+=change
       points.append([round(step*dt,3),round(x+math.sin(yaw)*length/2,4),round(y+math.cos(yaw)*length/2,4),round(math.degrees(yaw)%360,4),round(direction*next_speed,4)])
       speed=next_speed
      branches.append({'acceleration':target_a,'steering':target_steer,'profile':profile,'points':points})
   records.append({'direction':direction,'speed':initial_speed,'acceleration':initial_acceleration,'branches':branches})
result={'schema':1,'model':'offline sampled kinematic bicycle primitives','horizon':3,'dt':.1,'length':4.7,'wheelbase':2.82,'coordinates':'front-bumper reference; x forward, y left; heading 90 degrees','filtered_for_obstacles':False,'speed_bins':SPEEDS,'acceleration_bins':ACCELERATIONS,'records':records}
target=ROOT/'simulation_ui/offline-reachability.json';target.write_text(json.dumps(result,separators=(',',':')),encoding='utf-8')
print(f'Precomputed {len(records)} state bins; {sum(len(r["branches"]) for r in records)} branches; {target.stat().st_size:,} bytes')
