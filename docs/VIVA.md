# Viva questions and answers

1. **What is your contribution?**

   A reproducible SUMO/RDF/SPARQL planning pipeline with packet-age-aware occupancy expansion and stale-data braking, evaluated against explicit baselines. KARS itself is existing work.

2. **Why SUMO?**

   It supplies lightweight traffic dynamics, signals and a controllable TraCI interface on a laptop.

3. **Why not CARLA?**

   The main objective is traffic knowledge and graph planning. Camera perception and detailed 3D physics would add hardware cost and are outside this scope.

4. **Why a knowledge graph?**

   It provides explicit entities, relationships and queryable restrictions with traceable sources.

5. **Why not only if-else rules?**

   A rule-based implementation could work here. RDF improves separation and extensibility; its computational benefit is not assumed.

6. **Is RS better than A*?**

   They solve different parts here: RS creates a dynamically feasible graph, while A* searches it. The comparison measures search/control behavior and does not prove universal superiority.

7. **What is the actual novelty?**

   The student contribution is the implemented age-aware extension and measured delay/loss evaluation. It is not a claim of globally unprecedented research.

8. **What if communication fails?**

   The channel retains the latest snapshot. The age-aware planner brakes if it is missing or older than the configured timeout.

9. **What if knowledge is outdated?**

   Occupancy bounds expand with age; timeout activates braking. These are conservative engineering assumptions.

10. **Can this work on a real vehicle?**

   The architecture is transferable, but this code lacks continuous vehicle dynamics, sensor validation and safety certification.

11. **Why no real vehicle?**

   Simulation supports repeatable safe experiments within student hardware constraints.

12. **Which dataset is used?**

   Seeded TraCI simulation generates traffic measurements; no external training dataset is used.

13. **What is autonomous driving?**

   Automated sensing, planning and control of a vehicle. This project implements a limited simulated planning/control part.

14. **What is IoT here?**

   Traffic observations transported through a simulated channel with delay and loss.

15. **What is TraCI?**

   SUMO’s client interface for reading simulation state and sending commands.

16. **What is RDF?**

   A graph of subject-predicate-object triples with identifiers and literals.

17. **What is OWL?**

   A vocabulary for defining classes and relationships. This project declares a lightweight schema without a full reasoner.

18. **What is SPARQL?**

   A query language for RDF. The planner actually executes a SELECT query to obtain constraints.

19. **What is an ontology?**

   A structured definition of relevant concepts and properties, such as vehicles, lanes and traffic signals.

20. **What is a reachable set?**

   States attainable under the selected motion model and action bounds within a horizon.

21. **Is your reachable set exact?**

   No. Sampling, grid bins and the state cap make it a finite incomplete approximation.

22. **What is a point-mass model?**

   A simplified longitudinal model with position, velocity and acceleration; no steering dynamics.

23. **Why separate offline and online RS?**

   Offline defines reusable transitions/actions, online anchors propagation to measured ego state, and adjustment imposes current restrictions.

24. **What is a transition matrix?**

   The exported table maps sampled velocities and accelerations to next velocity and displacement; online graph edges represent actual transitions.

25. **What is dt?**

   The planning discretization interval in seconds. Simulation uses a separate smaller interval.

26. **What is the horizon?**

   The number of future planning steps, configured as five by default.

27. **What does spatial restriction mean?**

   A forbidden longitudinal/lane region independent of speed or time.

28. **What does spatial-speed mean?**

   A region with a maximum allowed speed.

29. **What does spatial-temporal mean?**

   A region forbidden during a given active time interval.

30. **What does spatial-temporal-speed mean?**

   A speed restriction that applies inside a region during an active time interval.

31. **Why check swept edges?**

   Checking only endpoints would allow jumping across a narrow obstacle without detecting intersection.

32. **How are solid markings handled?**

   Crossing between lane indices is rejected while the motion segment overlaps the marked interval.

33. **How are pedestrians handled?**

   Only an advisory crossing speed region exists; no moving pedestrian agent is simulated.

34. **How do you detect red lights?**

   TraCI getNextTLS gives the upcoming state and distance. The planner creates a temporary stop-line restriction.

