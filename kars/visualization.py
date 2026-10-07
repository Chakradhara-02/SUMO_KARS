import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import networkx as nx
from rdflib import Graph

plt.rcParams.update({'figure.dpi':130,'font.size':10,'axes.grid':True,'grid.alpha':.2})

def plot_run(output):
    df = pd.read_csv(output/'ego.csv')
    fig,axes = plt.subplots(4,1,figsize=(10,10),sharex=True)
    for ax,column,label in zip(axes,['speed','acceleration','jerk','clearance'],
                               ['Speed (m/s)','Acceleration (m/s²)','Jerk (m/s³)','Clearance (m)']):
        ax.plot(df.timestamp,df[column],color='#167e9c')
        ax.set_ylabel(label)
    axes[-1].set_xlabel('Simulation time (s)')
    fig.suptitle('Measured SUMO ego vehicle states')
    fig.tight_layout()
    fig.savefig(output/'dynamics.png'); plt.close(fig)
    plans = json.loads((output/'plans.json').read_text())
    # Choose the strongest visible change, preserving chronological snapshots in JSON.
    display=[p for p in plans if p['trajectory']] or plans
    plan = max(display,key=lambda p:p['removed_edges']) if display else None
    if plan:
        fig,axes = plt.subplots(1,2,figsize=(13,5))
        for ax,key,title in zip(axes,['raw','adjusted'],['Online reachable set','Knowledge-adjusted set and DP chain']):
            values = plan[key]
            ax.scatter([n['x'] for n in values],[n['t'] for n in values],c=[n['lane'] for n in values],
                       s=12,cmap='viridis',vmin=0,vmax=2,alpha=.55)
            if key=='adjusted':
                lookup = {n['id']:n for n in values}
                chain = [lookup[n] for n in plan['chain']]
                ax.plot([n['x'] for n in chain],[n['t'] for n in chain],'r-o',label='DP/A* chain')
                ax.legend()
            ax.set(xlabel='Longitudinal position (m)',ylabel='Time (s)',title=title)
        fig.tight_layout(); fig.savefig(output/'reachable_set.png'); plt.close(fig)
        corridor_plan=max((p for p in plans if len(p['candidates'])>1),key=lambda p:p['removed_edges'],default=plan)
        if corridor_plan['candidates']:
            fig,axes=plt.subplots(1,len(corridor_plan['candidates']),figsize=(13,5),squeeze=False)
            lookup={n['id']:n for n in corridor_plan['adjusted']}
            for ax,candidate in zip(axes.flat,corridor_plan['candidates']):
                points=[lookup[n] for n in candidate.get('nodes',lookup)]
                selected=candidate['lane']==corridor_plan['selected_lane']
                ax.scatter([n['x'] for n in points],[n['t'] for n in points],s=12,
                           color='#d83f45' if selected else '#889aa0',alpha=.4)
                ax.set(xlabel='Position (m)',ylabel='Time (s)',
                       title=f"Lane {candidate['lane']} {'selected' if selected else 'rejected'}\nscore={candidate['score']:.2f}")
            fig.tight_layout(); fig.savefig(output/'corridors.png'); plt.close(fig)
        fig,ax = plt.subplots(figsize=(12,4))
        for lane in range(3):
            ax.axhline(lane*3.2,color='gray',lw=1,ls='--')
        ax.plot(df.x,df.lane*3.2,label='Measured lane centers',color='#167e9c')
        for c in plan['constraints']:
            if c['source'] in ('construction','temporary roadblock','speed-limit zone','crossing advisory'):
                lane = c['lane'] if c['lane']>=0 else 1
                ax.axvspan(c['start'],c['end'],alpha=.12,color='orange')
                ax.text(c['start'],lane*3.2+.2,c['source'],fontsize=8,rotation=25)
        ax.set(xlabel='Position (m)',ylabel='Lane center (m)',title='Road boundaries, restrictions and measured path',ylim=(-1.6,8))
        ax.legend(); fig.tight_layout(); fig.savefig(output/'road_trajectory.png'); plt.close(fig)
        trajectory = next((p['trajectory'] for p in reversed(plans) if p['trajectory']),None)
        if trajectory:
            fig,axes = plt.subplots(3,2,figsize=(10,8))
            for ax,column in zip(axes.flat,['x','y','velocity','acceleration','jerk','lane']):
                ax.plot(trajectory['time'],trajectory[column],'-o'); ax.set(xlabel='Time (s)',ylabel=column)
            fig.suptitle('Planned trajectory (lane-level lateral approximation)')
            fig.tight_layout(); fig.savefig(output/'planned_trajectory.png'); plt.close(fig)
    rdf = Graph().parse(output/'dynamic.ttl')
    graph = nx.DiGraph()
    selected_subjects={'ego','center','constraint_0','constraint_2'}
    selected_properties={'type','locatedAt','hasSpeed','timestamp','hasCurrentColor','source','kind','start','end','speed'}
    for s,p,o in sorted(rdf,key=lambda triple:tuple(str(v) for v in triple)):
        if str(s).split('#')[-1] not in selected_subjects or str(p).split('#')[-1] not in selected_properties:
            continue
        graph.add_edge(str(s).split('#')[-1],str(o).split('#')[-1],label=str(p).split('#')[-1])
    fig,ax = plt.subplots(figsize=(13,9))
    positions=nx.spring_layout(graph,seed=1,k=1.1,iterations=150)
    nx.draw_networkx(graph,pos=positions,ax=ax,font_size=9,node_size=550,
                     node_color='#b4dfe5',arrowsize=8)
    nx.draw_networkx_edge_labels(graph,pos=positions,edge_labels=nx.get_edge_attributes(graph,'label'),font_size=8,ax=ax)
    ax.set_title('Dynamic RDF: ego state, observed signal and speed restrictions (subset)'); ax.axis('off')
    fig.tight_layout(); fig.savefig(output/'knowledge_graph.png'); plt.close(fig)
    plot_constraint_categories(output)

