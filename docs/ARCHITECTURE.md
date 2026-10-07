# Architecture diagrams

## System architecture
```mermaid
flowchart LR
 S[SUMO traffic] --> T[TraCI observations]
 T --> I[Simulated IoT delay and loss]
 I --> K[Static and dynamic RDF]
 K --> Q[SPARQL constraints]
 O[Offline motion transitions] --> R[Online reachable graph]
 E[Measured ego state] --> R
 Q --> A[Knowledge adjustment]
 R --> A
 A --> C[Corridor extraction]
 C --> D[Sub-corridor DP]
 D --> P[SLSQP trajectory]
 P --> V[Speed and lane commands]
 V --> S
 T --> M[Metrics CSV and plots]
 M --> U[Streamlit dashboard]
```

## Data flow
```mermaid
flowchart TD
 V[vehicle id, time, x, y, lane, speed, acceleration, heading, road, signal, limit] --> B[Traffic packet]
 B --> L[Delayed observation snapshot]
 L --> G[RDF triples]
 G --> Q[SPARQL result rows]
 Q --> C[Typed spatial and temporal restrictions]
 C --> P[Feasible graph and chain]
 P --> T[Planned time, x, lane center, velocity, acceleration, jerk]
 T --> S[SUMO execution]
 S --> F[Measured CSV]
```

## Module diagram
```mermaid
flowchart LR
 main[main.py] --> sim[simulation.py]
 main --> ex[experiments.py]
 sim --> comm[communication.py]
 sim --> kg[knowledge.py]
 sim --> plan[planning.py]
 plan --> rs[reachable_set.py]
 sim --> viz[visualization.py]
 dash[dashboard.py] --> main
```

## Algorithm flowchart
```mermaid
flowchart TD
 A[Observe traffic] --> B[Deliver latest IoT packet]
 B --> C[Update RDF and query restrictions]
 C --> D[Generate and prune RS graph]
 D --> E{Full horizon chain exists?}
 E -->|Yes| F[Score corridors and run DP]
 F --> G[Optimize and validate trajectory]
 E -->|No| H[Controlled braking]
 G --> I[Send control commands]
 H --> I
 I --> J[Measure and log]
 J --> A
```

## Sequence diagram
```mermaid
sequenceDiagram
 participant S as SUMO
 participant T as TraCI
 participant I as IoT channel
 participant K as RDF/SPARQL
 participant P as Planner
 loop Simulation steps
 S->>T: Measured traffic and ego
 T->>I: Observation packet
 I->>K: Latest delivered snapshot
 K->>P: SPARQL traffic restrictions
 T->>P: Current measured ego
 P->>P: Online RS, pruning, corridors, DP, SLSQP
 P->>T: Speed and lane target or braking
 T->>S: setSpeed and changeLane
 end
```

## Deployment
```mermaid
flowchart LR
 subgraph Laptop
 B[Browser localhost:8501] --> D[Streamlit Python process]
 D --> P[Planner Python subprocess]
 P <-->|TraCI TCP localhost| S[SUMO process]
 P --> O[outputs CSV RDF JSON PNG]
 O --> D
 end
```

SUMO provides traffic dynamics and signals; TraCI supplies observations and commands. The channel is simulated IoT transport. RDF stores facts, SPARQL retrieves actual planner restrictions, and the separate motion modules produce feasible sampled states. Metrics compare executed behavior; dashboard displays saved live snapshots. Deployment requires one laptop and no cloud service.
