# Final project state

Implementation lives entirely in SUMO_KARS. Existing SUMO installation is reused. Verified with Python 3.14.2, SUMO/TraCI 1.27.1 and the versions recorded in requirements-lock.txt.

| Phase | Completed work | Verification / output |
|---|---|---|
| 1 Environment | Python packages and SUMO discovery | pip check passes |
| 2 SUMO | Three-lane approach and signal intersection | netconvert succeeds, GUI smoke passes |
| 3 TraCI | Measured states and vehicle control | Live integration tests |
| 4 Traffic data | CSV + real-time observations | ego.csv, traffic.csv |
| 5 Ontology | RDF/OWL project schema | traffic.ttl parses |
| 6 Knowledge graph | Static lanes + cycle-specific dynamic RDF | static.ttl, dynamic.ttl |
| 7 SPARQL | Actual planner query + ten examples | Every query executes in tests |
| 8 Dynamics | Point-mass propagation and bounds | Dynamics tests |
| 9 Offline RS | Reusable actions and transition table | offline_transitions.json |
| 10 Online RS | Time-layer state graph | DAG and transition consistency tests |
| 11 Adjustment | Four restrictions + lane markings | Pruning tests and category plots |
| 12 Corridors | Terminal-lane connected candidate subgraphs | Selected/rejected plots |
| 13 DP | Optimal graph chain and cost | DP/A* cost equivalence |
| 14 Trajectory | SLSQP smoothing + validated fallback | Trajectory dynamics tests |
| 15 Closed loop | Observe, query, plan, control, repeat | Full demo arrives without collision/rule violations |
| 16 Emergency | Braking, stop, recovery | Emergency integration test and full demo |
| 17 Baselines | Genuine A* and basic RS ablation | Shared model and simulator safety settings |
| 18 Experiments | Four scenarios, four planners, three seeds | 48 completed runs |
| 19 Extension | Age-aware occupancy and stale-data braking | 72 delay/density sweep runs |
| 20 Evaluation | Safety, efficiency, comfort and timing | CSV means/SD, measured report tables |
| 21 Dashboard | Start/pause/resume/reset + live results | AppTest loads and controls verified |
| 22 Tests | Unit, live integration and dashboard tests | 21 passed |
| 23 Documentation | README, report, diagrams, methodology, team | docs/ and README.md |
| 24 Presentation/viva | 20 slides, notes and 107 Q&A | Validated PPTX and visually checked slides |

Final artifacts: outputs/demo_kars_delay_seed1/demo.gif, plots and measured CSV/JSON; outputs/experiments/ and outputs/sweep/; docs/presentation/SUMO_KARS_Project.pptx; docs/RESULTS.md.

Scope boundaries: project-level approximations, simulated IoT, virtual restriction polygons, discrete lane control, no moving pedestrian, no ML/Frenet baseline, no full paper reproduction. The paper PDF was not supplied. SUMO safety remains enabled, and timings depend on machine workload. These limitations are documented and apply to interpretation of results.
