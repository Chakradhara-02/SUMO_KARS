# Reachability and rendering performance

The planner runs in a dedicated Web Worker with at most eight searches per second and one outstanding job. Worker code is embedded in the app payload and started with a Blob URL, so an older running dashboard does not need a new static route. The map is transferred once per network. Paused unchanged scenes reuse results; hidden views skip work, and disabling Offline points skips offline projection. The UI and 3D renderer share results.

Collision checks precompute vehicle dimensions, axes and predicted velocities. A squared-distance broad phase precedes exact oriented-box collision tests. Road support queries use a cached 20 m spatial grid. The candidate count and swept-footprint sample density are preserved.

## Controlled measurements

Local Node.js benchmarks, 15 warmup and 60 measured searches:

| Fixture | Before median / p95 | After median / p95 |
| --- | --- | --- |
| Two-lane map, 600 actors | 42.74 / 97.52 ms | 6.92 / 9.85 ms |
| Native city map, 947 lanes, 21 actors | 212.51 / 263.91 ms | 33.14 / 46.68 ms |

The native-map comparison isolates the road-grid change after the collision optimization. Synthetic safe and offline point counts are unchanged (519 and 475). Measurements vary with machine load. Reproduce with `node tools/benchmark_reachability.mjs`; JSON captures are under artifacts/performance/.

These are search timings, not whole-application frame rates. Headless Chrome used software rendering; its frame timings do not establish hardware GPU performance.

## Rendering and continuity

Immutable opaque road surfaces are merged by material and spatial tile to reduce draw calls while preserving spatial culling. Existing box instancing remains. Reachability point and line buffers update only for new results. Dashboard indicators update at 10 Hz. Sustained slow rendering gradually lowers pixel resolution, then recovers it after load drops.

Trajectory selection retains a feasible incumbent within a small cost tolerance, preventing insignificant score changes from switching branches. Each displayed blue path starts at the current ego pose and discards passed samples. A current-traffic guard suppresses invalid old paths. Geometry is never visually smoothed through unchecked obstacles. This improves the predicted trajectory; SUMO remains responsible for executing city driving and parking.

Validation: 90 JavaScript tests passed, including collision parity across 500 deterministic cases, scheduling, stale results, hidden layers, path trimming, selection stability, adaptive rendering and surface batching. Browser checks passed for nearby blocked points and warning removal, offline toggling, reverse direction, and the selected parking endpoint, with no JavaScript exceptions.

Rebuild both UI and worker after source changes: `python tools/build_frontend.py`.
