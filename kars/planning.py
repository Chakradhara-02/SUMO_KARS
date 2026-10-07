"""Corridor candidates, sub-corridor DP/A*, and validated SLSQP smoothing."""
import heapq
import time
import numpy as np
import networkx as nx
from scipy.optimize import minimize
from .models import State
from .reachable_set import offline_rs, online_rs, rs_adjustment, violates

def corridors(graph, horizon):
    candidates = []
    for lane in sorted({graph.nodes[n]['state'].lane for n in graph if graph.nodes[n]['layer']==horizon}):
        ends = [n for n in graph if graph.nodes[n]['layer']==horizon and graph.nodes[n]['state'].lane==lane]
        members = {0}
        for node in ends:
            members |= nx.ancestors(graph, node) | {node}
        sub = graph.subgraph(members).copy()
        # Spatial margin proxy: number of distinct positions at each time layer.
        margin = min(len({round(sub.nodes[n]['state'].x, 1) for n in sub
                          if sub.nodes[n]['layer']==layer}) for layer in range(1,horizon+1))
        candidates.append({'lane': lane, 'graph': sub, 'margin': margin})
    return candidates

def edge_cost(graph, u, v, config):
    a, b = graph.nodes[u]['state'], graph.nodes[v]['state']
    w = config['weights']
    return (w['center'] * abs(b.lane-1) + w['efficiency']*(config['max_speed']-b.v)**2 / config['max_speed']
            + w['stability']*graph.edges[u,v]['acceleration']**2
            + w['lane_change']*abs(b.lane-a.lane) + .01)

def dynamic_programming(graph, config):
    cost, parent = {0: 0.}, {}
    for node in nx.topological_sort(graph):
        if node not in cost:
            continue
        for nxt in graph.successors(node):
            value = cost[node] + edge_cost(graph,node,nxt,config)
            if value < cost.get(nxt,float('inf')):
                cost[nxt], parent[nxt] = value, node
    ends = [n for n in cost if graph.nodes[n]['layer']==config['horizon']]
    if not ends:
        return [], float('inf')
    end = min(ends,key=cost.get)
    chain, final = [end], cost[end]
    while chain[-1] != 0:
        chain.append(parent[chain[-1]])
    return list(reversed(chain)), final

def astar(graph, config):
    # Admissible lower bound: each remaining edge costs at least .01.
    heuristic = lambda n: .01*(config['horizon']-graph.nodes[n]['layer'])
    queue = [(heuristic(0),0.,0)]
    costs, parents = {0:0.}, {}
    while queue:
        _, value, node = heapq.heappop(queue)
        if value != costs[node]:
            continue
        if graph.nodes[node]['layer']==config['horizon']:
            chain = [node]
            while chain[-1]!=0:
                chain.append(parents[chain[-1]])
            return list(reversed(chain)), value
        for nxt in graph.successors(node):
            trial = value+edge_cost(graph,node,nxt,config)
            if trial < costs.get(nxt,float('inf')):
                costs[nxt], parents[nxt] = trial, node
                heapq.heappush(queue,(trial+heuristic(nxt),trial,nxt))
    return [], float('inf')

def optimize_trajectory(states, constraints, config):
    dt, n = config['dt'], len(states)-1
    initial = np.diff([s.v for s in states])/dt
    target = np.array([s.x for s in states[1:]])
    def rollout(accel):
        velocity = states[0].v+np.cumsum(accel)*dt
        previous_v = np.r_[states[0].v,velocity[:-1]]
        position = states[0].x+np.cumsum(previous_v*dt+.5*accel*dt*dt)
        return position, velocity
    def objective(accel):
        x,_ = rollout(accel)
        return .1*np.sum(accel**2)+.3*np.sum(np.diff(accel)**2)+np.sum((x-target)**2)
    def bounds(accel):
        x,v = rollout(accel)
        return np.r_[v-config['min_speed'],config['max_speed']-v,
                     config['position_grid']/2-(x-target),config['position_grid']/2+(x-target)]
    result = minimize(objective,initial,method='SLSQP',bounds=[(config['min_acceleration'],config['max_acceleration'])]*n,
                      constraints=[{'type':'ineq','fun':bounds}],options={'maxiter':35,'ftol':1e-5})
    x,v = rollout(result.x)
    proposed = [states[0]]+[State(float(x[i]),float(v[i]),states[i+1].lane,states[i+1].t,
                                states[i+1].lane_hold,states[i+1].lane_origin) for i in range(n)]
    valid = result.success and np.min(bounds(result.x))>=-1e-5 and all(
        not violates(a,b,c) for a,b in zip(proposed,proposed[1:]) for c in constraints)
    selected = proposed if valid else states
    velocity = np.array([s.v for s in selected])
    acceleration = np.r_[initial[0] if not valid else result.x[0],np.diff(velocity)/dt]
    jerk = np.r_[0.,np.diff(acceleration)/dt]
    # Map the lane intent to the same gradual lateral transition used by SUMO.
    world_y = []
    for s in selected:
        center = -config['lanes']*config['lane_width'] + config['lane_width']/2 + s.lane*config['lane_width']
        if s.lane_origin >= 0 and s.lane_hold > 0:
            center -= (s.lane-s.lane_origin)*config['lane_width']*s.lane_hold/config['lane_change_duration']
        world_y.append(center)
    return {'time':[s.t for s in selected], 'x':[s.x for s in selected],
            'y':[s.lane*config['lane_width'] for s in selected], 'velocity':velocity.tolist(),
            'acceleration':acceleration.tolist(),'jerk':jerk.tolist(),
            'lane':[s.lane for s in selected],'world_y':world_y,'optimized':bool(valid)}

def emergency(state, config):
    return max(config['min_speed'],state.v+config['min_acceleration']*config['simulation_dt'])

class Planner:
    def __init__(self, config, algorithm='kars'):
        self.config, self.algorithm = config, algorithm
        self.offline = offline_rs(config)

    def plan(self, state, constraints):
        begin = time.perf_counter()
        raw = online_rs(state,self.offline,self.config)
        rs_seconds = time.perf_counter()-begin
        # Basic RS sees physical roadblocks/vehicle occupancies; traffic rules are omitted.
        used = constraints if self.algorithm!='rs' else [c for c in constraints if c.kind in ('spatial','spatial_temporal')]
        adjusted,rejected = rs_adjustment(raw,used)
        candidates = corridors(adjusted,self.config['horizon'])
        scored = []
        solver = astar if self.algorithm=='astar' else dynamic_programming
        for candidate in candidates:
            chain,cost = solver(candidate['graph'],self.config)
            candidate['cost'] = cost
            candidate['score'] = cost-.05*candidate['margin']
            scored.append((candidate['score'],chain,candidate))
        selected = min(scored,key=lambda item:item[0]) if scored else None
        chain = selected[1] if selected else []
        trajectory = optimize_trajectory([adjusted.nodes[n]['state'] for n in chain],used,self.config) if chain else None
        return {'raw':raw,'adjusted':adjusted,'rejected':rejected,'candidates':candidates,
                'selected_lane':selected[2]['lane'] if selected else None,'chain':chain,'trajectory':trajectory,
                'emergency':not bool(chain),'rs_seconds':rs_seconds,'planning_seconds':time.perf_counter()-begin}
