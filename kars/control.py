"""Execute lane-level plans with bounded acceleration and committed lane changes."""


class TrajectoryTracker:
    def __init__(self, config):
        self.config = config
        self.lane_target = None
        self.lane_started = -1e9
        self.last_speed = None

    def command(self, connection, ego, now, requested_speed, requested_lane, emergency=False):
        cfg = self.config
        speed = max(0., min(cfg['max_speed'], requested_speed))
        speed = min(speed, ego.speed + cfg['max_acceleration'] * cfg['simulation_dt'])
        speed = max(speed, ego.speed + cfg['min_acceleration'] * cfg['simulation_dt'])
        connection.vehicle.setSpeed('ego', float(speed))
        completed = self.lane_target == ego.lane and abs(ego.lateral_position) < .05
        expired = now - self.lane_started >= cfg['lane_change_duration'] + cfg['dt']
        if completed or expired:
            self.lane_target = None
        allowed = ego.road_id in ('in', 'out') and not (80 <= ego.x <= 140)
        if not emergency and allowed and self.lane_target is None and requested_lane != ego.lane:
            requested_lane = ego.lane + (1 if requested_lane > ego.lane else -1)
            if 0 <= requested_lane < cfg['lanes']:
                self.lane_target = requested_lane
                self.lane_started = now
                connection.vehicle.changeLane('ego', requested_lane, cfg['lane_change_duration'] + cfg['dt'])
        tracking_error = ego.speed-self.last_speed if self.last_speed is not None else 0.
        self.last_speed = speed
        return {'command_speed': speed, 'command_lane': self.lane_target if self.lane_target is not None else ego.lane,
                'speed_tracking_error': tracking_error,
                'lane_change_active': self.lane_target is not None}


def collision_risk(ego, vehicles):
    """Bumper clearance and time-to-collision from measured current positions."""
    gaps, ttcs = [], []
    for other in vehicles:
        if other.vehicle_id == ego.vehicle_id or other.road_id not in ('in', 'out') or other.x <= ego.x:
            continue
        if abs(other.y - ego.y) > (other.width + ego.width) / 2 + .2:
            continue
        gap = other.x - other.length - ego.x
        gaps.append(gap)
        closing = ego.speed - other.speed
        if closing > .01:
            ttcs.append(max(0., gap) / closing)
    return min(gaps) if gaps else None, min(ttcs) if ttcs else None
