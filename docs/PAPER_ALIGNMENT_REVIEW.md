# Code relevance to the KARS paper

Review date: 12 October 2026. Paper: Chen et al., *Traffic-Knowledge-Augmented Path Planning for Autonomous Vehicles in Internet of Things*, IEEE Internet of Things Journal 12(23), 2025, DOI 10.1109/JIOT.2025.3613790. Reviewed the supplied 15-page PDF, including the algorithm equations, corridor figures and evaluation tables.

## Verdict and processing order

The project has the correct **high-level processing order** and a working closed-loop SUMO implementation. It is a **simplified, paper-inspired adaptation**, not a verified reproduction of the paper's mathematical reachable sets, geometric corridors or experimental results.

Actual order:

1. Read configuration and prepare the SUMO network, traffic and signal schedule.
2. Initialize sampled acceleration actions and the knowledge graph.
3. Advance SUMO and observe the ego vehicle and surrounding vehicles through TraCI.
4. Apply physical scenario events and simulate roadside communication.
5. Fuse current onboard observations with delivered remote observations.
6. Construct infrastructure constraints and predicted vehicle-occupancy constraints.
7. For KARS variants, serialize constraints into dynamic RDF and retrieve them with SPARQL. Baselines use direct Python constraints.
8. Generate future states from the current ego state and remove violating transitions.
9. Group full-horizon paths by ending lane and solve each group with DP or A*.
10. Select the lowest-scoring candidate, smooth its longitudinal trajectory with SLSQP, and validate the result.
11. Pass the first future speed/lane targets to the tracker. Apply braking overrides when required.
12. Execute bounded commands in SUMO, measure the result, save diagnostics and repeat.

Preparation occurs once; sensing/execution runs every 0.2 s by default. Planning normally runs every 1 s, with additional replans when delivered infrastructure restrictions change. A new vehicle observation does not automatically force an immediate replan.

## Component-by-component relevance

| Paper component | Current source | Assessment |
|---|---|---|
| IoT sensing, communication and knowledge layers (Section II, pp. 2-4) | `kars/communication.py`, `kars/simulation.py` | Simulated sensing and packet delay/loss/jitter/outage; no physical RSUs, PC5, MEC deployment or cloud network. Appropriate for simulation, but not a deployed IoT system. |
| Ontology and traffic knowledge extraction (Section II-B, Algorithm 1) | `knowledge_graph/ontology/traffic.ttl`, `kars/knowledge.py`, `knowledge_graph/queries/constraints.rq` | Actual RDF and SPARQL are implemented. Most operative constraints are first computed procedurally and then queried from dynamic RDF. Lane topology is stored, but no GeoSPARQL spatial reasoning or general ontology inference produces the constraints. |
| Vehicle dynamics (Eq. 11-14, p. 5) | `State`, `propagate()` in `kars/models.py`, `kars/reachable_set.py` | Constant-acceleration longitudinal dynamics align in spirit. The paper uses longitudinal/lateral position and velocity with acceleration bounds; this code uses longitudinal x/v and discrete lane intents with a lane-change hold timer. |
| Offline reachable sets and reusable transition matrix (Eq. 15-19, p. 5) | `offline_rs()`, `online_rs()` | Partial adaptation. A one-step integer-speed table is exported, but the online generator uses only its action list and rebuilds the graph from the measured state. It does not project a cached multi-step offline RS or reuse the paper's transition matrix. |
| Knowledge-based adjustment (Eq. 20-25, p. 6) | `violates()`, `rs_adjustment()` | All four spatial/time/speed categories are present, plus a marking constraint. Edges are removed using swept longitudinal intervals and occupied lanes; disconnected nodes are removed by forward reachability. These are point samples, not geometric sub-RS intersections. |
| Backward feasibility propagation (static experiment, p. 9) | `rs_adjustment()`, `corridors()` | Partial. Corridor extraction excludes nodes outside complete paths for candidate search, but the displayed adjusted graph can retain forward-reachable dead ends. There is no explicit geometric backward recursion matching the paper. |
| Driving corridors and spatial area score (Eq. 26, pp. 6-7) | `corridors()` in `kars/planning.py` | Major simplification. Candidates group ancestors of final-layer nodes by ending lane, so candidates can overlap. Margin is the minimum number of distinct sampled x positions per future layer, not the total 2D feasible area in the paper. |
| Sub-corridor cost and DP (Eq. 27-28, p. 7) | `edge_cost()`, `dynamic_programming()` | DP on a DAG is real. The cost uses center-lane distance, speed deficit squared, acceleration squared and lane-change penalty. It does not implement the paper's exact region-based efficiency/stability terms or cost-threshold merging of neighboring sub-RSs. |
| SQP trajectory generation (Eq. 29-31, p. 8) | `optimize_trajectory()` | SLSQP smooths longitudinal acceleration, acceleration changes and deviation from sampled positions. It enforces speed/acceleration and narrow position bounds, then rechecks constraints. It falls back to the discrete chain when smoothing fails. Bounds are not the paper's merged geometric sub-corridor bounds. |
| Failure detection / braking (Section III-B, p. 6) | `emergency()`, `TrajectoryTracker`, simulation overrides | Braking for no complete path and imminent all-lane blockage is implemented. Age-aware stale-data braking is a project extension. SUMO retains independent safety. There is no implemented human handover or vulnerable-road-user reasoning. |
| Static, semidynamic and dynamic validation (Section V, pp. 8-14) | `kars/scenarios.py`, `road_constraints()`, `kars/experiments.py` | The same scenario categories are represented, but this is a synthetic SUMO road. NGSIM scenario extraction, exact construction-size experiments and signal timing trials from the paper have not been reproduced. |
| Baselines and evaluation (Tables I-IV) | `Planner`, `experiments()`, `summarize()` | Basic RS, A*, KARS and age-aware KARS exist. Frenetix is absent. A* shares the sampled graph, constraints, objective and smoothing with KARS; it is a search ablation, not an independent geometric baseline. |

