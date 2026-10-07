# Scope and provenance

The supplied attachment is a specification. It contains no paper pages or equations. The paper metadata identifies Chen, Lu, Wu, Chen and Gong, IEEE Internet of Things Journal 12(23), 51438–51452, DOI 10.1109/JIOT.2025.3613790. Full-text reproduction remains unverified. This table maps requested concepts to this project's implementation; it does not attribute the formulas to the paper.

| Component | Purpose | Input | Output | Algorithm / project logic | Difficulty | Implementation | Provenance |
|---|---|---|---|---|---|---|---|
| IoT layer | Traffic observations | TraCI state | Delayed packets | Seeded delay/loss queue | Low | communication.py | Engineering extension |
| Ontology/KG | Structured facts | Vehicles, rules | Static/dynamic RDF | RDFLib + OWL classes | Medium | knowledge.py, traffic.ttl | Inspired, simplified schema |
| SPARQL | Retrieve constraints | Dynamic RDF | Typed restrictions | SELECT bindings | Low | constraints.rq | Functional project implementation |
| Offline RS | Precompute motion | v, a, dt | Transition table | x'=x+v dt+0.5a dt²; v'=v+a dt | Medium | offline_rs | Approximation |
| Online RS | Reachable graph | Ego state, actions | Layered directed graph | Grid-binned propagation | Medium | online_rs | Approximation |
| Adjustment | Remove unsafe moves | Rules + graph | Pruned graph | Swept-edge/time/speed checks | Medium | rs_adjustment | Approximation |
| Corridor | Candidate drivable chains | Pruned DAG | Terminal-lane ancestor subgraphs | Reachable ancestors; layer width proxy | Medium | corridors | Simplified, not continuous corridor union |
| Sub-corridor/DP | Lowest-cost state chain | Corridor DAG | Optimal chain | Bellman recurrence | Medium | dynamic_programming | Approximation |
| Trajectory | Smooth longitudinal motion | DP chain | x,v,a,jerk | SciPy SLSQP, bounds and post-validation | Medium | optimize_trajectory | Approximation |
| Control | Execute plan | Next speed/lane | SUMO commands | setSpeed/changeLane + SUMO safety | Medium | simulation.py | Engineering adapter |
| Emergency | Handle infeasible graph | Empty full-horizon paths | Bounded braking | v_cmd=max(0,v+a_min dt_sim) | Low | emergency | Project policy, paper details unverified |
| Evaluation | Measure executed behavior | TraCI CSV | Metrics/plots | RMS, means, SD | Medium | simulation/experiments | Engineering evaluation |

## Extension selection

Relative ranks are project judgments, not a claim of global research novelty.

| Rank | Extension | Novelty potential | Difficulty | Hardware | Measurement | Panel suitability |
|---|---|---|---|---|---|---|
| 1 | Age-aware delayed/lost knowledge | Medium | Medium | Laptop | Clearance, age, arrival, delay sweep | Strong, directly testable |
| 2 | Explainable rejection reasons | Low-medium | Low | Laptop | Trace correctness | Strong supplement |
| 3 | Dynamic TTC risk score | Medium | Medium | Laptop | Conflict rate, false alarms | Needs calibrated threshold |
| 4 | Cooperative multi-vehicle planning | Medium-high | High | Laptop | Throughput and fairness | Too broad for initial scope |
| 5 | Learned conflict prediction | Medium | High | Laptop + labeled data | Prediction error and planner outcomes | Dataset burden |

Primary extension: delayed/lost knowledge with age-dependent occupancy expansion, bounded extrapolation and stale-data braking. No ML is required. Compare `kars` and `kars_delay` under identical packet streams. It may improve clearance while reducing arrival/speed. Results decide whether the tradeoff helps.

## Equations implemented

State s=(x,v,lane,t). Actions are sampled longitudinal accelerations and adjacent lane indices. Longitudinal point mass: x_next=x+v*dt+0.5*a*dt²; v_next=v+a*dt. Reject velocities outside configured bounds. Time advances by dt. Lane changes are abstract discrete decisions; lateral acceleration and jerk are not modeled. TraCI's actual lane movement remains under SUMO.

