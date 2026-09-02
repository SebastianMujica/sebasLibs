"""Pillow-based EXIF metadata extractor."""

from __future__ import annotations

from pathlib import Path

try:
    from PIL import Image
    from PIL.ExifTags import GPSTAGS, TAGS

    _HAS_PILLOW = True
except ImportError:
    Image = None  # type: ignore
    GPSTAGS = {}  # type: ignore
    TAGS = {}  # type: ignore
    _HAS_PILLOW = False

from ..core.ports import MetadataExtractorPort


class PillowMetadataExtractor(MetadataExtractorPort):
    def extract_exif(self, file_path: Path) -> dict:
        if not _HAS_PILLOW or Image is None:
            return {}

        result: dict = {}
        try:
            with Image.open(file_path) as img:
                exif_data = img.getexif()

                if exif_data:
                    for tag_id, value in exif_data.items():
                        tag = TAGS.get(tag_id, tag_id)
                        result[str(tag)] = value

                date_taken = result.get("DateTimeOriginal") or result.get("DateTime")
                if date_taken:
                    from datetime import datetime

                    try:
                        result["date_taken_parsed"] = datetime.strptime(str(date_taken), "%Y:%m:%d %H:%M:%S")
                    except ValueError:
                        pass

                camera = result.get("Make", "")
                model = result.get("Model", "")
                if camera or model:
                    result["camera"] = f"{camera} {model}".strip()

                result["resolution"] = f"{img.width}x{img.height}"

                gps = exif_data.get_ifd(GPSTAGS)
                if gps:
                    result["gps"] = self._parse_gps(gps)

        except Exception:
            return {}

        return result

    def _parse_gps(self, gps_ifd: dict) -> dict:
        """Simplified GPS parsing."""
        lat = gps_ifd.get(GPSTAGS.get("Latitude"))
        lat_ref = gps_ifd.get(GPSTAGS.get("LatitudeRef"), "N")
        lon = gps_ifd.get(GPSTAGS.get("Longitude"))
        lon_ref = gps_ifd.get(GPSTAGS.get("LongitudeRef"), "E")

        if lat and lon:
            lat_dec = self._convert_to_degrees(lat)
            lon_dec = self._convert_to_degrees(lon)
            if lat_ref == "S":
                lat_dec = -lat_dec
            if lon_ref == "W":
                lon_dec = -lon_dec
            return {"latitude": lat_dec, "longitude": lon_dec}
        return {}

    def _convert_to_degrees(self, value: list) -> float:
        """Convert GPS DMS to decimal degrees."""
        d, m, s = value
        return float(d) + float(m) / 60 + float(s) / 3600