## Planner distinctions

| Method | Traffic knowledge | Vehicle prediction | Path search | Interpretation |
|---|---|---|---|---|
| `rs` | Direct spatial / spatial-temporal occupancy; omits planner speed and marking rules | Constant speed + fixed margin | DP | Knowledge ablation. SUMO still supplies rule/safety protections. |
| `astar` | Direct constraints, all implemented rule categories | Constant speed + fixed margin | A* | Search-method baseline on the same constrained graph. |
| `kars` | Dynamic RDF + SPARQL, all categories | Constant speed + fixed margin | DP | Main paper-inspired implementation. |
| `kars_delay` | RDF + SPARQL, all categories | Braking/constant-speed envelope + age margin | DP | Project extension for communication impairment and stale-data fallback. |

DP and A* can find the same minimum-cost chain on identical graphs. Changing RDF transport alone does not establish a trajectory-performance improvement when extracted constraints are identical. Compare knowledge coverage, prediction assumptions and search cost separately.

## Correctness fix and enhancements implemented in this update

- **Lane-change continuity fix:** replanning previously passed a positive hold timer without the original lane. It could forget source-lane occupancy during an active maneuver. `TrajectoryTracker.planning_state()` now carries the committed target, original lane and remaining hold into the planner, retaining both-lane reservations until measured completion or timeout. A regression test checks source/destination blockage and completion.
- **Actual planner diagnostics:** stage times for graph generation, adjustment, corridor extraction, search and smoothing; per-layer state counts; received/used constraints; rejection-source counts; solver, smoothing status and selected score. These are recorded in live and saved planning snapshots.
- **3D dashboard:** local WebGL road geometry from SUMO, measured vehicle dimensions/positions/headings, measured signal states, planned trajectory overlays, follow/chase/overview cameras, and vehicle inspection. Procedural buildings are scenery, not sensed infrastructure.
- **3D reachable graph:** longitudinal distance, lane and future time axes; raw/retained/selected states, valid edges, future-layer filtering and state inspection. Time height and lane spacing are visibly labelled as display scaling.
- **Planner detail pages:** explicit knowledge coverage, prediction assumptions, solver, fallback and paper relationship for all four methods.
- **Controlled comparisons:** only the newest completed result per planner with matching scenario, seed, duration, density, communications, substantive configuration, source hashes, input hashes and SUMO version is displayed. Missing results remain empty. No fictional benchmarks are inserted.

## Highest-value enhancements to add next

### Priority 1: close the main mathematical gaps

