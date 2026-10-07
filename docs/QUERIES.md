# SPARQL examples

Planner executes `constraints.rq` each planning cycle. The other ten files illustrate individual queries against the saved dynamic.ttl. Nearby vehicles uses longitudinal distance only, so cross-road vehicles must be filtered by road in production. Pedestrian crossing is an advisory region, not a moving pedestrian.

- `speed_limit.rq`: speed limit, using actual stored RDF properties.
- `current_lane.rq`: current lane, using actual stored RDF properties.
- `nearby_vehicles.rq`: nearby vehicles, using actual stored RDF properties.
- `traffic_light.rq`: traffic light, using actual stored RDF properties.
- `upcoming_obstacle.rq`: upcoming obstacle, using actual stored RDF properties.
- `pedestrian_crossing.rq`: pedestrian crossing, using actual stored RDF properties.
- `road_block.rq`: road block, using actual stored RDF properties.
- `allowed_speed.rq`: allowed speed, using actual stored RDF properties.
- `temporal_restriction.rq`: temporal restriction, using actual stored RDF properties.
- `spatial_restriction.rq`: spatial restriction, using actual stored RDF properties.

Example execution:
```python
from rdflib import Graph
g = Graph().parse("outputs/demo_kars_delay_seed1/dynamic.ttl")
print(list(g.query(open("knowledge_graph/queries/current_lane.rq").read())))
```