35. **Do you predict future light colors?**

   No. Current red/yellow is conservatively treated as closed for the local horizon.

36. **What is corridor extraction?**

   Full-horizon endpoints are grouped by lane and their reachable ancestors form candidate subgraphs.

37. **Is your corridor continuous?**

   No. It is a sampled graph corridor, not a union of continuous reachable polytopes.

38. **What is spatial margin?**

   Here it is a proxy based on distinct positions per layer. The paper’s exact margin is unverified.

39. **What is a sub-corridor?**

   The DP chain within a candidate graph corridor, chosen by configured costs.

40. **What is dynamic programming?**

   A method that reuses optimal costs to preceding states in a layered graph.

41. **What is the DP recurrence?**

   Best cost to a node equals the minimum parent cost plus that transition’s cost.

42. **Why is the graph acyclic?**

   Every transition increases the time layer, preventing directed cycles.

43. **What is A*?**

   A priority-queue search that ranks accumulated cost plus an admissible future-cost bound.

44. **What heuristic do you use?**

   0.01 times the number of remaining layers, since every edge costs at least 0.01.

45. **How is A* validated?**

   Unit tests compare its cost to DP on the same graph.

46. **What is Frenet planning?**

   Planning in longitudinal/lateral coordinates relative to a reference road. A separate Frenet baseline is not implemented.

47. **What is trajectory planning?**

   Producing time-indexed motion targets rather than only a geometric route.

48. **What is SLSQP?**

   SciPy’s sequential least-squares programming optimizer for constrained nonlinear problems.

49. **What does the optimizer minimize?**

   Acceleration squared, acceleration differences and deviation from DP longitudinal positions.

50. **What if optimization fails?**

   The validated feasible DP trajectory is retained.

51. **What is velocity?**

   Rate of position change, measured in meters per second.

52. **What is acceleration?**

   Rate of velocity change, measured in meters per second squared.

53. **What is jerk?**

   Rate of acceleration change, measured in meters per second cubed.

54. **Why measure jerk?**

   Abrupt acceleration changes can indicate reduced ride comfort.

55. **What is RMS?**

   Square root of the mean of squared samples.

56. **How is collision count measured?**

   SUMO collision events involving ego are counted; repeated reporting can count multiple events.

57. **What is success?**

   Ego arrival without a reported collision. Rule compliance is measured separately.

58. **How is clearance measured?**

   Leader bumper gap and distance to active virtual blocks in ego’s lane; it is not full 2D geometric clearance.

59. **What is emergency mode?**

   A no-full-horizon-chain or stale-data condition that requests bounded braking.

60. **How does emergency recover?**

   The next planning cycle can return to normal when a feasible full-horizon chain and fresh knowledge exist.

61. **Does braking guarantee avoidance?**

   No. Late detection and limited deceleration can still leave inadequate stopping distance.

62. **What is stopping distance?**

   For constant braking magnitude b, an idealized estimate is v²/(2b), plus reaction-distance effects.

63. **What is packet loss?**

   A sent simulated observation packet randomly never arrives.

64. **What is packet delay?**

   The time between generating and delivering an observation snapshot.

65. **What is knowledge age?**

   Current simulation time minus the latest received snapshot timestamp.

66. **What is uncertainty growth?**

   A configured distance added to occupancy margin per second of packet age.

67. **Is uncertainty statistically calibrated?**

   No. It is a tunable conservative bound, not a calibrated probability.

68. **Why use random seeds?**

   They make traffic and packet streams repeatable across algorithms.

69. **Why repeat experiments?**

   Traffic and packet randomness can change outcomes; mean and standard deviation show variability.

70. **What is a fair comparison?**

   Same scenario, seed, packet stream, motion limits, cost, smoothing and SUMO safety settings, with documented information differences.

71. **Does RS receive all traffic rules?**

   No. It is explicitly an ablation that keeps physical occupancy but omits traffic-rule pruning.

72. **Does A* use the knowledge graph?**

   No. It receives the same delivered typed constraints directly, isolating graph-query overhead.

