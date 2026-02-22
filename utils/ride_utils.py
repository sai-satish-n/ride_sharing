from shapely.geometry import shape, Point
import math


def point_in_geojson(lat, lng, geojson):
    """
    geojson: Polygon or MultiPolygon (GeoJSON)
    """
    try:
        polygon = shape(geojson)
        point = Point(lng, lat)  # NOTE: lng first
        return polygon.contains(point)
    except Exception:
        return False


def haversine_distance(lat1, lng1, lat2, lng2):
    """
    Calculate the great-circle distance between two points on the Earth.
    Returns distance in kilometers.
    """
    # Convert decimal degrees to radians
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])

    # Haversine formula
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2)**2
    c = 2 * math.asin(math.sqrt(a))

    # Radius of Earth in kilometers (mean radius)
    r = 6371
    return c * r
