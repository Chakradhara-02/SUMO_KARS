"""Local simulation console: persistent runs, process controls, streaming and replay."""
import bisect
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
import uuid
import webbrowser
import urllib.request
import socket
import xml.etree.ElementTree as ET
import zipfile
from .models import ROOT
from .scenarios import SCENARIO_INFO
from .simulation import SCENARIOS, ALGORITHMS, atomic_json
from .storage import read_json


def process_alive(pid):
    if not pid:
        return False
    if os.name == 'nt':
        import ctypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.OpenProcess.argtypes = [ctypes.c_uint32,ctypes.c_bool,ctypes.c_uint32]
        kernel.GetExitCodeProcess.argtypes = [ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint32)]
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel.OpenProcess(0x1000,False,int(pid))
        if not handle:
            return False
        code = ctypes.c_uint32()
        valid = kernel.GetExitCodeProcess(handle,ctypes.byref(code))
        kernel.CloseHandle(handle)
        return bool(valid and code.value == 259)
    try:
        os.kill(int(pid),0)
        return True
    except OSError:
        return False


class RunManager:
    def __init__(self, root=None):
        self.root = Path(root) if root else ROOT/'outputs/runs'
        self.root.mkdir(parents=True,exist_ok=True)
        self.lock = threading.RLock()
        self.processes = {}
        self.cache = {}

    def folder(self, run_id):
        if not run_id or any(c not in '0123456789abcdefghijklmnopqrstuvwxyz_-' for c in run_id):
            raise ValueError('Invalid run ID')
        folder = self.root/run_id
        if not folder.is_dir():
            raise ValueError('Run not found')
        return folder

    def describe(self, folder):
        manifest = read_json(folder/'manifest.json')
        launch = read_json(folder/'launch.json')
        status = read_json(folder/'status.json',{'state':'starting','time':0})
        process = self.processes.get(folder.name)
        # A recycled OS PID must not resurrect an already completed saved run.
        alive = process.poll() is None if process else (
            status.get('state') in ('starting','running','paused') and process_alive(launch.get('pid')))
        if status.get('state') in ('starting','running','paused') and not alive:
            status = {'state':'failed','error':'Simulation process ended before saving its final status'}
            atomic_json(folder/'status.json',status)
        return {'id':folder.name,'manifest':manifest or launch,'status':status,
                'metrics':read_json(folder/'metrics.json'),'alive':alive}

    def runs(self):
        with self.lock:
            return [self.describe(p) for p in sorted(self.root.iterdir(),reverse=True)
                    if p.is_dir() and (p/'launch.json').exists()]

    def start(self, params):
        with self.lock:
            if any(r['alive'] for r in self.runs()):
                raise ValueError('Stop the current run before starting another')
            scenario, algorithm = params.get('scenario','demo'),params.get('algorithm','kars')
            if scenario=='city':algorithm='city'
            if scenario not in SCENARIOS or algorithm not in ALGORITHMS:
                raise ValueError('Unknown scenario or planner')
            def numeric(key, default, lower, upper):
                value = float(params.get(key,default))
                if not lower <= value <= upper:
                    raise ValueError(f'{key} must be between {lower} and {upper}')
                return value
            values = {'duration':numeric('duration',200,5,3600),'seed':numeric('seed',1,0,2**31-1),
                      'delay':numeric('delay',0,0,10),'loss':numeric('loss',0,0,1),
                      'density':numeric('density',9,2,60),'realtime':numeric('realtime',1,0,20),
                      'jitter':numeric('jitter',0,0,5),'sensor-range':numeric('sensor_range',120,10,500)}
            if not values['seed'].is_integer():
                raise ValueError('Random seed must be an integer')
            outage = params.get('outage',False)
            if scenario=='city':
                from .city import city_route
                city_route(params.get('city_start','n0_0'),params.get('city_destination','n4_4'))
                city_count=numeric('city_vehicles',180,20,600)
                if not city_count.is_integer():raise ValueError('City traffic count must be an integer')
            run_id = time.strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:6]
            folder = self.root/run_id
            folder.mkdir()
            atomic_json(folder/'control.json',{'action':'run','realtime_factor':values['realtime']})
            args = [sys.executable,str(ROOT/'main.py'),'run','--scenario',scenario,'--algorithm',algorithm,
                    '--output',str(folder),'--control-file',str(folder/'control.json')]
            for key,value in values.items():
                args += ['--'+key,str(int(value) if key=='seed' else value)]
            if scenario=='city':
                args += ['--city-start',params.get('city_start','n0_0'),
                         '--city-destination',params.get('city_destination','n4_4'),
                         '--city-vehicles',str(int(city_count))]
            if params.get('gui',False):
                args += ['--gui']
            if outage:
                args += ['--outage','30','40']
            flags = {'creationflags':subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
            with (folder/'run.log').open('w',encoding='utf-8') as log:
                process = subprocess.Popen(args,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,**flags)
            self.processes[run_id] = process
            atomic_json(folder/'launch.json',{'pid':process.pid,'scenario':scenario,'algorithm':algorithm,
                                              'city_network':'indian_city.net.xml' if scenario=='city' else None,
                                              'started_at':time.time(),'parameters':params})
            return {'id':run_id}

    def command(self, run_id, action, speed=None):
        with self.lock:
            folder = self.folder(run_id)
            if action not in ('run','pause','stop'):
                raise ValueError('Unknown command')
            if not self.describe(folder)['alive']:
                raise ValueError('This run has already ended')
            control = read_json(folder/'control.json',{'action':'run','realtime_factor':1})
            control['action'] = action
            if speed is not None:
                speed = float(speed)
                if not 0 <= speed <= 20:
                    raise ValueError('Playback speed must be between 0 and 20')
                control['realtime_factor'] = speed
            atomic_json(folder/'control.json',control)
            return control

    def frame(self, run_id, when=None):
        folder = self.folder(run_id)
        if when is None:
            return read_json(folder/'live.json')
        trace = folder/'trace.jsonl'
        if not trace.exists():
            return {}
        signature = (trace.stat().st_mtime_ns,trace.stat().st_size)
        with self.lock:
            cached = self.cache.get(run_id)
            if cached is None or cached[0] != signature:
                frames = []
                for line in trace.read_text(encoding='utf-8').splitlines():
                    try:
                        frames.append(json.loads(line))
                    except ValueError:
                        continue  # A partially written final frame is not a valid snapshot.
                plans = read_json(folder/'plans.json',[])
                cached = (signature,frames,[f['time'] for f in frames],plans,[p['time'] for p in plans])
                self.cache[run_id] = cached
            _,frames,times,plans,plan_times = cached
            if not frames:
                return {}
            index = max(0,bisect.bisect_right(times,when)-1)
            frame = dict(frames[index])
            if plans:
                plan = plans[max(0,bisect.bisect_right(plan_times,frame['time'])-1)]
                frame = {**plan,**frame}
            # Replay charts contain only data observed up to the selected time.
            frame['history'] = [{'timestamp':f['time'],'speed':f['ego']['speed'],
                                 'acceleration':f['ego']['acceleration'],'clearance':f['clearance'],
                                 'knowledge_age':f['age']} for f in frames[max(0,index-299):index+1]]
            return frame

    def archive(self, run_id):
        folder = self.folder(run_id)
        if self.describe(folder)['alive']:
            raise ValueError('Finish or stop the run before exporting')
        data = io.BytesIO()
        with zipfile.ZipFile(data,'w',zipfile.ZIP_DEFLATED) as archive:
            for path in folder.iterdir():
                if path.is_file() and path.suffix in ('.json','.jsonl','.csv','.ttl','.xml','.png','.log'):
                    archive.write(path,path.name)
        return data.getvalue()


def network_data(scenario=None,version=None):
    from .city import build_city_network, CITY_POINTS
    city_path=ROOT/'sumo/network/city/city.net.xml' if version=='legacy' else build_city_network() if scenario=='city' else None
    root = ET.parse(city_path if scenario=='city' else ROOT/'sumo/network/road.net.xml').getroot()
    return {'lanes':[{'id':lane.get('id'),'internal':edge.get('id').startswith(':'),
                      'width':float(lane.get('width','3.2')),
                      'shape':[[float(v) for v in pair.split(',')] for pair in lane.get('shape').split()]}
                     for edge in root.findall('edge') for lane in edge.findall('lane')],
            'city':scenario=='city','points':CITY_POINTS if scenario=='city' else [],
            'left_hand':root.get('lefthand')=='true','network_file':city_path.name if scenario=='city' else 'road.net.xml',
            'junctions':[{'id':j.get('id'),'shape':[[float(v) for v in p.split(',')]
                         for p in j.get('shape','').split()]} for j in root.findall('junction')
                         if j.get('type') != 'internal'],
            'signals':[{'id':c.get('tl'),'link':int(c.get('linkIndex')),
                        'lane':c.get('from')+'_'+c.get('fromLane'),'direction':c.get('dir','s')} for c in root.findall('connection')
                       if c.get('tl') and c.get('linkIndex')]}


def make_handler(manager):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, value, code=200, content_type='application/json', filename=None):
            body = json.dumps(value,allow_nan=False).encode() if content_type=='application/json' else value
            self.send_response(code)
            self.send_header('Content-Type',content_type)
            self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            if filename:
                self.send_header('Content-Disposition',f'attachment; filename="{filename}"')
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            try:
                url = urlparse(self.path)
                params = parse_qs(url.query)
                run_id = params.get('id',[''])[0]
                if url.path == '/api/runs':
                    self.send(manager.runs())
                elif url.path == '/api/network':
                    self.send(network_data(params.get('scenario',[None])[0],params.get('version',[None])[0]))
                elif url.path == '/api/city-route':
                    from .city import city_route
                    self.send(city_route(params.get('start',['n0_0'])[0],params.get('destination',['n4_4'])[0]))
                elif url.path == '/api/scenarios':
                    self.send({k:{'title':v[0],'description':v[1]} for k,v in SCENARIO_INFO.items()})
                elif url.path == '/api/frame':
                    when = float(params['time'][0]) if 'time' in params else None
                    self.send(manager.frame(run_id,when))
                elif url.path == '/api/log':
                    folder = manager.folder(run_id)
                    path = folder/'run.log'
                    self.send({'log':path.read_text(encoding='utf-8',errors='replace')[-12000:] if path.exists() else ''})
                elif url.path == '/api/export':
                    self.send(manager.archive(run_id),content_type='application/zip',filename=run_id+'.zip')
                elif url.path in ('/','/app.js','/app.bundle.js','/style.css','/scene3d.js','/planners.js',
                                  '/vendor/three.module.js','/vendor/three.core.js','/vendor/OrbitControls.js'):
                    filename = 'index.html' if url.path=='/' else url.path[1:]
                    types = {'index.html':'text/html; charset=utf-8','app.js':'text/javascript; charset=utf-8',
                             'style.css':'text/css; charset=utf-8'}
                    content_type = types.get(filename,'text/javascript; charset=utf-8')
                    self.send((ROOT/'simulation_ui'/filename).read_bytes(),content_type=content_type)
                else:
                    self.send({'error':'Not found'},404)
            except (ValueError,OSError) as error:
                self.send({'error':str(error)},400)

        def do_POST(self):
            # Bind to loopback and reject browser requests from other origins.
            origin = self.headers.get('Origin')
            if origin and origin != 'http://'+self.headers.get('Host',''):
                self.send({'error':'Origin rejected'},403)
                return
            try:
                size = int(self.headers.get('Content-Length',0))
                if size > 16384:
                    raise ValueError('Request too large')
                data = json.loads(self.rfile.read(size))
                if not isinstance(data,dict):
                    raise ValueError('Request must be a JSON object')
                if self.path == '/api/run':
                    self.send(manager.start(data))
                elif self.path == '/api/control':
                    self.send(manager.command(data['id'],data['action'],data.get('speed')))
                else:
                    self.send({'error':'Not found'},404)
            except (ValueError,KeyError,TypeError,OSError) as error:
                self.send({'error':str(error)},400)
    return Handler


class LocalServer(ThreadingHTTPServer):
    allow_reuse_address = False

    def server_bind(self):
        if os.name=='nt':
            # Windows SO_REUSEADDR permits competing servers to steal requests.
            self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        super().server_bind()


def serve(port=8765, open_browser=True):
    try:
        server = LocalServer(('127.0.0.1',port),make_handler(RunManager()))
    except OSError:
        url=f'http://127.0.0.1:{port}'
        try:
            with urllib.request.urlopen(url+'/api/scenarios',timeout=2) as response:
                existing=json.load(response)
            if set(existing)!=set(SCENARIOS):
                raise ValueError('Port is used by another application')
        except (OSError,ValueError):
            raise OSError(f'Port {port} is in use; choose another with --port') from None
        print(f'Simulation console already running: {url}',flush=True)
        if open_browser:
            webbrowser.open(url)
        return
    url = f'http://127.0.0.1:{server.server_port}'
    print(f'Simulation console: {url}',flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever(poll_interval=.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
