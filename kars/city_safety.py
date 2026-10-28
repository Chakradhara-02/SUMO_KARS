"""Measured same-road clearance on roads with arbitrary headings and elevation."""
import math


def city_collision_risk(ego, vehicles):
    heading = math.radians(ego.heading)
    forward = (math.sin(heading), math.cos(heading))
    gaps, ttcs = [], []
    for other in vehicles:
        if other.vehicle_id == ego.vehicle_id or other.road_id != ego.road_id or abs(other.z-ego.z) > 3:
            continue
        if math.cos(math.radians(other.heading-ego.heading)) < .8:
            continue
        dx, dy = other.x-ego.x, other.y-ego.y
        ahead = dx*forward[0]+dy*forward[1]
        side = abs(dx*forward[1]-dy*forward[0])
        if ahead <= 0 or side > (ego.width+other.width)/2 + .2:
            continue
        gap = ahead-other.length
        gaps.append(gap)
        closing = ego.speed-other.speed
        if closing > .01:
            ttcs.append(max(0., gap)/closing)
    return min(gaps) if gaps else None, min(ttcs) if ttcs else None
