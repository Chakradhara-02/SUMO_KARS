# Roadster City V10 - start here

Open [START_HERE.md](START_HERE.md) for the imported Tesla Roadster, updated motion and City Mall parking. Extract the full project ZIP and double-click **Start_City.cmd**. The dashboard opens directly in city mode on port **8784**. Use **Enable sound** for optional driver alerts.

The sections below document the existing straight-road KARS experiments and older dashboard workflows.

# SUMO KARS simulation

## Start

```powershell
cd D:\SUMO_MP\SUMO_KARS
.\sumo_env\Scripts\python.exe main.py setup
.\sumo_env\Scripts\python.exe main.py serve
```

The console opens at http://127.0.0.1:8765. Click **Configure run**, choose a scenario and planner, then **Start simulation**. Runs use real-time playback by default. Change speed, pause, resume or stop using the controls.

You can also double-click `Start_Simulation.cmd`. Reopening it uses an already-running console.

- **3D road:** clean driving visualization with detailed vehicles, blue planned path and speed display. The default **Rear camera** follows behind the ego vehicle and tracks its heading. Follow ego, overview, orbit, pan and zoom are also available.
- **2D map:** switch to the measured overhead map at any time, including on browsers without WebGL. Both views support every scenario and planner, live runs and saved replays.
- Click the **lane change, acceleration, target speed or safe clearance** cards for short explanations and current measured/commanded values. Use the **â“˜** buttons in Configure run to explain each parameter.
- **Reachable regions:** raw grey and retained teal projections appear around the vehicle on the road in both views. The separate reachable-state plot has been removed. These strips summarize sampled future extents; they do not certify every point inside them as safe.
- **Sensor view:** shows the sensing boundary, observed-actor highlights and onboard/IoT links. Blue links are onboard observations; purple links are delivered remote observations. The model uses simulated TraCI sensing, not a camera/lidar detector.
- **Live explainable workspace:** click Sense & fuse â†’ Ontology â†’ Knowledge graph â†’ SPARQL â†’ Reachable regions â†’ Search â†’ Execution. Each stage explains its role and shows recorded data, RDF relationships, actual query/results, pruning and commands. A* marks RDF/SPARQL stages as bypassed.
- Scenario events appear in the driving view; active infrastructure restrictions have road shading and signs. Motion uses buffered measured-frame interpolation (about 650 ms display latency), with smooth heading-aware rear-camera following. The numeric telemetry reports the latest frame.
- Click a vehicle to inspect its measured state.
- Inspect reachable states, feasible corridors, RDF/SPARQL timing and constraints.
- **Planner methods:** KARS and A* are the two selectable dashboard planners. Legacy methods remain available through the command line and saved-run history.
- **Compare planners:** select a reference run; only completed results with matching settings, code, inputs and SUMO version appear. Configure missing planners with its settings. A single seed is descriptive.
- New runs record stage timings, constraint coverage, graph counts, solver, smoothing status and rejection reasons. Older runs show available data and request a rerun for missing diagnostics.
- Saved runs support time scrubbing, replay and ZIP export.
- Optional **native SUMO GUI** follows the ego vehicle.
- Refreshing the page or restarting the console preserves saved runs and recovers an active process.

Braking fixes: fractional speeds can stop without reversing; known same-lane followers cannot block forward escape through inflated predicted margins, while their occupancy still guards lane transitions. When the full horizon is unavailable, a valid slower prefix is executed and replanned. Immediate failure or an active all-lane obstacle still requests bounded emergency braking, with its recorded reason available by clicking the status banner. The legacy age-aware method uses a local-visibility speed cap for stale messages instead of treating missing packets alone as an emergency. SUMO retains independent following and collision safeguards.

New runs are required to see recorded sensor, RDF/query and braking-reason details; older replays retain their original outputs.

## Command-line simulation

