import os
import csv
import math

neighbour_radius = 3.0
max_neighbours_allowed = 5

urban_terms = (
    "radisson", "scandic", "hilton", "marriott", "best western",
    "thon", "clarion", "comfort hotel", "quality hotel", "strawberry",
    "sokos", "lapland hotels", "nordic choice", "first hotel",
    "airport", "central station", "city center", "city centre", "downtown",
    "centrum"
)

def distance_haversine(lat1, lon1, lat2, lon2):
    earth_radius_km = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * earth_radius_km * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def get_coords(row):
    lat_raw = row.get("lat") or row.get("@lat")
    lon_raw = row.get("lon") or row.get("@lon")
    try:
        return float(lat_raw), float(lon_raw)

    except (ValueError, TypeError):
        return None, None

def chain_or_city(row):
    values = list(row.values())
    name = (row.get("name") or (values[1] if len(values) > 1 else "")).lower()
    return any(term in name for term in urban_terms) 

def count_neighbours(lat, lon, coords, radius_km):
    neighbours = 0
    for x_lat, x_lon in coords:
        distance = distance_haversine(lat, lon, x_lat, x_lon)
        if 0.001 < distance <= radius_km:
            neighbours += 1

    return neighbours

def processing_filter(iso_code):
    folder = f"{iso_code}_filtered"
    input_path = os.path.join(folder, f"all_emails_{iso_code}.csv")
    map_places_path = f"hotels_{iso_code}.csv"
    output_path = os.path.join(folder, f"geofiltered_emails_{iso_code}.csv")

    if not os.path.exists(input_path):
        print("Email list not found. ")
        return

    with open(input_path, "r", encoding="utf-8") as file:
        rows_emails = list(csv.DictReader(file, delimiter='\t'))

    if os.path.exists(map_places_path):
        with open(map_places_path, "r", encoding="utf-8") as file:
            rows_map = list(csv.DictReader(file, delimiter='\t'))

    else:
        print("Raw file not found. ")
        return

    map_coords = [
        coords for coords in (get_coords(r) for r in rows_map)
        if coords[0] is not None and coords[1] is not None
    ]

    final_targets = []
    for row in rows_emails:
        if chain_or_city(row):
            continue

        lat, lon = get_coords(row)
        if lat is None or lon is None:
            continue

        neighbours = count_neighbours(lat, lon, map_coords, neighbour_radius)
        if neighbours <= max_neighbours_allowed:
            row["nearby_neigbours"] = neighbours
            final_targets.append(row)

    fieldnames = final_targets[0].keys()
    with open(output_path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter='\t')
        writer.writeheader()
        writer.writerows(final_targets)

    print("Final processing and filtering done!")

if __name__ == "__main__":
    processing_filter("IS")
