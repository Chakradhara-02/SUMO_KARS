"""Animated replay of recorded SUMO and planner states, not a new simulation."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation,PillowWriter
from matplotlib.patches import Rectangle

def replay(folder,frames=40):
    plans=json.loads((folder/'plans.json').read_text())
    measured=pd.read_csv(folder/'ego.csv')
    chosen=np.linspace(0,len(plans)-1,min(frames,len(plans)),dtype=int)
    fig,(road,rs)=plt.subplots(1,2,figsize=(13,5))
    def update(index):
        plan=plans[chosen[index]]
        road.clear(); rs.clear()
        row=measured.iloc[(measured.timestamp-plan['time']).abs().argmin()]
        for lane in range(3):
            road.axhline(lane*3.2,color='gray',ls='--',lw=1)
        for c in plan['constraints']:
            if c['source'] in ('construction','temporary roadblock','updated speed limit','crossing advisory','speed-limit zone'):
                y=c['lane']*3.2-1.3 if c['lane']>=0 else -1.3
                height=2.6 if c['lane']>=0 else 9.0
                road.add_patch(Rectangle((c['start'],y),c['end']-c['start'],height,
                                        color='orange',alpha=.22))
        road.scatter([row.x],[row.lane*3.2],s=180,c='#167e9c',marker='s',label='Measured ego')
        road.set(xlim=(0,1000),ylim=(-1.6,8),xlabel='Position (m)',ylabel='Lane center (m)',
                 title=f"SUMO t={plan['time']:.1f} s, speed={row.speed:.1f} m/s")
        road.legend(loc='upper left')
        for name,color,label in [('raw','#cbd4d8','Raw RS'),('adjusted','#167e9c','Retained RS')]:
            points=plan[name]
            rs.scatter([p['x'] for p in points],[p['t'] for p in points],s=10,c=color,alpha=.5,label=label)
        lookup={p['id']:p for p in plan['adjusted']}
        chain=[lookup[n] for n in plan['chain']]
        if chain:
            rs.plot([p['x'] for p in chain],[p['t'] for p in chain],'r-o',label='Selected chain')
        rs.set(xlabel='Position (m)',ylabel='Future simulation time (s)',
               title=f"SPARQL constraints={len(plan['constraints'])}, removed edges={plan['removed_edges']}")
        rs.legend(loc='upper left',fontsize=8)
        fig.suptitle('Recorded traffic-knowledge planning: '+('EMERGENCY BRAKING' if plan['emergency'] else f"Selected corridor lane {plan['selected_lane']}"))
        fig.tight_layout()
    animation=FuncAnimation(fig,update,frames=len(chosen),interval=300)
    animation.save(folder/'demo.gif',writer=PillowWriter(fps=3),dpi=85)
    plt.close(fig)
    print(folder/'demo.gif')
