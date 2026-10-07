"""Refresh documentation from measured outputs only."""
import json
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
lines=['# Verified results','', 'Run `main.py experiments --repeats 3` to reproduce the comparison. SUMO safety stays enabled. Success means arrival without a collision event; rule violations remain separate. All values below come from measured run files.','',
       '## Demonstration runs','', '| Scenario | Arrival | Collisions | Rule violation samples | Average speed (m/s) | Minimum clearance (m) | Emergency entries |','|---|---:|---:|---:|---:|---:|---:|']
for folder in ['demo_kars_delay_seed1','emergency_kars_delay_seed1']:
    path=ROOT/'outputs'/folder/'metrics.json'
    if path.exists():
        m=json.loads(path.read_text())
        lines.append(f"| {m['scenario']} | {m['arrived']} | {m['collision_events']} | {m['rule_violations']} | {m['average_speed']:.3f} | {m['minimum_clearance']:.3f} | {m['emergency_entries']} |")
lines+=['','## Repeated comparisons','']
path=ROOT/'outputs/experiments/results.csv'
if path.exists():
    frame=pd.read_csv(path)
    lines += [f'{len(frame)} completed runs in the measured CSV. Three seeds are required for every scenario/planner group.','',
              '| Scenario | Planner | N | Success mean | Speed mean ± SD (m/s) | Rule samples mean |','|---|---|---:|---:|---|---:|']
    for (scenario,algorithm),group in frame.groupby(['scenario','algorithm']):
        lines.append(f"| {scenario} | {algorithm} | {len(group)} | {group.success.mean():.3f} | {group.average_speed.mean():.3f} ± {group.average_speed.std():.3f} | {group.rule_violations.mean():.1f} |")
    lines += ['','Collision-free runs do not establish superiority because SUMO can intervene. RS is an information ablation; A* and KARS receive the same delivered constraints. See clearance, rule compliance, arrival, comfort and timing together.']
path=ROOT/'outputs/sweep/results.csv'
if path.exists():
    frame=pd.read_csv(path)
    lines+=['','## Communication and density sweep','',f'{len(frame)} runs. Delay values: {sorted(float(x) for x in frame.delay.unique())}. Vehicle insertion periods: {sorted(int(x) for x in frame.density_period.unique())} seconds. Smaller period means denser traffic.','',
            '| Delay (s) | Planner | Arrival mean | Speed mean ± SD (m/s) |','|---:|---|---:|---|']
    for (delay,algorithm),group in frame.groupby(['delay','algorithm']):
        lines.append(f'| {delay} | {algorithm} | {group.success.mean():.3f} | {group.average_speed.mean():.3f} ± {group.average_speed.std():.3f} |')
    slow=frame[frame.delay==2.].groupby('algorithm')[['minimum_clearance','average_speed']].mean()
    if {'kars','kars_delay'}.issubset(slow.index):
        base,aware=slow.loc['kars'],slow.loc['kars_delay']
        lines+=['',f"At 2 s nominal delay, age-aware KARS had mean minimum clearance {aware.minimum_clearance:.3f} m versus {base.minimum_clearance:.3f} m, with mean speed {aware.average_speed:.3f} m/s versus {base.average_speed:.3f} m/s. Each mean combines three densities and three seeds. Clearance did not improve uniformly at smaller delays, so this supports a conditional safety/efficiency tradeoff, not universal superiority."]
lines += ['','## Verification','', '21 automated tests pass: dynamics, offline/online RS, four restriction types, swept/lane constraints, SPARQL replacement and every example query, connected pruning, corridors, DP/A* cost equivalence, trajectory dynamics, emergency recovery, channel delay/loss, SUMO integration, dashboard loading, actual dynamic lead braking in ego lane, and emergency stop/resume. SUMO GUI connected and moved ego successfully. START, PAUSE, RESUME and RESET were exercised through Streamlit AppTest.','',
          '## Interpretation limits','', 'Planner state cap is finite. Obstacles are virtual planning regions. Lateral dynamics are simplified. Crossing has no pedestrian agent. The original paper PDF was not supplied, so exact reproduction is not verified. Sweep results aggregate traffic-density settings at each delay; inspect results.csv and the condition-wise summary.csv for per-density comparisons. Wall-clock timings depend on local workload. Some recorded experiment runs overlapped the sweep; rerun experiments alone for a controlled timing benchmark.']
(ROOT/'docs/RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('Updated docs/RESULTS.md from measured files.')
