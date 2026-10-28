export function landmarkStyle(lot){
 const id=lot.id||'',index=[...id].reduce((n,c)=>n+c.charCodeAt(0),0)%5;
 const colors=['#547fa3','#cb8955','#6b9a87','#8b79af','#b96f76'];
 return {wall:lot.kind==='mall'?'#248f9b':colors[index],accent:lot.kind==='mall'?'#f0ad4e':'#203c58',roof:'#d9e6ec'};
}
export function drawCityLots(ctx,lots,X,Y,scale){
 for(const lot of lots||[]){const s=landmarkStyle(lot),x=lot.x,y=lot.y;
  ctx.fillStyle='#657480';ctx.fillRect(X(x),Y(y+44),78*scale,44*scale);
  ctx.strokeStyle='#dde4d9';ctx.lineWidth=Math.max(1,scale*.3);
  for(const slot of lot.slots){ctx.strokeStyle=slot.occupied?'#d2dae1':'#9ee5c4';ctx.strokeRect(X(slot.x-slot.width/2),Y(slot.y+slot.length/2),slot.width*scale,slot.length*scale);
   if(slot.occupied){ctx.fillStyle='#9ca6b3';ctx.fillRect(X(slot.x-.9),Y(slot.y+2.35),1.8*scale,4.7*scale);}
   if(scale>1.3){ctx.fillStyle='#edf5f7';ctx.font='9px Segoe UI';ctx.textAlign='center';ctx.fillText(slot.id,X(slot.x),Y(slot.y+4.3));}
  }
  ctx.fillStyle=s.wall;ctx.fillRect(X(x+12),Y(y+65),54*scale,18*scale);ctx.fillStyle=s.accent;ctx.fillRect(X(x+12),Y(y+51),54*scale,4*scale);
  ctx.fillStyle='#ffffff';ctx.textAlign='center';ctx.font='600 '+Math.max(9,Math.min(18,scale*2.4))+'px Segoe UI';ctx.fillText(lot.name.toUpperCase(),X(x+39),Y(y+54),50*scale);
 }
 ctx.textAlign='left';
}
