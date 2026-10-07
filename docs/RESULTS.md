# Verified results

Run `main.py experiments --repeats 3` to reproduce the comparison. SUMO safety stays enabled. Success means arrival without a collision event; rule violations remain separate. All values below come from measured run files.

## Demonstration runs

| Scenario | Arrival | Collisions | Rule violation samples | Average speed (m/s) | Minimum clearance (m) | Emergency entries |
|---|---:|---:|---:|---:|---:|---:|
| demo | 1 | 0 | 0 | 10.052 | 21.915 | 2 |
| emergency | 1 | 0 | 0 | 9.420 | 11.203 | 4 |

## Repeated comparisons

48 completed runs in the measured CSV. Three seeds are required for every scenario/planner group.

| Scenario | Planner | N | Success mean | Speed mean ± SD (m/s) | Rule samples mean |
|---|---|---:|---:|---|---:|
| dynamic | astar | 3 | 1.000 | 10.195 ± 0.133 | 0.0 |
| dynamic | kars | 3 | 1.000 | 10.180 ± 0.107 | 0.0 |
| dynamic | kars_delay | 3 | 1.000 | 10.155 ± 0.139 | 0.0 |
| dynamic | rs | 3 | 1.000 | 11.191 ± 0.505 | 67.7 |
| iot_delay | astar | 3 | 1.000 | 10.171 ± 0.070 | 0.0 |
| iot_delay | kars | 3 | 1.000 | 10.049 ± 0.239 | 0.0 |
| iot_delay | kars_delay | 3 | 1.000 | 9.928 ± 0.315 | 0.0 |
| iot_delay | rs | 3 | 1.000 | 11.774 ± 0.000 | 67.0 |
| semi_dynamic | astar | 3 | 1.000 | 10.203 ± 0.163 | 0.0 |
| semi_dynamic | kars | 3 | 1.000 | 10.195 ± 0.162 | 0.0 |
| semi_dynamic | kars_delay | 3 | 1.000 | 10.133 ± 0.261 | 0.0 |
| semi_dynamic | rs | 3 | 1.000 | 11.707 ± 0.115 | 68.3 |
| static | astar | 3 | 1.000 | 10.258 ± 0.106 | 0.0 |
| static | kars | 3 | 1.000 | 10.258 ± 0.106 | 0.0 |
| static | kars_delay | 3 | 1.000 | 10.222 ± 0.170 | 0.0 |
| static | rs | 3 | 1.000 | 11.603 ± 0.158 | 69.0 |

Collision-free runs do not establish superiority because SUMO can intervene. RS is an information ablation; A* and KARS receive the same delivered constraints. See clearance, rule compliance, arrival, comfort and timing together.

## Communication and density sweep

72 runs. Delay values: [0.0, 0.5, 1.0, 2.0]. Vehicle insertion periods: [5, 9, 15] seconds. Smaller period means denser traffic.

| Delay (s) | Planner | Arrival mean | Speed mean ± SD (m/s) |
|---:|---|---:|---|
| 0.0 | kars | 1.000 | 10.039 ± 0.305 |
| 0.0 | kars_delay | 1.000 | 9.869 ± 0.340 |
| 0.5 | kars | 1.000 | 10.120 ± 0.203 |
| 0.5 | kars_delay | 1.000 | 9.908 ± 0.202 |
| 1.0 | kars | 1.000 | 10.038 ± 0.181 |
| 1.0 | kars_delay | 1.000 | 9.907 ± 0.380 |
| 2.0 | kars | 1.000 | 10.045 ± 0.342 |
| 2.0 | kars_delay | 1.000 | 9.896 ± 0.226 |

At 2 s nominal delay, age-aware KARS had mean minimum clearance 25.686 m versus 16.136 m, with mean speed 9.896 m/s versus 10.045 m/s. Each mean combines three densities and three seeds. Clearance did not improve uniformly at smaller delays, so this supports a conditional safety/efficiency tradeoff, not universal superiority.

## Verification

21 automated tests pass: dynamics, offline/online RS, four restriction types, swept/lane constraints, SPARQL replacement and every example query, connected pruning, corridors, DP/A* cost equivalence, trajectory dynamics, emergency recovery, channel delay/loss, SUMO integration, dashboard loading, actual dynamic lead braking in ego lane, and emergency stop/resume. SUMO GUI connected and moved ego successfully. START, PAUSE, RESUME and RESET were exercised through Streamlit AppTest.

## Interpretation limits

Planner state cap is finite. Obstacles are virtual planning regions. Lateral dynamics are simplified. Crossing has no pedestrian agent. The original paper PDF was not supplied, so exact reproduction is not verified. Sweep results aggregate traffic-density settings at each delay; inspect results.csv and the condition-wise summary.csv for per-density comparisons. Wall-clock timings depend on local workload. Some recorded experiment runs overlapped the sweep; rerun experiments alone for a controlled timing benchmark.
