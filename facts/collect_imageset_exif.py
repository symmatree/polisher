#!/usr/bin/env python3
"""
Collect EXIF-derived summary for an imageset folder (image count, altitude range, bbox).
Uses Pillow; run with polisher venv: polisher/.venv/bin/python facts/collect_imageset_exif.py <folder_path>
Output: one line KEY=value per metric, for use when updating Datasets/imagesets-*.md.
Tags used: GPS IFD (0x8825), altitude tag 6, lat tag 2, lon tag 4; lon negated if ref is W.
See facts repo kb/imagesets-data-collection.md.
"""

import sys
from pathlib import Path

from PIL import Image
from PIL.ExifTags import IFD, GPS


def rational_to_float(r):
    """Single rational: (num, den) tuple or IFDRational -> float."""
    if r is None:
        return None
    try:
        if hasattr(r, "numerator") and hasattr(r, "denominator"):
            num, den = r.numerator, r.denominator
        elif isinstance(r, (tuple, list)) and len(r) == 2:
            num, den = r[0], r[1]
        else:
            return None
        return float(num) / float(den) if den else None
    except (TypeError, ZeroDivisionError):
        return None


def dms_to_decimal(dms):
    """GPS (deg, min, sec) as three rationals (tuple or IFDRational) -> decimal degrees."""
    if not dms or len(dms) != 3:
        return None
    d = rational_to_float(dms[0])
    m = rational_to_float(dms[1])
    s = rational_to_float(dms[2])
    if d is None or m is None or s is None:
        return None
    return d + m / 60.0 + s / 3600.0


def main():
    if len(sys.argv) != 2:
        print("Usage: collect_imageset_exif.py <imageset_folder_path>", file=sys.stderr)
        sys.exit(1)
    folder = Path(sys.argv[1])
    if not folder.is_dir():
        print(f"Not a directory: {folder}", file=sys.stderr)
        sys.exit(1)

    extensions = {".jpg", ".jpeg", ".JPG", ".JPEG"}
    image_paths = sorted(
        p for p in folder.iterdir()
        if p.is_file() and p.suffix in extensions
    )
    image_count = len(image_paths)

    alts = []
    lats = []
    lons = []

    for path in image_paths:
        try:
            with Image.open(path) as img:
                exif = img.getexif()
                if exif is None:
                    continue
                gps_ifd = exif.get_ifd(IFD.GPSInfo)
                if not gps_ifd:
                    continue

                # Altitude (tag 6): rational (num, den) -> meters
                alt_val = gps_ifd.get(GPS.GPSAltitude)
                if alt_val is not None:
                    a = rational_to_float(alt_val)
                    if a is not None:
                        alts.append(a)

                # Lat/lon: tags 2 and 4; refs 1 and 3 for S/W
                lat_val = gps_ifd.get(GPS.GPSLatitude)
                lon_val = gps_ifd.get(GPS.GPSLongitude)
                lat_ref = gps_ifd.get(GPS.GPSLatitudeRef, "N")
                lon_ref = gps_ifd.get(GPS.GPSLongitudeRef, "E")
                if isinstance(lat_ref, bytes):
                    lat_ref = lat_ref.decode("ascii", errors="ignore").strip()
                if isinstance(lon_ref, bytes):
                    lon_ref = lon_ref.decode("ascii", errors="ignore").strip()

                lat = dms_to_decimal(lat_val) if lat_val else None
                lon = dms_to_decimal(lon_val) if lon_val else None
                if lat is not None:
                    if lat_ref == "S":
                        lat = -lat
                    lats.append(lat)
                if lon is not None:
                    if lon_ref == "W":
                        lon = -lon
                    lons.append(lon)
        except Exception as e:
            print(f"Warning: {path.name}: {e}", file=sys.stderr)

    # Output for doc update
    print(f"IMAGE_COUNT={image_count}")
    if alts:
        print(f"ALT_MIN={min(alts):.1f}")
        print(f"ALT_MAX={max(alts):.1f}")
    else:
        print("ALT_MIN=")
        print("ALT_MAX=")
    if lats and lons:
        print(f"LAT_MIN={min(lats):.6f}")
        print(f"LAT_MAX={max(lats):.6f}")
        print(f"LON_MIN={min(lons):.6f}")
        print(f"LON_MAX={max(lons):.6f}")
    else:
        print("LAT_MIN=")
        print("LAT_MAX=")
        print("LON_MIN=")
        print("LON_MAX=")


if __name__ == "__main__":
    main()
