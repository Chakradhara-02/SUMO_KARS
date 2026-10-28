// Change canvas resolution slowly; keep layout and vehicle interpolation intact.
export class FrameQuality{
 constructor(){this.ratio=null;this.average=16.7;this.lastChange=0;this.goodSince=null;}
 update(frameMs,now,cap){
  if(this.ratio===null)this.ratio=cap;
  this.ratio=Math.min(this.ratio,cap);
  if(Number.isFinite(frameMs)&&frameMs>0&&frameMs<1000)this.average=.92*this.average+.08*frameMs;
  if(this.average>28&&now-this.lastChange>=1500){this.ratio=Math.max(.65,Math.round(this.ratio*.85*100)/100);this.lastChange=now;this.goodSince=null;}
  else if(this.average<18.5){this.goodSince??=now;if(now-this.goodSince>5000&&now-this.lastChange>=3000){this.ratio=Math.min(cap,Math.round((this.ratio+.05)*100)/100);this.lastChange=now;}}
  else this.goodSince=null;
  return this.ratio;
 }
}