1. Implement a 2D point-mass state `(x, vx, y, vy)` with bounded longitudinal/lateral accelerations and polygonal or interval sub-RSs. Check whole vehicle footprints and continuous transitions, including junction conflicts. Validate lateral velocity, acceleration and clearance before treating a path as feasible.
2. Precompute a multi-step zero-initial-state reachable graph and transition relations; project it onto current initial states online. Compare generated states and transitions with an independently computed small reference case. Benchmark online time and memory against the current generator.
3. Extract connected drivable regions per layer, connect them over time, score the sum of their spatial areas (Eq. 26), then select sub-corridors using the paper's cost/merge process. Give SQP the resulting geometric bounds. Keep the current approximation as a separately named baseline.
4. Add backward viability pruning to identify every state with a feasible full-horizon continuation. Distinguish invalid transitions, unreachable states and forward-reachable dead ends in logs and visualizations.

### Priority 2: make evaluation defensible

5. Add an independent Frenetix or clearly labelled Frenet-sampling baseline and reproduce the construction-size experiments. Table I prints 6 x 3, 8 x 4.5 and 6 x 3 m for its small/medium/large labels; the repeated small/large dimensions need clarification before exact replication. Reproduce red-to-green delays of 1-6 s, green-to-red delays of 1-4 s and lead braking after 1-4 s. Keep supplied SUMO scenarios as separate experiments.
6. Import a documented NGSIM subset with its coordinate, time and vehicle mappings. Specify background traffic models and all conversions. The paper uses IDM/MOBIL for modified background scenarios; the current project should not claim that exact setting without implementing and verifying it.
7. Use matched repeated seeds, save complete settings and report distributions/confidence intervals for success, arrival, rule compliance, speed, acceleration RMS, peak jerk, minimum clearance, planning latency and deadline misses. Match prediction and sensing assumptions when isolating search methods.
8. Separate planner feasibility, actual execution and SUMO intervention metrics. Current `success` means arrived with zero recorded collisions; it does not require zero rule-violation samples. `rule_violations` counts samples, not distinct events. Add a strict compliant-success metric and contiguous violation episodes, plus counts of commanded motion curtailed by SUMO safeguards.
9. Store sensor provenance and timestamps per fact, not only aggregate packet age. Add calibration/noise experiments, stale constraint expiry and confidence bounds. Measure p50/p95/p99 planning times and sensor-to-command latency on the same hardware.

### Priority 3: improve knowledge and control

10. Derive constraints from lane slices, signs, shapes and signal entities using semantic/geometric queries rather than round-tripping precomputed constraints. Add SHACL validation and explicit unit/time semantics. Preserve immutable scene identifiers and provenance for replay.
11. Introduce tracking over the selected trajectory with lateral dynamics, adaptive replanning for critical vehicle changes and a validated emergency controller. Keep the existing SUMO controller as the reference implementation while measuring tracking error and safety interventions.
12. Add pedestrian/cyclist models and explicit priority/yield constraints only after collision checking supports their geometry. These classes and handover behavior are not currently implemented.

## Practical limits and verification

- Default prediction is 5 steps at 1 s, with 2 m / 1 m/s bins and at most 180 nodes per future layer. The paper's static/semidynamic experiments use 30 steps at 0.1 s with 1 m spatial squares; the dynamic signal experiment uses 60 steps. These settings are not equivalent.
- Graph bin collisions and node caps discard distinct continuous states. This is an under-sampled search and does not prove safety, completeness or existence of every possible trajectory.
- Planning is main-road/lane oriented. Crossing conflict handling also depends on SUMO; 3D rendering does not add 3D vehicle dynamics.
- Saved runs from earlier revisions do not acquire new diagnostics automatically. Rerun them under this revision before making matched comparisons.
- Validation: 44 Python regression/integration tests and 3 JavaScript cohort tests passed. All four planners completed matched 25-second, seed-101 smoke runs with zero recorded collisions; the basic RS run recorded 15 speed-rule violation samples. All ended at the duration limit, so this is not an arrival-success benchmark. The dashboard displayed all four as a matched cohort. Browser checks cover the 3D road, reachable graph and layer filter, planner pages, configuration, replay and responsive layout. Actual outcomes are recorded in `docs/.qa/` during development; use repeated full-length experiments for research conclusions.

## Run and evaluate

```powershell
cd D:\SUMO_MP\SUMO_KARS
.\sumo_env\Scripts\python.exe main.py serve
.\sumo_env\Scripts\python.exe -m pytest -q
.\sumo_env\Scripts\python.exe main.py experiments --repeats 15 --duration 250
```

Use the dashboard's **Planner methods** page to choose a method and **Compare planners** to select a completed reference run. Configure missing planners with the reference settings. The existing command-line experiment outputs remain available separately under `outputs/experiments/`.
