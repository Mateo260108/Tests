import math
lambda_km = 4.0

def haversine(lat1, lon1, lat2, lon2):
    earth_radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon1 - lon2)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * earth_radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def parse_coords(place):
    try:
        return float(place.get("lat")), float(place.get("lon"))
    except (ValueError, TypeError):
        return None, None

def apply_proximity_order(places, reference_places, mode="rural", decay_km=lambda_km):
    ref_coords = []
    for reference in reference_places:
        rlat, rlon = parse_coords(reference)
        if rlat is not None and rlon is not None:
            ref_coords.append((rlat, rlon))

    ordered = []
    no_coords = []

    for place in places:
        item = dict(place)
        lat, lon = parse_coords(item)
        if lat is None or lon is None:
            item["score_s"] = "" 
            no_coords.append(item)
            continue

        score_s = 0.0
        for rlat, rlon in ref_coords:
            distance = haversine(lat, lon, rlat, rlon)
            if distance > 0.001:
                score_s += math.exp(-distance / decay_km)

        item["score_s"] = round(score_s, 4)
        ordered.append(item)

    reverse_mode = mode == "urban"
    ordered.sort(key=lambda x: x["score_s"], reverse=reverse_mode)
    return ordered + no_coords
