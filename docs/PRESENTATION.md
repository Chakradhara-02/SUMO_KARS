# 20-slide presentation notes

## 1. Delay-aware traffic planning

Content: SUMO simulation of traffic knowledge and reachable motion

Diagram: Optional supporting graphic; focus on the stated concept.

Say: SUMO simulation of traffic knowledge and reachable motion

Likely panel question: What assumptions limit this part of the implementation?

## 2. Local planning problem

Content: Road restrictions and nearby vehicles change while the ego vehicle moves. Delayed observations can misrepresent available space.

Diagram: Optional supporting graphic; focus on the stated concept.

Say: Road restrictions and nearby vehicles change while the ego vehicle moves. Delayed observations can misrepresent available space.

Likely panel question: What assumptions limit this part of the implementation?

## 3. Project motivation

Content: A student laptop can reproduce traffic events and compare planning decisions using measured simulation data.

Diagram: Optional supporting graphic; focus on the stated concept.

Say: A student laptop can reproduce traffic events and compare planning decisions using measured simulation data.

Likely panel question: What assumptions limit this part of the implementation?

## 4. Existing KARS framework

Content: The referenced KARS work connects traffic knowledge with reachable-set planning. This implementation uses project-level approximations.

Diagram: Optional supporting graphic; focus on the stated concept.

Say: The referenced KARS work connects traffic knowledge with reachable-set planning. This implementation uses project-level approximations.

Likely panel question: What assumptions limit this part of the implementation?

## 5. Experiment gap

Content: We study delayed and lost traffic knowledge. The full paper was unavailable, so we do not assert an unverified gap in its experiments.

Diagram: Optional supporting graphic; focus on the stated concept.

Say: We study delayed and lost traffic knowledge. The full paper was unavailable, so we do not assert an unverified gap in its experiments.

Likely panel question: What assumptions limit this part of the implementation?

## 6. Proposed implementation

Content: Received packets become RDF constraints. The planner prunes motion, selects a chain and requests speed/lane changes.

Diagram: Use the system architecture in ARCHITECTURE.md.

Say: Received packets become RDF constraints. The planner prunes motion, selects a chain and requests speed/lane changes.

Likely panel question: What assumptions limit this part of the implementation?

## 7. System architecture

Content: SUMO, TraCI, simulated IoT, RDF/SPARQL, RS, corridor DP, SLSQP and control form a repeating loop.

Diagram: Use the system architecture in ARCHITECTURE.md.

Say: SUMO, TraCI, simulated IoT, RDF/SPARQL, RS, corridor DP, SLSQP and control form a repeating loop.

Likely panel question: What assumptions limit this part of the implementation?

## 8. Simulated IoT layer

Content: A seeded channel delays or drops packets. Each snapshot retains its generation timestamp. No hardware sensor is claimed.

Diagram: Optional supporting graphic; focus on the stated concept.

Say: A seeded channel delays or drops packets. Each snapshot retains its generation timestamp. No hardware sensor is claimed.

Likely panel question: What assumptions limit this part of the implementation?

## 9. Knowledge graph

Content: Static schema describes roads and lanes. Dynamic triples describe observed vehicles and active restrictions. SPARQL drives pruning.

Diagram: Show knowledge_graph.png.

Say: Static schema describes roads and lanes. Dynamic triples describe observed vehicles and active restrictions. SPARQL drives pruning.

Likely panel question: Why is SPARQL actually needed?

## 10. Reachable motion

Content: Offline samples define actions. Online propagation uses x_next=x+v dt+0.5a dt² and v_next=v+a dt. The grid is finite.

Diagram: Show raw and adjusted RS from the demo.

Say: Offline samples define actions. Online propagation uses x_next=x+v dt+0.5a dt² and v_next=v+a dt. The grid is finite.

Likely panel question: Is the sampled set complete?

## 11. Traffic constraint handling

Content: Swept segments are checked against spatial, spatial-speed, spatial-temporal and spatial-temporal-speed restrictions.

Diagram: Optional supporting graphic; focus on the stated concept.

Say: Swept segments are checked against spatial, spatial-speed, spatial-temporal and spatial-temporal-speed restrictions.

Likely panel question: What assumptions limit this part of the implementation?

## 12. Corridor and chain selection

Content: Terminal lane endpoints define ancestor corridors. DP minimizes speed deficit, acceleration, lane switching and center distance.

Diagram: Optional supporting graphic; focus on the stated concept.

Say: Terminal lane endpoints define ancestor corridors. DP minimizes speed deficit, acceleration, lane switching and center distance.

Likely panel question: What assumptions limit this part of the implementation?

## 13. Trajectory generation

Content: SLSQP smooths longitudinal acceleration within bounds. Invalid optimization falls back to the feasible DP chain.

Diagram: Show planned_trajectory.png.

Say: SLSQP smooths longitudinal acceleration within bounds. Invalid optimization falls back to the feasible DP chain.

Likely panel question: What assumptions limit this part of the implementation?

## 14. Age-aware extension

Content: Vehicle occupancy grows with packet age. Missing or stale knowledge triggers controlled braking. Compare safety and progress together.

Diagram: Optional supporting graphic; focus on the stated concept.

Say: Vehicle occupancy grows with packet age. Missing or stale knowledge triggers controlled braking. Compare safety and progress together.

Likely panel question: How do you distinguish contribution from existing KARS?

## 15. SUMO demonstration

Content: Construction, temporary lane blockage, lead braking, changed speed cap and traffic signal exercise the full pipeline.

Diagram: Show road_trajectory.png.

Say: Construction, temporary lane blockage, lead braking, changed speed cap and traffic signal exercise the full pipeline.

Likely panel question: What assumptions limit this part of the implementation?

## 16. Measured results

Content: Use the completed run CSV and JSON. Arrival, collision events, rule violations and clearance describe executed behavior.

Diagram: Show measured run metrics.

Say: Use the completed run CSV and JSON. Arrival, collision events, rule violations and clearance describe executed behavior.

Likely panel question: Did the ego arrive and how did SUMO safety affect outcomes?

## 17. Baseline comparison

Content: A* searches the same feasible time-state graph. Basic RS omits traffic-rule pruning. All planners retain identical SUMO safety.

Diagram: Use generated comparison.png.

Say: A* searches the same feasible time-state graph. Basic RS omits traffic-rule pruning. All planners retain identical SUMO safety.

Likely panel question: Did baselines receive the same packet stream?

## 18. Project advantages

Content: Explicit queries and rejection sources make decisions auditable. Tests and seeded scenarios support reproduction.

Diagram: Optional supporting graphic; focus on the stated concept.

Say: Explicit queries and rejection sources make decisions auditable. Tests and seeded scenarios support reproduction.

Likely panel question: What assumptions limit this part of the implementation?

## 19. Limits and future work

Content: Add validated lateral dynamics and physical obstacles. Obtain the full paper for equation alignment. Calibrate uncertainty before real deployment.

Diagram: Optional supporting graphic; focus on the stated concept.

Say: Add validated lateral dynamics and physical obstacles. Obtain the full paper for equation alignment. Calibrate uncertainty before real deployment.

Likely panel question: What assumptions limit this part of the implementation?

## 20. Conclusion

Content: The project demonstrates knowledge-driven local planning and an implementable delay-aware extension. Measured comparisons determine its benefit.

Diagram: Optional supporting graphic; focus on the stated concept.

Say: The project demonstrates knowledge-driven local planning and an implementable delay-aware extension. Measured comparisons determine its benefit.

Likely panel question: What assumptions limit this part of the implementation?
