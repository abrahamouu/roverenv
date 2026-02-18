import csv
import os


def load_waypoints(filepath):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Waypoint file not found: {filepath}")

    waypoints = []

    with open(filepath, newline='') as f:
        sample = f.read(1024)
        f.seek(0)
        has_header = csv.Sniffer().has_header(sample)
        reader = csv.reader(f)

        if has_header:
            header = next(reader)  # skip header row
            # Detect which columns hold lat/lon
            header_lower = [h.strip().lower() for h in header]
            lat_col, lon_col = _find_lat_lon_columns(header_lower)
        else:
            lat_col, lon_col = 0, 1  # assume first two columns

        for line_num, row in enumerate(reader, start=2 if has_header else 1):
            if not row or all(cell.strip() == '' for cell in row):
                continue  # skip blank lines
            try:
                lat = float(row[lat_col].strip())
                lon = float(row[lon_col].strip())
            except (IndexError, ValueError) as e:
                print(f"Warning: skipping line {line_num}: {row} ({e})")
                continue

            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                print(f"Warning: skipping invalid coordinates on line {line_num}: ({lat}, {lon})")
                continue

            waypoints.append((lat, lon))

    if not waypoints:
        raise ValueError(f"No valid waypoints found in {filepath}")

    print(f"Loaded {len(waypoints)} waypoints from {filepath}")
    return waypoints


def _find_lat_lon_columns(header_lower):
    lat_col = lon_col = None
    for i, name in enumerate(header_lower):
        if 'lat' in name:
            lat_col = i
        if 'lon' in name:
            lon_col = i
    if lat_col is None or lon_col is None:
        # Fall back to first two columns
        print("Warning: could not detect lat/lon columns from header, using columns 0 and 1")
        return 0, 1
    return lat_col, lon_col


# Quick test
if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "waypoints.csv"
    wps = load_waypoints(path)
    for i, (lat, lon) in enumerate(wps):
        print(f"  WP{i+1}: {lat:.6f}, {lon:.6f}")