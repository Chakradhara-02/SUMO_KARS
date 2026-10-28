# Roadster City V10

1. Extract the complete ZIP. Stop the terminal running an older release.
2. Double-click **Start_City.cmd** inside the extracted folder; keep its terminal open.
3. Open http://127.0.0.1:8784/?view=city and refresh with Ctrl+F5. Port 8778 is the previous release.
4. Choose a start and **City Mall** as the destination. Select an empty bay, then click **Drive to destination**. Grey occupied bays cannot be selected.
5. Leave the mall bay unselected to choose later: the car waits at the parking entrance until you select an empty bay in the parking panel.
6. Use **Rear camera**, **Fullscreen**, **Route overlay** and **Reachable points**. Click **Enable sound** for optional indicator ticks, ADAS tones and the completion chime.

Alternatively, open a terminal in the extracted folder and run `python launch_city.py`. Install missing dependencies with `python -m pip install -r requirements.txt`.

## Changes

- Your supplied Tesla Roadster replaces the procedural coupe. The driving asset has 43,994 triangles and is about 2 MB; the parked detail asset has 120,996 triangles and is about 7 MB. Both keep the source texture and proportions. New journeys use a 4.7 m by 2.05 m physical envelope.
- Turning interpolation preserves position velocity, heading and angular-speed continuity across incoming frames, including unequal sample intervals. Front wheels steer around local axle pivots with Ackermann angles; wheel spin follows signed measured distance, including reversing. Small damped body pitch and roll provide feedback without changing SUMO driving states. Native junction turns retain detailed curves and a lower turn-speed limit.
- Ten parking loops connect through mid-block priority driveways. They have no separate traffic lights; normal traffic lights remain at the 25 main junctions. Start a new journey for this network.
- White lane separators, edge lines and yellow center lines remain visible on roads near parking access, including ramps and expressways.
- Colorful buildings and City Mall have names fixed to their facades. The 2D map now shows parking surfaces, occupied cars, bays and named buildings too.
- After parking, the detailed Roadster presentation opens. Drag to orbit, or use Rotate view and Reset view. Use minus to minimize, cross to close, and Show parking to restore it. The supplied body is a fused mesh without separate doors, bonnet or boot, so those panels cannot open on this asset.
- Reachable samples use visible screen-sized dots with their lane elevations. Forecasts refresh at lane transitions. A lack of feasible samples remains explicit, while the blue navigation route stays available independently.
- Rendering caches road elevations, limits detailed traffic and throttles minimap painting. Parking graphics stop rendering after closing their panel.

## Does traffic change the route?

Yes. City mode uses a connected weighted shortest-path graph and assesses up to three alternatives. Its score combines observed edge travel time, queue delay, distance and junction delay. It checks again every eight simulated seconds when enough road remains to change route safely, and uses a minimum benefit threshold to avoid oscillation. SUMO applies the selected route; lane and junction collision controls remain active.

The native Central Chowk to Government Hospital check placed 12 stopped vehicles on the original route. The planner selected a route about 95 metres longer with a lower traffic-and-distance cost, and SUMO accepted the replacement route. A quieter detour can be preferable to the geometrically shortest route.

City routing and sampled reachable previews are separate from the repository's straight-road RDF/SPARQL KARS experiments. Green dots represent feasible sampled forecasts, not every point in a continuously safe region.

## Validation

See `docs/VALIDATION_V10.json` for Roadster-specific results and `docs/ROADSTER_ASSET.md` for asset details. The older `docs/VALIDATION_V9.json` records the previous network, congestion-routing and regression checks; those are historical results. Frame rate still depends on the computer and browser; audible output needs checking on your speakers.

## Update your collaborative Git checkout

The extracted folder runs independently. To transfer it into `C:\Users\vivek\SUMO_KARS`, stop the old server and run `python apply_to_git.py` from the extracted release folder. It checks conflicting edits and creates backups. It does not commit or push; review `git diff` before committing. If it reports conflicting edits, merge those files first.

Start a **new journey** to use the Roadster's wider physical envelope and axle metadata. Older replays retain their recorded dimensions and network; their visual model is scaled to fit that envelope.
