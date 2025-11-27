from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import math


def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2) ** 2) + math.cos(phi1) * math.cos(phi2) * (
        math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c  # Distance in meters


def get_decimal_from_dms(dms, ref):
    degrees = dms[0]
    minutes = dms[1]
    seconds = dms[2]

    decimal = degrees + minutes / 60.0 + seconds / 3600.0
    if ref in ["S", "W"]:
        decimal = -decimal
    return decimal


def extract_metadata_from_image(image_path: str) -> dict:
    """
    Extracts EXIF metadata, specifically GPS coordinates, from an image.
    """
    try:
        image = Image.open(image_path)
        exif = image._getexif()
        if not exif:
            return {}

        metadata = {}
        gps_info = {}

        for tag_id, value in exif.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == "GPSInfo":
                for t in value:
                    sub_tag = GPSTAGS.get(t, t)
                    gps_info[sub_tag] = value[t]
            elif tag == "DateTimeOriginal":
                metadata["date_taken"] = str(value)
            elif tag == "Make":
                metadata["camera_make"] = str(value)
            elif tag == "Model":
                metadata["camera_model"] = str(value)

        if gps_info:
            lat = None
            lon = None

            if "GPSLatitude" in gps_info and "GPSLatitudeRef" in gps_info:
                lat = get_decimal_from_dms(
                    gps_info["GPSLatitude"], gps_info["GPSLatitudeRef"]
                )

            if "GPSLongitude" in gps_info and "GPSLongitudeRef" in gps_info:
                lon = get_decimal_from_dms(
                    gps_info["GPSLongitude"], gps_info["GPSLongitudeRef"]
                )

            if lat is not None and lon is not None:
                metadata["gps"] = {"latitude": lat, "longitude": lon}

        return metadata
    except Exception as e:
        print(f"Error extracting metadata from {image_path}: {e}")
        return {}
