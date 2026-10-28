import {localReachability} from './local-reachability.js';
let network,generation=0,previousSelection;
self.onmessage=({data})=>{
 if(data.type==='context'){if(data.network!==undefined)network=data.network;generation=data.generation;previousSelection=undefined;return;}
 if(data.type!=='plan'||data.generation!==generation)return;
 const begin=performance.now();
 try{
  const prediction=localReachability(data.frame,data.actors,network,{includeOffline:data.includeOffline,previousSelection});
  previousSelection=prediction.optimization?.complete?prediction.optimization:undefined;
  // Source/debug tables stay in the worker. Transport only drawing data.
  const {offlineRaw,offlineBranches,...result}=prediction;
  if(data.includeCandidates===false){result.safe=[];result.unsafe=[];result.branches=[];result.offline=[];result.offlineUnsafe=[];}
  self.postMessage({type:'result',id:data.id,generation,result,computeMs:performance.now()-begin});
 }catch(error){self.postMessage({type:'error',id:data.id,generation,error:String(error)});}
};
