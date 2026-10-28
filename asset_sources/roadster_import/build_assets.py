import hashlib,io,json,struct
from pathlib import Path
import numpy as np
from PIL import Image

root=Path(__file__).parent;target=root.resolve().parents[1]/'simulation_ui/assets';target.mkdir(exist_ok=True)
a=np.load(root/'source_arrays.npz');p=a['positions'].copy();normals=a['normals'].copy();uv=a['uv'].copy()
scale=4.7/float(p[:,2].max()-p[:,2].min());front=float(p[:,2].max())
positions=np.column_stack(((p[:,2]-front)*scale,p[:,1]*scale,-p[:,0]*scale)).astype('<f4')
normals=np.column_stack((normals[:,2],normals[:,1],-normals[:,0])).astype('<f4')
centers={};wheel_names={}
for source,name,src_center in [('rear_left','rear_right',[-.329,.146,-.627]),('rear_right','rear_left',[.331,.145,-.629]),('front_left','front_right',[-.326,.146,.533]),('front_right','front_left',[.326,.146,.533])]:
 centers[source]=[(src_center[2]-front)*scale,src_center[1]*scale,-src_center[0]*scale];wheel_names[source]=name
wheelbase=centers['front_left'][0]-centers['rear_left'][0]
report=json.loads((root/'optimization.json').read_text());report.update(source_name='tesla-roadtser-2026.zip',source_sha256=hashlib.sha256((root/'roadster.zip').read_bytes()).hexdigest(),canonical={'length':4.7,'width':float(np.ptp(positions[:,2])),'height':float(positions[:,1].max()),'front_bumper':[0,0,0],'forward_axis':'+X','up_axis':'+Y','wheelbase':wheelbase,'rear_axle_offset':-centers['rear_left'][0]},rig={'wheels':'Two disconnected rear wheel components and two front wheel regions isolated from the combined body. Cylindrical front masks are centered on measured tire geometry.','body_panels':'Unrigged; no door/bonnet/boot animation supplied. Controls disabled for this asset.'})
for level,texture_size,quality in [('drive',1024,92),('showroom',2048,94)]:
 data=bytearray();views=[];accessors=[];meshes=[];nodes=[]
 def append(b,target_kind=None):
  while len(data)%4:data.append(0)
  view={'buffer':0,'byteOffset':len(data),'byteLength':len(b)}
  if target_kind:view['target']=target_kind
  data.extend(b);views.append(view);return len(views)-1
 def accessor(array,kind,component):
  view=append(array.tobytes(),34963 if kind=='SCALAR' else 34962)
  item={'bufferView':view,'componentType':component,'count':len(array),'type':kind}
  if kind=='VEC3':item.update(min=array.min(axis=0).tolist(),max=array.max(axis=0).tolist())
  accessors.append(item);return len(accessors)-1
 total=0
 for source in ['body','front_left','front_right','rear_left','rear_right']:
  idx=np.fromfile(root/f'{level}_{source}_indices.bin',dtype='<u4');keep,remap=np.unique(idx,return_inverse=True)
  local=positions[keep].copy();is_wheel=source!='body';center=centers.get(source,[0,0,0]);name='wheel_'+wheel_names[source] if is_wheel else 'RoadsterBody'
  if is_wheel:local-=np.asarray(center,dtype='<f4')
  index_type='<u2' if len(keep)<65536 else '<u4';index_component=5123 if len(keep)<65536 else 5125
  attrs={'POSITION':accessor(local,'VEC3',5126),'NORMAL':accessor(normals[keep],'VEC3',5126),'TEXCOORD_0':accessor(uv[keep].astype('<f4'),'VEC2',5126)}
  primitive={'attributes':attrs,'indices':accessor(remap.astype(index_type),'SCALAR',index_component),'material':0}
  meshes.append({'name':name,'primitives':[primitive]});node={'name':name,'mesh':len(meshes)-1}
  if is_wheel:node.update(translation=center,extras={'wheel':True,'front':source.startswith('front'),'radius':.1465*scale,'side':'left' if center[2]<0 else 'right'})
  nodes.append(node);total+=len(idx)//3
 im=Image.open(root/'texture.png').convert('RGB');im.thumbnail((texture_size,texture_size),Image.Resampling.LANCZOS);f=io.BytesIO();im.save(f,'JPEG',quality=quality,optimize=True,subsampling=0);view=append(f.getvalue())
 gltf={'asset':{'version':'2.0','generator':'KARS user-supplied Roadster conversion; meshoptimizer attribute-aware LOD'},'scene':0,'scenes':[{'nodes':list(range(len(nodes)))}],'nodes':nodes,'meshes':meshes,'materials':[{'name':'Roadster baked finish','doubleSided':True,'pbrMetallicRoughness':{'baseColorFactor':[1,1,1,1],'baseColorTexture':{'index':0},'metallicFactor':.08,'roughnessFactor':.4}}],'textures':[{'source':0}],'images':[{'bufferView':view,'mimeType':'image/jpeg'}],'buffers':[{'byteLength':len(data)}],'bufferViews':views,'accessors':accessors,'extras':report['canonical']}
 text=json.dumps(gltf,separators=(',',':')).encode();text+=b' '*(-len(text)%4);data+=b'\0'*(-len(data)%4)
 content=struct.pack('<4sII',b'glTF',2,28+len(text)+len(data))+struct.pack('<I4s',len(text),b'JSON')+text+struct.pack('<I4s',len(data),b'BIN\0')+data
 file=target/f'roadster-{level}.glb';file.write_bytes(content);report['levels'][level]['total_triangles']=total;report['levels'][level]['bytes']=len(content);report['levels'][level]['texture_size']=texture_size;print(file.name,total,'triangles',len(content),'bytes')
(target/'roadster-info.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report['canonical'],indent=2))
