from pathlib import Path
import os
import shutil
import subprocess
import sys
from .models import ROOT

def binary(name):
    suffix = '.exe' if os.name=='nt' else ''
    candidates = [ROOT.parent/'bin'/(name+suffix)]
    if os.environ.get('SUMO_HOME'):
        candidates.append(Path(os.environ['SUMO_HOME'])/'bin'/(name+suffix))
    candidates += [Path(sys.executable).parent/(name+suffix)]
    for path in candidates:
        if path.exists():
            if (path.parent.parent/'data').exists():
                os.environ['SUMO_HOME'] = str(path.parent.parent)
            return str(path)
    found = shutil.which(name)
    if found:
        return found
    # eclipse-sumo wheels also expose their installed binaries here.
    import sumo
    home = Path(sumo.__file__).parent
    for path in (home/'bin'/(name+suffix),home/(name+suffix)):
        if path.exists():
            return str(path)
    raise FileNotFoundError(f'{name} not found. Install eclipse-sumo or set SUMO_HOME.')

def build_network():
    folder = ROOT/'sumo/network'
    subprocess.run([binary('netconvert'),'--node-files',str(folder/'nodes.nod.xml'),
                    '--edge-files',str(folder/'edges.edg.xml'),'--output-file',str(folder/'road.net.xml'),
                    '--offset.disable-normalization','true','--no-turnarounds','true'],check=True,capture_output=True,text=True)
    return folder/'road.net.xml'
