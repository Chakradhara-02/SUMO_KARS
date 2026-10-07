# Four-student responsibilities

| Member | Tasks / algorithms | Files | Deliverables | Dependencies | Presentation |
|---|---|---|---|---|---|
| 1 | SUMO network, traffic, events, TraCI control | sumo/, sumo_setup.py, simulation.py | Verified moving ego, traffic CSV, scenario demos | Environment | Simulation and IoT acquisition |
| 2 | Ontology, RDF updates, SPARQL, packet semantics | knowledge_graph/, knowledge.py, communication.py | Static/dynamic TTL, constraint queries, age traces | Member 1 observations | Knowledge representation and communication |
| 3 | Point-mass RS, pruning, corridors, DP, A*, SLSQP | reachable_set.py, planning.py | Feasible chains, optimization, emergency tests | Member 2 restrictions | Mathematical model and algorithms |
| 4 | Repeats, metrics, plots, dashboard, report | experiments.py, visualization.py, dashboard.py, docs/ | Mean/SD comparisons, sweep, panel demo | Members 1–3 | Extension results and limitations |

ML is not assigned as implemented work because the selected extension needs no trained model. Each student should run the full integration test and understand the SUMO safety limitation.
