"""Portable launcher: validate this folder, then open its city dashboard."""
import argparse
from pathlib import Path
import sys
import threading
import webbrowser


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8784)
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--no-browser',action='store_true')
    args=parser.parse_args()
    try:
        from kars.city import build_city_network
        from kars.sumo_setup import binary
        from kars.console import serve
    except ModuleNotFoundError as error:
        print('Missing dependency:',error.name)
        print('Install the project packages with: python -m pip install -r requirements.txt')
        return 1
    print('ROADSTER CITY V10',flush=True)
    print('Project:',Path(__file__).resolve().parent,flush=True)
    print('Python:',sys.version.split()[0],flush=True)
    print('SUMO:',binary('sumo'),flush=True)
    print('Network:',build_city_network(),flush=True)
    if args.check:return 0
    url=f'http://127.0.0.1:{args.port}/?view=city'
    print('Dashboard:',url,flush=True)
    print('Start a NEW journey. Click Enable sound for indicator ticks and driver alerts.',flush=True)
    if not args.no_browser:
        timer=threading.Timer(1.5,lambda:webbrowser.open(url))
        timer.daemon=True;timer.start()
    serve(args.port,False)
    return 0


if __name__=='__main__':
    try:sys.exit(main())
    except (OSError,RuntimeError) as error:
        print('Launch failed:',error,flush=True);sys.exit(1)
