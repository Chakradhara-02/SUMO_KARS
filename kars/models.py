from dataclasses import dataclass, asdict
from pathlib import Path
import yaml
import math

ROOT = Path(__file__).resolve().parents[1]

def load_config(overrides=None):
    config = yaml.safe_load((ROOT / 'config.yaml').read_text())
    config.update(overrides or {})
    for key in ('dt','simulation_dt','horizon','max_speed','max_states','lanes','lane_width',
                'safety_gap','vehicle_length','stale_timeout','duration','lane_change_duration','sensor_range'):
        if not math.isfinite(config[key]) or config[key] <= 0:
            raise ValueError(f'{key} must be positive')
    if config['min_acceleration'] >= 0 or config['max_acceleration'] <= 0:
        raise ValueError('Acceleration bounds must straddle zero')
    if config['simulation_dt'] > config['dt']:
        raise ValueError('simulation_dt cannot exceed planning dt')
    if config['lanes'] != 3:
        raise ValueError('The supplied road network has exactly three main lanes')
    if any(int(config[k]) != config[k] for k in ('horizon','max_states','lanes')):
        raise ValueError('horizon, max_states and lanes must be integers')
    for key in ('realtime_factor','delay_jitter','sensor_range'):
        if not math.isfinite(config[key]) or config[key] < 0:
            raise ValueError(f'{key} must be finite and nonnegative')
    if not 0 <= config['outage_begin'] <= config['outage_end']:
        raise ValueError('Outage interval must have 0 <= begin <= end')
    return config

@dataclass(frozen=True)
class State:
    x: float
    v: float
    lane: int
    t: float = 0.0
    lane_hold: float = 0.0
    lane_origin: int = -1

@dataclass
class Constraint:
    kind: str
    start: float
    end: float
    lane: int = -1
    speed: float = 0.0
    begin: float = 0.0
    finish: float = 1e9
    source: str = ''

@dataclass
class Vehicle:
    vehicle_id: str
    timestamp: float
    x: float
    y: float
    lane_id: str
    lane: int
    speed: float
    acceleration: float
    heading: float
    road_id: str
    traffic_light: str
    traffic_light_state: str
    speed_limit: float
    obstacle_information: str = ''
    length: float = 5.0
    width: float = 1.8
    lateral_position: float = 0.0
    z: float = 0.0
    signals: int = 0
    indicator_reason: str = ''

    def record(self):
        return asdict(self)
