import argparse
from pathlib import Path
from kars.models import ROOT
from kars.sumo_setup import build_network, binary
from kars.simulation import run_simulation, SCENARIOS, ALGORITHMS

def main():
    parser = argparse.ArgumentParser(description='SUMO knowledge-augmented reachable-set project')
    parser.add_argument('command',choices=['setup','run','experiments','sweep','replay','serve'])
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--no-browser',action='store_true')
    parser.add_argument('--scenario',choices=SCENARIOS,default='demo')
    parser.add_argument('--scenarios',nargs='+',choices=SCENARIOS,help='Selected comparison scenarios; preserves other completed groups')
    parser.add_argument('--algorithm',choices=ALGORITHMS,default='kars_delay')
    parser.add_argument('--seed',type=int,default=1)
    parser.add_argument('--duration',type=float)
    parser.add_argument('--gui',action='store_true')
    parser.add_argument('--delay',type=float)
    parser.add_argument('--loss',type=float)
    parser.add_argument('--repeats',type=int,default=3)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--control-file',type=Path)
    parser.add_argument('--no-plots',action='store_true')
    parser.add_argument('--density',type=float,default=9,help='Main traffic insertion period (s)')
    parser.add_argument('--realtime',type=float,default=0,help='Simulation seconds per wall second; 0 runs unrestricted')
    parser.add_argument('--jitter',type=float,default=0,help='Uniform IoT delay variation (+/- seconds)')
    parser.add_argument('--sensor-range',type=float,default=120,help='Onboard sensor range in metres')
    parser.add_argument('--city-start',default='n0_0')
    parser.add_argument('--city-destination',default='n4_4')
    parser.add_argument('--city-vehicles',type=int,default=180)
    parser.add_argument('--city-parking-slot',default=None)
    parser.add_argument('--outage',nargs=2,type=float,metavar=('BEGIN','END'),help='IoT blackout interval')
    args = parser.parse_args()
    if args.command=='serve':
        from kars.console import serve
        serve(args.port,not args.no_browser)
    elif args.command=='setup':
        print('SUMO:',binary('sumo'))
        print('Network:',build_network())
    elif args.command=='replay':
        from kars.replay import replay
        replay(args.output or ROOT/'outputs/demo_kars_delay_seed1')
    elif args.command=='run':
        run_simulation(args.scenario,args.algorithm,args.seed,args.duration,args.gui,args.delay,args.loss,
                       args.output,args.control_file,not args.no_plots,args.density,
                       {'realtime_factor':args.realtime,'delay_jitter':args.jitter,'sensor_range':args.sensor_range,
                        'outage_begin':args.outage[0] if args.outage else 30.,
                        'outage_end':args.outage[1] if args.outage else 30.,
                        'city_start':args.city_start,'city_destination':args.city_destination,
                        'city_vehicles':args.city_vehicles,'city_parking_slot':args.city_parking_slot})
    else:
        from kars.experiments import experiments, sweep
        if args.command=='experiments':
            experiments(args.repeats,args.duration,args.scenarios)
        else:
            sweep(args.repeats,args.duration)

if __name__=='__main__':
    main()
