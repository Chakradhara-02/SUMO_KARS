# Project title

Delay-Aware Traffic Knowledge Augmented Reachable-Set Planning in SUMO

# Abstract

This project implements a simulated IoT traffic pipeline, RDF/SPARQL restrictions, a sampled point-mass reachable graph, graph pruning, corridor candidates, dynamic programming and SLSQP longitudinal smoothing. SUMO executes speed and lane requests. Age-aware occupancy margins and stale-data braking form the primary extension. Comparisons measure executed safety, progress, comfort and timing. This is a project-level approximation inspired by KARS, with no exact paper reproduction claim.

# Introduction

Local planning must account for surrounding vehicles and road restrictions as conditions change. Connected observations can support planning, but delayed or missing packets make information less reliable.

# Problem statement

Select feasible local motion under road, speed, temporal and vehicle occupancy restrictions while monitoring the age of simulated IoT observations.

# Existing system

The referenced KARS work motivates knowledge-augmented reachable-set planning. The project compares ordinary knowledge adjustment, a basic RS traffic-rule ablation and an A* graph search.

# Limitations of existing system

The full paper was not supplied, so this project does not assert unverified limitations of its implementation. Our controlled experiment studies sensitivity to delayed and lost observations.

# Proposed system

A closed loop converts received traffic packets to RDF, executes SPARQL, prunes reachable motion, scores corridors, runs DP and validates longitudinal smoothing before sending TraCI commands.

# Objectives

Create a reproducible laptop simulation, demonstrate traffic-rule changes, maintain useful RDF, compare planners fairly, quantify packet-age effects and expose failures.

# Scope

Three-lane straight approach with a signal intersection. IoT simulation, virtual road restrictions, discrete lane planning and independent SUMO safety. No actual sensor, robot vehicle or learned model.

# Architecture

See ARCHITECTURE.md for system, data flow, module, algorithm, sequence and deployment diagrams.

# Methodology

See METHODOLOGY.md for component mapping, assumptions, extension ranking and implementation provenance.

# Algorithms

Offline dynamics samples, online grid-binned graph propagation, swept restriction pruning, terminal-lane corridor extraction, DP, genuine A* and SciPy SLSQP.

# Mathematical model

x_next=x+v*dt+0.5*a*dt², v_next=v+a*dt. DP recurrence D(v)=min_u[D(u)+c(u,v)]. Comfort uses RMS of measured acceleration and finite-difference jerk. The lateral state is a lane index, not a continuous steering model.

# Implementation

Python modules are in kars/. SUMO XML is under sumo/. RDF ontology and queries are under knowledge_graph/. Commands are in README.md.

# Experimental setup

Identical seeded SUMO scenarios, packet loss streams, vehicle dynamics and simulator safety modes. Full experiments use four scenarios, four algorithms and three seeds. Robustness sweeps vary delay and vehicle insertion period.

# Results

Use generated outputs/experiments/results.csv and summary.csv. See RESULTS.md for verified run records. Report full-length arrival separately from short integration tests. Never substitute paper metrics.

# Comparison

RS ablates traffic rules. A* and DP share traffic constraints and a time-expanded graph. Age-aware KARS uses wider occupancy and stale-data braking. Independent SUMO safety can hide collision differences.

# Novelty

The defensible student contribution is implementation and evaluation of packet-age-aware traffic knowledge, with rejection traces and reproducible experiments. KARS itself and age-aware planning in general are not claimed as new inventions.

# Advantages

Runs on a laptop, uses auditable SPARQL constraints, separates RS stages and logs measured states and feasible-chain decisions.

# Limitations

Incomplete bounded graph, virtual obstacle regions, conservative predictions, advisory crossing, no continuous lateral dynamics, no ground-truth real hardware, limited network and no verified exact paper equations.

# Future scope

Paper-exact equation alignment after obtaining PDF, physical obstacle integration, continuous lateral dynamics, future signal timing, validated uncertainty models and optional CARLA co-simulation.

# Conclusion

The project demonstrates a reproducible simulated traffic-knowledge planning pipeline. Claims about improvement require the measured comparisons and must account for reduced progress and the SUMO safety layer.

# References

Chen et al. (2025), Traffic-Knowledge-Augmented Path Planning for Autonomous Vehicles in Internet of Things, DOI https://doi.org/10.1109/JIOT.2025.3613790. SUMO https://sumo.dlr.de/docs/TraCI.html. RDFLib https://rdflib.readthedocs.io/. SciPy SLSQP https://docs.scipy.org/doc/scipy/reference/optimize.minimize-slsqp.html.
