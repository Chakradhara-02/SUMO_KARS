# Supplied Roadster asset

Source: the user-supplied `tesla-roadtser-2026.zip`, containing `source/tesla roadtser 2026.glb`. The model name is supplied by the user; it is not a claim about a released vehicle's specifications. The archive contains no separate license text.

The original GLB contains 500,000 triangles, one combined mesh and a baked texture. Offline meshoptimizer simplification produces a 43,994-triangle driving model (2,093,460 bytes) and a 120,996-triangle parked model (6,985,456 bytes). The driving texture is 1024 pixels; the parked texture is 2048 pixels. Embedded textures keep runtime loading local. `simulation_ui/assets/roadster-info.json` records dimensions, source hash, part counts and simplification errors. The original 28 MB GLB is not needed at runtime.

Both models preserve proportions and use a 4.7 m length, approximately 2.045 m width, 1.243 m height and 2.875 m wheelbase. New SUMO journeys use a 2.05 m vehicle width. These are simulation dimensions, not manufacturer specifications.

The rear wheels were disconnected components. Front tire regions were isolated from the fused body. Each wheel has its own centered pivot; steering and spin use separate parent groups. Ackermann angles turn the inside front wheel more than the outside wheel. Spin follows signed measured travel, so reversing changes rotation direction and replay speed does not change distance per rotation. The remaining body has no separate hinged doors, bonnet or boot. The parked view offers orbit, automatic rotation and camera reset instead.

Rendering interpolates measured rear-axle positions with shared monotone velocity tangents and measured heading with continuous angular velocity. It does not extrapolate past the latest received state. Parking uses the existing bounded kinematic forward/reverse controller through TraCI; ordinary road movement uses SUMO. Visual smoothing does not certify that native acceleration or jerk is always comfortable.

Only the ego uses this detailed asset. Nearby traffic keeps the existing limited-detail models and distant instancing. Browser checks establish correct loading and controls on this machine; they do not guarantee a frame rate on every computer.

Three.js and its GLTFLoader utilities retain their MIT license in `simulation_ui/vendor`. Meshoptimizer was used offline and is not a runtime dependency.