def plot_constraint_categories(output):
    from .models import load_config,State,Constraint
    from .reachable_set import offline_rs,online_rs,rs_adjustment
    config=load_config()
    config['lanes']=1
    raw=online_rs(State(0,8,0),offline_rs(config),config)
    examples=[Constraint('spatial',12,24,0),Constraint('spatial_speed',12,40,speed=6),
              Constraint('spatial_temporal',12,24,0,begin=1,finish=2),
              Constraint('spatial_temporal_speed',12,40,speed=6,begin=1,finish=3)]
    fig,axes=plt.subplots(2,2,figsize=(12,9))
    for ax,constraint in zip(axes.flat,examples):
        adjusted,_=rs_adjustment(raw,[constraint])
        for graph,color,label in [(raw,'#ced5d9','Raw'),(adjusted,'#167e9c','Retained')]:
            states=[graph.nodes[n]['state'] for n in graph]
            ax.scatter([s.x for s in states],[s.t for s in states],s=12,color=color,label=label,alpha=.65)
        ax.set(xlabel='Position (m)',ylabel='Time (s)',title=constraint.kind.replace('_',' + '))
        ax.legend()
    fig.suptitle('Four restriction types: one-lane illustration')
    fig.tight_layout(); fig.savefig(output/'constraint_categories.png'); plt.close(fig)

def plot_comparison(frame, output):
    grouped = frame.groupby(['scenario','algorithm'])
    metrics = ['success','average_speed','minimum_clearance','acceleration_rms','jerk_rms','planning_ms']
    fig,axes = plt.subplots(3,2,figsize=(13,12))
    for ax,metric in zip(axes.flat,metrics):
        means,std = grouped[metric].mean(),grouped[metric].std().fillna(0)
        means.plot.bar(yerr=std,ax=ax,color='#167e9c',capsize=2)
        ax.set_title(metric+' (mean ± SD)'); ax.tick_params(axis='x',labelsize=7)
    fig.tight_layout(); fig.savefig(output/'comparison.png'); plt.close(fig)
