import json,struct
from pathlib import Path
import numpy as np
from kars.models import ROOT

def asset(level):
    b=(ROOT/'simulation_ui/assets'/f'roadster-{level}.glb').read_bytes()
    assert b[:4]==b'glTF' and struct.unpack_from('<I',b,8)[0]==len(b)
    size=struct.unpack_from('<I',b,12)[0];return json.loads(b[20:20+size]),b[28+size:]

def test_imported_roadster_has_four_measured_wheel_pivots_and_fits_ego_envelope():
    for level in ('drive','showroom'):
        g,b=asset(level);points=[];wheels=[]
        for n in g['nodes']:
            primitive=g['meshes'][n['mesh']]['primitives'][0];a=g['accessors'][primitive['attributes']['POSITION']];view=g['bufferViews'][a['bufferView']]
            p=np.frombuffer(b,dtype='<f4',count=a['count']*3,offset=view['byteOffset']).reshape(-1,3)+np.asarray(n.get('translation',[0,0,0]))
            points.append(p)
            if n.get('extras',{}).get('wheel'):wheels.append(n)
        p=np.concatenate(points)
        assert p[:,0].min()>=-4.701 and p[:,0].max()<=.001
        assert np.abs(p[:,2]).max()<1.025 and p[:,1].min()>-.001
        assert len(wheels)==4 and sum(w['extras']['front'] for w in wheels)==2
        assert {w['extras']['side'] for w in wheels}=={'left','right'}
        assert all(abs(w['translation'][1]-w['extras']['radius'])<.02 for w in wheels)
        assert 2.8<g['extras']['wheelbase']<3.

def test_driving_model_has_bounded_geometry_and_embedded_texture():
    g,_=asset('drive');triangles=sum(g['accessors'][p['indices']]['count']//3 for m in g['meshes'] for p in m['primitives'])
    assert triangles<=50000
    assert (ROOT/'simulation_ui/assets/roadster-drive.glb').stat().st_size<3_000_000
    assert all('uri' not in i and 'bufferView' in i for i in g['images'])
    assert all('uri' not in b for b in g['buffers'])
    assert 'baseColorTexture' in g['materials'][0]['pbrMetallicRoughness']
