// The build imports this bundle as text. Keeping the worker in the app payload
// lets dashboards already running an older static-route whitelist load it too.
import source from './reachability.worker.bundle.js';

export function createReachabilityWorker(){
 const url=URL.createObjectURL(new Blob([source],{type:'text/javascript'}));
 let worker;
 try{worker=new Worker(url);}catch(error){URL.revokeObjectURL(url);throw error;}
 const release=()=>URL.revokeObjectURL(url);
 worker.addEventListener('message',release,{once:true});
 worker.addEventListener('error',release,{once:true});
 return worker;
}