Offline produces permitted (v,a,v_next,dx) samples plus acceleration actions. Online reuses those actions at the measured continuous initial velocity, propagates them and merges only identical continuous states. Grid bins and the state cap discard some alternatives. This avoids treating a quantized representative as proof that a transition is feasible, but the graph is incomplete.

Restrictions check the entire longitudinal segment [x_previous,x_next]. Spatial removes any intersecting segment. Spatial+speed removes intersecting moves exceeding the cap. Spatial+temporal adds overlap with the active time interval. Spatial+temporal+speed adds both time overlap and cap. Solid markings remove lane changes within a marked segment. Adjacent-lane changes check both endpoint lane occupancies conservatively.

All descendants disconnected from the root are removed. A corridor is the ancestor subgraph of full-horizon endpoints sharing a lane. Its margin proxy is the minimum count of distinct x samples per layer, not the paper's spatial-margin equation. DP selects a sub-corridor chain using D(v)=min over parents u of D(u)+c(u,v). Cost penalizes distance from lane 1, speed deficit, acceleration squared and lane switching. Corridor score is DP cost minus 0.05 times margin proxy.

SLSQP minimizes 0.1*sum(a²)+0.3*sum(diff(a)²)+sum((x-x_DP)²). Bounds enforce configured acceleration, speed and +/-half position-grid distance from DP points. Every optimized segment is checked against traffic constraints. Failure restores the feasible DP trajectory. Lateral output consists of lane centers. This is not a continuous bicycle-model SQP path planner.

Age margin = safety_gap + uncertainty_growth*packet_age. Delayed vehicle occupancy includes constant-speed extrapolation and a conservative stationary lower bound. Age above stale_timeout commands braking. Uncertainty bounds are assumptions, not statistically calibrated probabilities.

Packet delivery is checked on simulation steps, so a nominal delay that is not a multiple of simulation_dt is rounded up to the next observation step. Occupancy uses the actual recorded age.

Emergency braking also activates for an observed all-lane blockage inside stopping distance plus the configured safety gap and 5 m margin. The emergency demo places the blockage beyond ideal stopping distance, allowing a visible stop and recovery. No policy can guarantee avoidance when a restriction first appears inside stopping distance.

Knowledge reaction time is the interval from the lead braking command to the first planning cycle consuming an observation with negative lead acceleration. It measures pipeline response, not causal physical ego braking latency. Independent constraints can already influence ego speed.

## Baselines and limitations

A* uses a priority queue on the same time-expanded graph, with admissible remaining-edge lower bound 0.01 per step. DP and A* must return the same cost without corridor scoring, tested explicitly. Basic RS receives physical occupancy but omits traffic-rule constraints, making it an ablation rather than an equally informed traffic-rule planner. SUMO safety mode 31 and lane-change mode 512 remain identical for all planners. Recorded safety combines planner and simulator behavior. Rule violation samples, arrival and requested emergency entries should be reported alongside collisions.

Constant-velocity traffic prediction, finite horizons, lane-level abstraction, conservative red persistence, grid truncation and virtual obstacles limit conclusions. Signal future colors are not guessed. Crossing is an advisory speed region and has no pedestrian simulation. Network is controlled, not imported city traffic. No full paper reproduction, real IoT hardware, real vehicle, Frenet baseline, CPU profiler or ML is claimed.

## Development / verification order

Environment → netconvert network → TraCI collection → ontology → RDF → SPARQL → point-mass propagation → offline transitions → online graph → adjustment → corridors → DP/A* → SLSQP → closed loop → emergency → comparisons → age-aware extension → evaluation → dashboard → tests → report and slides.

`pytest -q` verifies propagation, all four constraints, swept spatial checks, lane markings, SPARQL replacement, connected reachability, corridors, equal DP/A* costs, trajectory dynamics, emergency recovery, packet delay/loss and an actual SUMO closed-loop run. Integration success requires measured movement, zero reported collisions and nonzero SPARQL time, not final arrival in the short fixture.
