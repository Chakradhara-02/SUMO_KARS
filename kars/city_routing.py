"""Connected route alternatives scored with measured traffic and distance."""
import itertools
import math
import xml.etree.ElementTree as ET
import networkx as nx


class CityRouter:
    def __init__(self, path):
        root = ET.parse(path).getroot()
        self.edges = {e.get('id'): e for e in root.findall('edge') if not e.get('id').startswith(':')}
        self.transitions={}
        self.directions={}
        lanes={lane.get('id'):lane for edge in root.findall('edge') for lane in edge.findall('lane')}
        for link in root.findall('connection'):
            pair=(link.get('from'),link.get('to'));via=lanes.get(link.get('via'))
            self.directions[pair]=link.get('dir','s')
            delay=0.;shape=[]
            if via is not None:
                delay=float(via.get('length'))/max(2.,float(via.get('speed')))
                shape=[[float(v) for v in p.split(',')] for p in via.get('shape').split()]
            if link.get('tl'):delay+=3.
            old=self.transitions.get(pair)
            if old is None or delay<old[0]:self.transitions[pair]=(delay,shape)
        self.costs={}
        self.graph = nx.DiGraph()
        self.graph.add_nodes_from(self.edges)
        for c in root.findall('connection'):
            a, b = c.get('from'), c.get('to')
            if a in self.edges and b in self.edges:
                self.graph.add_edge(a, b)

    def alternatives(self, current, destination, connection=None, limit=3):
        graph = self.graph.copy()
        costs = {}
        for key, edge in self.edges.items():
            lane = edge.find('lane')
            length = float(lane.get('length'))
            free = length / min(22., float(lane.get('speed')))
            count, travel, halted = 0, free, 0
            if connection is not None:
                count = connection.edge.getLastStepVehicleNumber(key)
                halted = connection.edge.getLastStepHaltingNumber(key)
                if count:
                    travel = max(free, min(free * 8 + 30, connection.edge.getTraveltime(key)))
            # Distance remains explicit; lower travel time can justify a modest detour.
            eta = travel + halted * 1.5
            costs[key] = (length, eta, count, eta + length / 30.)
        for a, b in graph.edges:
            graph[a][b]['weight'] = costs[b][3]+self.transitions.get((a,b),(0,[]))[0]
        self.costs=costs
        results = []
        goal='arrival_'+destination if any(e.get('to')=='arrival_'+destination for e in self.edges.values()) else destination
        for end, edge in self.edges.items():
            if edge.get('to') != goal:
                continue
            try:
                for route in itertools.islice(nx.shortest_simple_paths(graph, current, end, weight='weight'), limit):
                    # Reject edge-simple paths that revisit a junction and make loops.
                    nodes = [self.edges[route[0]].get('from')] + [self.edges[e].get('to') for e in route]
                    if len(nodes) != len(set(nodes)):
                        continue
                    length = sum(costs[e][0] for e in route)
                    eta = sum(costs[e][1] for e in route)+sum(self.transitions.get((a,b),(0,[]))[0] for a,b in zip(route,route[1:]))
                    shape=[]
                    for i,e in enumerate(route):
                        if i:shape.extend(self.transitions.get((route[i-1],e),(0,[]))[1])
                        shape.extend([[float(v) for v in p.split(',')] for p in self.edges[e].find('lane').get('shape').split()])
                    results.append({'edges': route, 'distance': length, 'eta': eta,
                                    'traffic': sum(costs[e][2] for e in route),
                                    'score': eta + length / 30., 'shape': shape})
            except nx.NetworkXNoPath:
                continue
        unique = {tuple(r['edges']): r for r in results}
        return sorted(unique.values(), key=lambda r: r['score'])[:limit]

    def score(self,route):
        """Use the identical observation snapshot and objective for switch hysteresis."""
        return sum(self.costs[e][3] for e in route)+sum(
            self.transitions.get((a,b),(0,[]))[0] for a,b in zip(route,route[1:]))

    def guidance(self,route,ego,maximum=220):
        """Persistent route geometry, independent of feasible motion forecasts."""
        points=[]
        for i,key in enumerate(route):
            if i:points.extend(self.transitions.get((route[i-1],key),(0,[]))[1])
            lane=self.edges[key].find('lane')
            if i==0:
                lane=next((l for l in self.edges[key].findall('lane') if l.get('id')==ego.lane_id),lane)
            points.extend([[float(v) for v in p.split(',')] for p in lane.get('shape').split()])
        if not points:return [[ego.x,ego.y,ego.z]]
        # Project onto segments so a stopped car still has forward guidance.
        nearest=(float('inf'),0,0.)
        for i,(a,b) in enumerate(zip(points,points[1:])):
            dx,dy=b[0]-a[0],b[1]-a[1];t=max(0,min(1,((ego.x-a[0])*dx+(ego.y-a[1])*dy)/(dx*dx+dy*dy or 1)))
            z=(a[2] if len(a)>2 else 0)*(1-t)+(b[2] if len(b)>2 else 0)*t
            distance=math.hypot(ego.x-a[0]-dx*t,ego.y-a[1]-dy*t)+abs(z-ego.z)*3
            if distance<nearest[0]:nearest=(distance,i,t)
        result=[[ego.x,ego.y,ego.z]];distance=0
        for p in points[nearest[1]+1:]:
            distance+=math.hypot(p[0]-result[-1][0],p[1]-result[-1][1]);result.append(p)
            if distance>=maximum:break
        return result

    def journey(self,route,lane_position=0):
        """Remaining route estimates follow rerouting instead of the original trip."""
        if not route:return {'remaining':0.,'eta':0.,'instruction':'Destination reached','junction_distance':0.}
        distance=eta=0.
        for i,key in enumerate(route):
            lane=self.edges[key].find('lane')
            length=float(lane.get('length'));left=max(0.,length-lane_position) if i==0 else length
            fraction=left/max(1.,length)
            travel=self.costs.get(key,(length,length/min(22.2,float(lane.get('speed'))),0,0))[1]
            distance+=left;eta+=travel*fraction
            if i:
                transition=self.transitions.get((route[i-1],key),(0,[]))
                eta+=transition[0]
        turn=self.directions.get(tuple(route[:2]),'s') if len(route)>1 else 'finish'
        instruction={'l':'Turn left','r':'Turn right','L':'Bear left','R':'Bear right',
                     's':'Continue straight','t':'Turn around','finish':'Continue to destination'}.get(turn,'Follow the route')
        first=float(self.edges[route[0]].find('lane').get('length'))
        return {'remaining':distance,'eta':eta,'instruction':instruction,
                'junction_distance':max(0.,first-lane_position)}
