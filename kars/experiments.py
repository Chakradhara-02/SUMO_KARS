import pandas as pd
from .models import ROOT
from .simulation import run_simulation
from .visualization import plot_comparison

def save(rows,folder,plot=True):
    folder.mkdir(parents=True,exist_ok=True)
    frame = pd.DataFrame(rows)
    frame.to_csv(folder/'results.csv',index=False)
    groups=['scenario','algorithm']
    if folder.name=='sweep':
        groups += ['delay','density_period']
    numeric = frame.select_dtypes('number').columns.difference(['seed']+groups)
    frame.groupby(groups)[numeric].agg(['mean','std']).to_csv(folder/'summary.csv')
    if plot:
        plot_comparison(frame,folder)
    return frame

def experiments(repeats=3,duration=None,scenarios=None):
    if repeats<1:
        raise ValueError('repeats must be positive')
    rows=[]
    previous=ROOT/'outputs/experiments/results.csv'
    if scenarios and previous.exists():
        frame=pd.read_csv(previous)
        rows=frame[~frame.scenario.isin(scenarios)].to_dict('records')
    for scenario in (scenarios or ['static','semi_dynamic','dynamic','iot_delay']):
        for algorithm in ['rs','astar','kars','kars_delay']:
            for seed in range(1,repeats+1):
                rows.append(run_simulation(scenario,algorithm,seed,duration,make_plots=False))
                save(rows,ROOT/'outputs/experiments',plot=False)
    save(rows,ROOT/'outputs/experiments')
    return rows

def sweep(repeats=3,duration=None):
    rows=[]
    for delay in [0.,.5,1.,2.]:
        for density in [5,9,15]:
            for algorithm in ['kars','kars_delay']:
                for seed in range(1,repeats+1):
                    folder=ROOT/'outputs/sweep'/f'{algorithm}_delay{delay}_density{density}_seed{seed}'
                    rows.append(run_simulation('iot_delay',algorithm,seed,duration,delay=delay,loss=.15,
                                               output=folder,make_plots=False,density=density))
    frame=save(rows,ROOT/'outputs/sweep')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(12,4))
    for algorithm,subset in frame.groupby('algorithm'):
        for ax,column in zip(axes,['delay','density_period']):
            values=subset.groupby(column).average_speed.agg(['mean','std'])
            ax.errorbar(values.index,values['mean'],yerr=values['std'].fillna(0),label=algorithm,marker='o')
            ax.set(xlabel=column,ylabel='Average speed (m/s)'); ax.legend()
    fig.tight_layout(); fig.savefig(ROOT/'outputs/sweep/robustness.png'); plt.close(fig)
    return rows
