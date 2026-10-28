# Reachable sets and trajectory predictions

The city visualization combines a precomputed offline sampled envelope with online sampled reachable-set prediction. Starting from the currently displayed ego state, a kinematic bicycle model integrates acceleration and steering controls to produce possible future vehicle positions over 3 seconds. Both layers are finite sampled approximations, not complete continuous safety certificates.

| View | Reachability computation |
| --- | --- |
| City | Offline motion-library lookup plus online bicycle rollouts, traffic filtering and sampled trajectory optimization |
| Straight-road KARS | Reusable offline acceleration/lane transition templates, online state expansion and constraint pruning |

The former near-car rectangle was a swept-footprint clearance overlay. It has been replaced by a trajectory fan: gray candidate paths, pale-green feasible sampled positions, light-red rejected states, and a blue optimized prediction. Candidates spread left and right as road space and dynamics permit. A moving forward vehicle does not instantly gain reverse states. Backing motion, reverse gear at rest, and an uncommitted stop receive reverse candidates as appropriate.

There are 39 forward control/profile candidates. The model bounds acceleration, jerk, steering rate and lateral acceleration. Both constant-turn and countersteering lane-change profiles are sampled. Vehicle footprints must remain supported by the road on the same elevation; signal stop lines and oriented swept collision checks truncate invalid branches. Traffic prediction assumes constant speed and heading over the short horizon.

The blue prediction minimizes a sampled objective balancing route progress, route deviation, vehicle clearance, acceleration and lateral comfort. The initial choice is the lowest-cost fully feasible candidate among the samples. Subsequent updates retain the current feasible control profile when its cost is within a small tolerance of the best candidate, reducing path flicker. An invalid incumbent is never retained. If none spans the full horizon, only a checked braking prefix is shown. An optimized predicted lane-change can avoid a stopped vehicle when space and dynamics permit. SUMO independently executes city driving; this predictor does not replace its vehicle controller.

Rendering and collision predictions use the same buffered actors as the visible car, so all branches originate at the displayed pose. The 2D and 3D views use the same model. The top-right hazard panel appears only for vehicle-conflict branches and clears when the blocker disappears. The UI explicitly labels the model Online RS.

The earlier ego signal-priority change remains: within 60 metres, a red request schedules ego's protected green within 15 seconds while retaining 3-second yellow and 6-second clearance. Traffic queues may still prevent motion after green. This is not a 15-second red limit on every approach.

Validation: dynamics, both-sided fan geometry, current-pose anchoring, road support, red-signal stopping, candidate cost selection, countersteering, obstacle avoidance and reverse-parking restrictions are covered by JavaScript tests. A headless Chrome fixture checks the displayed fan and corner warnings without modifying live runs; its screenshot and report are in artifacts/local_envelope_qa/.


## Offline points and reverse motion

The offline library is generated before browser runtime with `python tools/build_offline_reachability.py`. It contains 1,638 branches across 42 direction/speed/acceleration bins for the supplied 4.7 m vehicle. At runtime, the nearest speed and acceleration bin is selected and its precomputed geometry is rotated and translated to the displayed ego pose. The stored offline library is independent of roads, vehicles and signals. Its displayed projection is checked against the current environment: only valid prefixes remain lavender. The first invalid state is red and later descendants are omitted. The original unfiltered geometry remains available as source data; it is not drawn past a rejection. Use the Offline points toggle to compare the projected library with the online layer. The source table is `simulation_ui/offline-reachability.json`.

Reverse is recognized from negative signed velocity or reverse gear at rest. A stopped, uncommitted vehicle can display both direction envelopes; a moving forward vehicle never acquires an instant reverse branch. Explicit drive gear stays forward and park/completed parking has no moving envelope. Reverse states retain body orientation, use signed negative speeds, and undergo the same online rear-obstacle and road checks. Displayed reverse rays track the rear bumper so they appear behind the car rather than underneath its body. The reverse chase camera widens to keep the rear fan in view. Parking motion and city actuation remain SUMO-controlled.


## Selected reachable point and parking consistency

Every online candidate now has a branch ID, sample IDs and parent IDs. The chosen endpoint is explicitly a feasible sample in that candidate, and the blue trajectory is its checked parent chain. A larger blue marker identifies that selected reachable endpoint in both views. The renderer no longer replaces it with unrelated full parking geometry.

During parking, candidates follow the controller's committed remaining manoeuvre with alternative bounded speed profiles. The path is projected from the displayed ego pose using position, gear and heading. Swept footprints are checked against lot bounds, occupied bays and current traffic. The selected feasible parking profile supplies the online samples, blue trajectory and selected endpoint together. The native snapshot includes a local remaining-path window and preserves the exact final bay target. A missing parking path produces a hold candidate; it does not invent independent moving rays. Old full-path blue parking overlays and driving-route guide lines are suppressed during parking.


## Shared validation of offline projections and online states

Both layers now use the same swept-footprint validator. It checks permitted carriageway support, road elevation, parking bounds, predicted vehicle occupancy, speed limits and signal timing. Red points retain their rejection kind and reason for road boundaries, opposing carriageways, parking boundaries, red/amber stop lines, expiring green phases, speed limits and vehicle conflicts. Rejection samples are not removed silently and cannot become selected trajectory states. Hovering the reachability summary lists reasons and counts. The corner panel remains reserved for vehicle conflicts so routine boundary pruning does not cover the view with alerts.

The visible offline layer is labeled Offline projection rather than unfiltered: no lavender branches continue beyond the first invalid state. Source library lookup and precomputed geometry are unchanged, while `offlineRaw` preserves the original transformed samples for inspection. Forward, reverse and parking all share the validator. Red states from the offline projection are hidden when that layer is toggled off; online rejections remain visible.


## Scheduling and trajectory continuity

Online expansion and offline projection run together in a dedicated background worker, at most eight searches per second with one outstanding request. Paused unchanged scenes reuse their result. Hidden views skip searches; hidden offline points skip offline projection. Both renderers consume the same result. Road segments use a cached spatial grid and vehicle footprints use precomputed collision geometry with an exact oriented-box narrow phase. Swept sampling density is unchanged.

Between results, the blue trajectory is trimmed to the current displayed ego position. Passed points are discarded. A current-state validation guard hides a prediction invalidated by new traffic and requests a fresh search. No unchecked spatial spline is added across obstacles. Static road surfaces are batched, point buffers upload only for new results, and rendering resolution adapts to sustained frame load. See PERFORMANCE.md for measured search timings and limits.


## Worker loading compatibility fix

The planner worker source is now embedded as text in the built app bundle and started with a Blob URL. The calculation still runs off the UI thread. Loading no longer depends on the running Python server knowing the new worker-file URL: the old static whitelist returned 404 and caused Reachability preview unavailable. A hard browser refresh is sufficient when the existing server already serves the project app bundle. Both bundles must still be rebuilt with `python tools/build_frontend.py`, which embeds the freshly generated worker into the app.

The browser regression deliberately returns 404 for the worker-file URL and verifies visible green online points, red rejections, offline toggles, reverse directions and the selected parking endpoint. The blue endpoint marker updates every displayed frame even when point-cloud buffers reuse the last worker result.