```powershell
# Combined traffic with physical roadworks and continuous lane changes
.\sumo_env\Scripts\python.exe main.py run --scenario demo --algorithm kars_delay --gui --realtime 1 --duration 250

# Emergency barriers appear at 8 s and clear at 18 s
.\sumo_env\Scripts\python.exe main.py run --scenario emergency --gui --realtime 1

# Delays, loss, variable latency and a 30â€“40 s communication outage
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
| `semi_dynamic` | Stationary maintenance truck in lane 0; lane-1 obstruction from 10â€“80 s |
| `dynamic` | Lead car merges and brakes at 12 s, stops at 16 s, resumes at 22 s |
| `emergency` | Three stationary physical vehicles block the road from 8â€“18 s |
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

SUMO binaries are discovered from the parent `bin` folder, `SUMO_HOME`, PATH or the installed `eclipse-sumo` package. The console requires no Node build, internet access or image API. Three.js 0.186.1 is bundled locally under the MIT license; WebGL support is needed for 3D rendering. The supplied `app.bundle.js` is ready to run.

The supplied KARS paper has now been reviewed against the code. Read [the code-to-paper mapping and enhancement priorities](docs/PAPER_ALIGNMENT_REVIEW.md). The overall sequence aligns with the paper, while lane dynamics, offline reuse, corridor scoring and evaluation are simplified. Frenetix and NGSIM reproduction are not implemented. IoT is simulated; SUMO supplies longitudinal traffic physics, gradual lateral movement and independent safety. The sampled planner is not a formal collision-avoidance proof. The 3D view displays measured states and planned data; scenery is drawn in code.

## Dashboard development

Edit `simulation_ui/app.js`, `scene3d.js`, `planners.js`, `index.html` and `style.css`. After JavaScript changes, rebuild both committed browser bundles (Node.js/npx is needed for development):

```powershell
python tools/build_frontend.py
node --test tests/planner_comparison.test.mjs tests/motion.test.mjs
```

Reload the page after changes. Restart the server after Python backend changes. Three.js files and license are in `simulation_ui/vendor/`. Runtime traffic data and scenery load locally without a CDN.

## City map and destination routing

Open `http://127.0.0.1:8765/?view=city` or select **City map** in the sidebar. Choose a named starting point and destination, set **Traffic vehicles** (20â€“600; default 180), then press **Drive to destination**. Green marks the start; orange marks the destination. The route appears in both 2D and 3D, with an overview camera and a city minimap. The city has 25 junctions, 80 directed street segments, two lanes in each direction, and nine signalized intersections. Traffic is replenished as vehicles finish their routes and includes cars, buses, trucks and a braking event.

City mode uses SUMO route finding, signal/right-of-way controls and car following. The KARS/A* reachable-state experiments remain on the original straight-road scenarios. City runs retain their route, measured traffic, trace, telemetry and trip information for replay and export.

Example: `python main.py run --scenario city --algorithm city --city-start n0_0 --city-destination n4_4 --city-vehicles 180 --duration 300 --no-plots`.

The updated city is an Indian-style synthetic street grid with **left-hand traffic**, black/yellow kerbs, yellow centre lines, zebra crossings and curbside signal gantries. Car, bus, truck, auto-rickshaw and motorcycle types share the roads. SUMO uses SL2015 lateral dynamics with bounded lateral acceleration and zero lateral speed at standstill; the viewer turns the vehicle body along an interpolated steering curve between observed positions. Large destination spheres have been replaced with ground markers.

City views show the measured ego trail (orange), a road-aligned feasible trajectory preview (blue) and reachable-state samples (green; unfiltered samples in grey). The five-second preview uses the actual lane/turn geometry, speed limits, signal schedules and constant-speed projections of observed vehicles, with 0.2-second swept collision checks. These sampled visualizations are separate from SUMO's executed city-driving controls. Old city replays retain their original right-hand network; start a new city run for the Indian-style layout and recorded reachability.
