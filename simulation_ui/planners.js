export const plannerProfiles = {
  kars: {
    title:'KARS', short:'KARS', tag:'KNOWLEDGE AUGMENTED', color:'#337aaf',
    summary:'The main paper-inspired pipeline using traffic knowledge and reachable states.',
    knowledge:'Dynamic RDF + SPARQL', search:'Dynamic programming',
    prediction:'Constant-speed occupancy of surrounding main-road vehicles, with a fixed safety margin.',
    constraints:'All four spatial / temporal / speed types, plus lane markings.',
    fallback:'No complete path or imminent all-lane blockage triggers bounded braking.',
    paper:'Matches the high-level pipeline. Lane sampling, offline reuse, corridor geometry and objective definitions differ from the paper.',
    stages:['Fuse onboard + IoT','Query RDF constraints','Expand sampled graph','Prune transitions','Score lane corridors','DP path + SLSQP'],
  },
  astar: {
    title:'A* search', short:'A*', tag:'SEARCH BASELINE', color:'#7560ba',
    summary:'A* searches the same sampled, rule-constrained graph without RDF conversion.',
    knowledge:'Direct Python constraints', search:'A* with an admissible lower bound',
    prediction:'Same constant-speed occupancy as KARS. Receives the same delivered observations.',
    constraints:'All four spatial / temporal / speed types, plus lane markings.',
    fallback:'Uses the same braking and SUMO execution safeguards.',
    paper:'This is a controlled search baseline. It is not an independent geometric A* implementation of the paper’s experiments. DP and A* can return the same minimum-cost path.',
    stages:['Fuse onboard + IoT','Use direct constraints','Expand sampled graph','Prune transitions','Score lane corridors','A* path + SLSQP'],
  },

};

const canonical = value => {
  if(Array.isArray(value))return value.map(canonical);
  if(value&&typeof value==='object')return Object.fromEntries(Object.keys(value).sort().map(k=>[k,canonical(value[k])]));
  return value;
};
export function comparisonKey(run) {
  const m=run.manifest||{},metrics=run.metrics||{};
  // Reject legacy/incomplete provenance rather than mixing different code or road inputs.
  if(!m.source_hashes||!m.input_hashes||!m.config||m.seed===undefined)return null;
  const config={...m.config};delete config.realtime_factor;
  return JSON.stringify(canonical({scenario:m.scenario,seed:m.seed,duration:m.duration,
    density:m.density_period,delay:metrics.delay??m.delay,loss:metrics.loss??m.loss,
    config,source:m.source_hashes,inputs:m.input_hashes,sumo:m.sumo_version}));
}
export function matchingRuns(runs,anchor) {
  const key=anchor&&comparisonKey(anchor);if(!key)return [];
  const newest=new Map();
  for(const run of runs){if(run.alive||run.status?.state!=='completed'||comparisonKey(run)!==key)continue;
    const algorithm=run.manifest.algorithm,existing=newest.get(algorithm);
    if(!existing||(run.manifest.started_at||0)>(existing.manifest.started_at||0))newest.set(algorithm,run);
  }
  return [...newest.values()];
}
