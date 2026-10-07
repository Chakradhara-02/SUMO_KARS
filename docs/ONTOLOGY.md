# Ontology and runtime knowledge

Namespace: `https://sumo-kars.local/traffic#`. The ontology is a project schema. Its exact equivalence to the paper is unverified. RDFLib stores explicit RDF/OWL declarations and facts; no OWL reasoner runs.

| Class | Meaning in this project |
|---|---|
| Vehicle | Observed surrounding traffic entity |
| EgoVehicle | Vehicle controlled by the planner, also a Vehicle |
| Road | SUMO road edge |
| Lane | SUMO lane with shape, speed and adjacency |
| LaneSlice | Schema concept for a portion of a lane; discretized states currently represent slices implicitly |
| TrafficLight | Signal entity with observed color |
| TrafficSignal | General schema concept for a signal; active signals use TrafficLight |
| Intersection | Junction associated with traffic control |
| SpeedLimitZone | Region with a configured speed cap |
| RoadBlock | Forbidden planning region |
| ConstructionZone | Specialized RoadBlock |
| PedCrossing | Advisory crossing region; no pedestrian actor is simulated |
| LaneMarking | Marking restricting lane switching |
| Constraint | Runtime restriction with kind, region, lane, speed and time bounds |

| Relationship / property | Meaning |
|---|---|
| locatedAt | Vehicle references its actual SUMO lane identifier |
| hasSpeed | Measured speed in m/s |
| hasNextLane | Connection to a following lane from the SUMO network |
| hasPreviousLane | Inverse predecessor relation |
| hasLeftLane | Adjacent higher-index lane |
| hasRightLane | Adjacent lower-index lane |
| hasShape | SUMO polyline or explanatory zone description |
| isOn | Lane belongs to a road |
| controlledBy | Intersection references its signal |
| controls | Signal references its controlled junction |
| hasCurrentColor | Observed signal color |
| hasFutureColor | Schema property only; future colors are not invented |
| hasSpeedLimit | Static lane or zone speed cap |
| hasType | Marking type |

Static graph: ontology, template road descriptions, actual lane shapes, speed limits, adjacency and lane connections imported from road.net.xml. Dynamic graph: delivered vehicle states, current traffic signal observations, snapshot timestamp and currently received restrictions. Dynamic triples are replaced each planning cycle so old vehicle states do not accumulate.

Example runtime triples:

```turtle
@prefix k: <https://sumo-kars.local/traffic#> .
k:ego a k:EgoVehicle, k:Vehicle;
  k:locatedAt k:in_1;
  k:hasSpeed 8.0;
  k:timestamp 1.0 .
k:in_1 a k:Lane;
  k:hasLeftLane k:in_2;
  k:isOn k:in;
  k:hasSpeedLimit 16.0 .
k:constraint_0 a k:Constraint;
  k:kind "spatial_speed";
  k:start 650.0;
  k:end 800.0;
  k:lane -1;
  k:speed 8.0 .
```

Triples above are examples, not a report of a particular final snapshot. See outputs/*/static.ttl and dynamic.ttl for recorded facts. Traffic constraints are returned by the real `constraints.rq` SPARQL query, converted to typed Constraint objects and used to delete motion transitions. Additional query examples are documented in QUERIES.md.
