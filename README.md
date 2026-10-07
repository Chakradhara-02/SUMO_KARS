# SUMO KARS simulation

## Start

```powershell
cd D:\SUMO_MP\SUMO_KARS
.\sumo_env\Scripts\python.exe main.py setup
.\sumo_env\Scripts\python.exe main.py serve
```

The console opens at http://127.0.0.1:8765. Click **Configure run**, choose a scenario and planner, then **Start simulation**. Runs use real-time playback by default. Change speed, pause, resume or stop using the controls.

You can also double-click `Start_Simulation.cmd`. Reopening it uses an already-running console.

- Follow ego / overview; scroll to zoom and drag to pan.
- Click a vehicle to inspect its measured state.
- Inspect reachable states, feasible corridors, RDF/SPARQL timing and constraints.
- Saved runs support time scrubbing, replay and ZIP export.
- Optional **native SUMO GUI** follows the ego vehicle.
- Refreshing the page or restarting the console preserves saved runs and recovers an active process.

## Command-line simulation

```powershell
# Combined traffic with physical roadworks and continuous lane changes
.\sumo_env\Scripts\python.exe main.py run --scenario demo --algorithm kars_delay --gui --realtime 1 --duration 250

# Emergency barriers appear at 8 s and clear at 18 s
.\sumo_env\Scripts\python.exe main.py run --scenario emergency --gui --realtime 1

# Delays, loss, variable latency and a 30–40 s communication outage
.\sumo_env\Scripts\python.exe main.py run --scenario iot_delay --delay 1 --loss 0.15 --jitter 0.5 --outage 30 40 --gui --realtime 1 --duration 250

# Headless run; larger insertion period means lighter traffic
.\sumo_env\Scripts\python.exe main.py run --scenario semi_dynamic --density 15 --duration 250

# Change local sensor range
.\sumo_env\Scripts\python.exe main.py run --scenario dynamic --sensor-range 80

# Tests
.\sumo_env\Scripts\python.exe -m pytest -q

# Compare planners / communication and density sweep
.\sumo_env\Scripts\python.exe main.py experiments --repeats 3 --duration 250
.\sumo_env\Scripts\python.exe main.py sweep --repeats 3 --duration 250
```

`--realtime 0` runs as fast as possible. Console port: `main.py serve --port 8766`. Prevent automatic browser opening: `--no-browser`.

## Scenarios

| Scenario | Traffic behavior |
|---|---|
| `static` | Main road, crossing traffic, signal phases and speed rules |
| `semi_dynamic` | Stationary maintenance truck in lane 0; lane-1 obstruction from 10–80 s |
| `dynamic` | Lead car merges and brakes at 12 s, stops at 16 s, resumes at 22 s |
| `emergency` | Three stationary physical vehicles block the road from 8–18 s |
| `iot_delay` | Roadworks and braking plus configurable communication impairments |
| `demo` | Combined traffic, including an upcoming speed-limit update at 18 s |

Barriers are actual SUMO vehicles, sensed with their real dimensions. They also affect surrounding traffic. Lane changes take 2.5 seconds, and the planner reserves both source and destination lanes during a maneuver. Current onboard observations override older IoT observations; signal constraints use the actual static phase schedule. Late out-of-order messages cannot replace newer observations. Age-aware planning brakes when roadside information becomes stale.

Planners: `kars` uses RDF/SPARQL constraints; `kars_delay` adds braking envelopes and age uncertainty; `astar` searches the same constrained graph without RDF; `rs` omits traffic-rule pruning. All retain SUMO safety controls.

## Saved data

Console runs: `outputs/runs/<timestamp_id>/`. CLI runs: `outputs/<scenario>_<algorithm>_seed<N>/` or `--output <folder>`.

- `manifest.json`: exact parameters, seed, config hash, runtime and lifecycle provenance.
- `ego.csv`, `traffic.csv`: measured position, velocity, acceleration, lateral motion and dimensions.
- `trace.jsonl`: streaming measured frames for replay, even after interruption.
- `plans.json`, `live.json`: RS, selected chain, corridors, trajectory and live telemetry.
- `metrics.json`: arrival, collisions, rule violations, clearance, TTC, comfort and timing.
- `timeline.json`, `events.json`: traffic events and sensor reaction times.
- `lane_changes.xml`, `tripinfo.xml`: native SUMO output.
- `static.ttl`, `dynamic.ttl`: actual RDF snapshots; PNG charts after completion.
- `status.json`, `run.log`, `error.log`: lifecycle and diagnostics.

Short runs may end before arrival. Runs from the earlier implementation remain in their original folders; rerun comparisons to evaluate the updated physical scenarios.

## Install on another laptop

Python 3.12+:

```powershell
cd D:\SUMO_MP\SUMO_KARS
py -3 -m venv sumo_env
.\sumo_env\Scripts\python.exe -m pip install -r requirements.txt
.\sumo_env\Scripts\python.exe main.py setup
.\sumo_env\Scripts\python.exe main.py serve
```

SUMO binaries are discovered from the parent `bin` folder, `SUMO_HOME`, PATH or the installed `eclipse-sumo` package. The console requires no Node build, internet access or image API.

This is an implemented lane-level simulation inspired by KARS, not a verified reproduction of a paper whose PDF was not supplied. IoT is simulated; SUMO supplies longitudinal traffic physics, gradual lateral movement and independent safety. The sampled planner is not a full steering/bicycle controller or a formal collision-avoidance proof. Map scenery is drawn in code; graphs and actor motion come from simulation data.