73. **Can SUMO hide unsafe planning?**

   Yes. Its independent collision and signal controls remain active. Therefore zero collisions alone are insufficient evidence.

74. **Why retain SUMO safety?**

   It provides a consistent simulator execution layer; its influence is disclosed for every algorithm.

75. **What is static knowledge?**

   Schema and road descriptions that remain stable across cycles.

76. **What is dynamic knowledge?**

   Observed vehicles, signal state and active restrictions refreshed from received packets.

77. **How do updates avoid obsolete triples?**

   The dynamic graph is replaced for each delivered snapshot rather than appending old states indefinitely.

78. **What are literals?**

   Typed RDF values such as speed, timestamp and lane index.

79. **What is a URI?**

   An identifier used to distinguish graph entities and properties.

80. **Do you use graph reasoning?**

   No full OWL reasoner. Planner rules operate on explicit SPARQL result rows.

81. **Why Python?**

   It offers TraCI, RDFLib, scientific optimization, plotting and a readable implementation.

82. **Why NumPy?**

   It supports trajectory arrays and metric calculations.

83. **Why Pandas?**

   It records traffic measurements and aggregates experiment results.

84. **Why SciPy?**

   It supplies the constrained SLSQP optimizer.

85. **Why NetworkX?**

   It represents time-state graphs and supplies graph traversal and topological ordering.

86. **Why Streamlit?**

   It provides a simple local dashboard with simulation controls and saved-result views.

87. **Is this real-time guaranteed?**

   No. Timings are measured; no hard real-time deadline or worst-case execution guarantee exists.

88. **How often does planning run?**

   At the configured planning interval or a changed local road/signal signature.

89. **What is the state cap?**

   A limit on retained states per layer to bound computation, potentially discarding feasible alternatives.

90. **Does finer grid always improve results?**

   It can preserve more detail but costs more computation; the state cap also affects completeness.

91. **How is speed control applied?**

   The first future trajectory velocity becomes a TraCI setSpeed request, constrained by SUMO safety.

92. **How is lane control applied?**

   The first future lane becomes changeLane on non-junction road edges, with safety gaps handled by SUMO.

93. **Are lateral acceleration and jerk measured?**

   No. Exported y is lane center and comfort metrics are longitudinal.

94. **Why are virtual obstacles used?**

   They make traffic-knowledge restrictions explicit and reproducible, but they are not physical collision objects.

95. **What is the static scenario?**

   Road speed, lane marking, crossing advisory and a traffic signal remain present; the name refers to added knowledge events, not a traffic-free road.

96. **What is the semi-dynamic scenario?**

   Construction and a timed temporary lane blockage modify drivable regions.

97. **What is the dynamic scenario?**

   A lead vehicle brakes and later resumes under changing traffic signals.

98. **What is the delay scenario?**

   Dynamic traffic and roadblocks with delayed/lost observation packets.

99. **Is ML implemented?**

   No. The primary extension is analytical age-aware traffic knowledge, avoiding unsupported AI claims.

100. **How would ML be added?**

   Collect labeled conflict examples, split by scenario/seed, validate prediction and then compare a planner using the risk output.

101. **What are the main limitations?**

   No paper-exact verification, finite sampled RS, discrete lateral state, simplified occupancy and signal predictions, virtual restrictions and simulator safety influence.

102. **What should future work prioritize?**

   Obtain the paper PDF for alignment, validate obstacle/signal handling, model lateral dynamics and calibrate uncertainty against ground truth.

103. **How do you defend an extension that reduces speed?**

   Compare clearance, collisions, rule violations and arrival as well as speed. A conservative safety policy has a measurable efficiency cost.

104. **What if no algorithm arrives?**

   Report failure honestly, inspect constraints and horizon/state limits, and avoid presenting a short or blocked run as successful.

105. **How can another student reproduce this?**

   Install requirements, run setup, pytest, scenarios and experiment commands from README, retaining seeds and config.

106. **Where do final numbers come from?**

   Measured ego.csv and traffic.csv, aggregated into metrics.json, results.csv and summary.csv.

107. **Did you reproduce the paper exactly?**

   No. The full PDF was unavailable; the implementation clearly marks project approximations and extensions.
