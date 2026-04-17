#!/usr/bin/env python3
"""
Render a small PNG preview of an imageset: markers at each image position, with a
chevron showing GPSImgDirection (heading) when present.
Optional: --ortho <path> to use an orthophoto as base (ortho must be georeferenced;
script will plot points in lat/lon and expect ortho in same CRS or will use ortho bounds).
Usage: polisher/.venv/bin/python facts/render_imageset_map_preview.py <imageset_folder> <output_png> [--ortho <ortho.tif>]
Requires: Pillow, matplotlib. For --ortho: rasterio.
Matplotlib uses ~/.config by default for its config/cache; if that is not writable (e.g. headless,
sandbox), set MPLCONFIGDIR to a writable directory before running.
"""

import argparse
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
from PIL.ExifTags import IFD, GPS


def rational_to_float(r):
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
    if not dms or len(dms) != 3:
        return None
    d = rational_to_float(dms[0])
    m = rational_to_float(dms[1])
    s = rational_to_float(dms[2])
    if d is None or m is None or s is None:
        return None
    return d + m / 60.0 + s / 3600.0


def collect_positions_and_heading(folder: Path):
    """Yield (lat, lon, heading_deg or None) for each image with GPS."""
    extensions = {".jpg", ".jpeg", ".JPG", ".JPEG"}
    for path in sorted(folder.iterdir()):
        if not path.is_file() or path.suffix not in extensions:
            continue
        try:
            with Image.open(path) as img:
                exif = img.getexif()
                if exif is None:
                    continue
                gps_ifd = exif.get_ifd(IFD.GPSInfo)
                if not gps_ifd:
                    continue
                lat_val = gps_ifd.get(GPS.GPSLatitude)
                lon_val = gps_ifd.get(GPS.GPSLongitude)
                lat_ref = gps_ifd.get(GPS.GPSLatitudeRef, "N")
                lon_ref = gps_ifd.get(GPS.GPSLongitudeRef, "E")
                if isinstance(lat_ref, bytes):
                    lat_ref = lat_ref.decode("ascii", errors="ignore").strip()
                if isinstance(lon_ref, bytes):
                    lon_ref = lon_ref.decode("ascii", errors="ignore").strip()
                lat = dms_to_decimal(lat_val)
                lon = dms_to_decimal(lon_val)
                if lat is None or lon is None:
                    continue
                if lat_ref == "S":
                    lat = -lat
                if lon_ref == "W":
                    lon = -lon
                heading = None
                dir_val = gps_ifd.get(GPS.GPSImgDirection)
                if dir_val is not None:
                    h = rational_to_float(dir_val)
                    if h is not None:
                        heading = float(h)  # degrees from true North
                yield (lat, lon, heading)
        except Exception:
            continue


def main() -> int:
    parser = argparse.ArgumentParser(description="Render imageset map preview with position and heading.")
    parser.add_argument("imageset_folder", type=Path, help="Path to imageset image folder")
    parser.add_argument("output_png", type=Path, help="Output PNG path (e.g. in facts repo for embedding)")
    parser.add_argument("--ortho", type=Path, default=None, help="Optional orthophoto GeoTIFF as base layer")
    args = parser.parse_args()

    if not args.imageset_folder.is_dir():
        print(f"Not a directory: {args.imageset_folder}", file=sys.stderr)
        return 1

    points = list(collect_positions_and_heading(args.imageset_folder))
    if not points:
        print("No GPS positions found in images", file=sys.stderr)
        return 1

    lats = [p[0] for p in points]
    lons = [p[1] for p in points]
    fig, ax = plt.subplots(figsize=(6, 4), dpi=100)

    use_ortho = False
    ortho_bounds = None
    ortho_crs = None
    warp_transform = None
    # Optional ortho base: transform WGS84 (lon, lat) to ortho CRS and plot in ortho coords.
    if args.ortho and args.ortho.exists():
        try:
            import rasterio
            from rasterio.warp import transform as _warp_transform
            warp_transform = _warp_transform
            with rasterio.open(args.ortho) as src:
                ortho_crs = src.crs
                ortho_bounds = src.bounds
                h, w = src.height, src.width
                scale = min(600 / w, 400 / h, 1.0)
                out_shape = (int(h * scale), int(w * scale))
                data = src.read(1, out_shape=out_shape)
                left, bottom, right, top = src.bounds
                ax.imshow(data, extent=(left, right, bottom, top), cmap="gray", origin="upper")
                if ortho_crs and str(ortho_crs) != "EPSG:4326":
                    xs, ys = warp_transform("EPSG:4326", ortho_crs, lons, lats)
                    use_ortho = True
                else:
                    xs, ys = lons, lats
                    use_ortho = True
        except ImportError:
            xs, ys = lons, lats
        except Exception:
            xs, ys = lons, lats
    else:
        xs, ys = lons, lats

    if use_ortho and ortho_bounds is not None:
        ax.set_xlim(ortho_bounds.left, ortho_bounds.right)
        ax.set_ylim(ortho_bounds.bottom, ortho_bounds.top)
        ax.set_aspect("equal")
    else:
        ax.set_xlim(min(lons) - 0.0002, max(lons) + 0.0002)
        ax.set_ylim(min(lats) - 0.0002, max(lats) + 0.0002)
        ax.set_aspect("equal")

    ax.scatter(xs, ys, c="red", s=4, alpha=0.8, zorder=2)
    # Chevrons for heading: degrees from North, clockwise. 0 = N, 90 = E.
    arrow_deg = 0.00015
    for i, (lat, lon, heading) in enumerate(points):
        if heading is None:
            continue
        rad = math.radians(heading)
        d_lon = arrow_deg * math.sin(rad)
        d_lat = arrow_deg * math.cos(rad)
        if use_ortho and ortho_crs and warp_transform:
            end_lons, end_lats = [lon + d_lon], [lat + d_lat]
            start_xs, start_ys = warp_transform("EPSG:4326", ortho_crs, [lon], [lat])
            end_xs, end_ys = warp_transform("EPSG:4326", ortho_crs, end_lons, end_lats)
            ax.annotate(
                "", xy=(end_xs[0], end_ys[0]), xytext=(start_xs[0], start_ys[0]),
                arrowprops=dict(arrowstyle="->", color="blue", lw=0.8),
            )
        else:
            ax.annotate(
                "", xy=(lon + d_lon, lat + d_lat), xytext=(lon, lat),
                arrowprops=dict(arrowstyle="->", color="blue", lw=0.8),
            )
    ax.axis("off")
    args.output_png.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout(pad=0.1)
    plt.savefig(args.output_png, bbox_inches="tight", pad_inches=0.05)
    plt.close()
    print(str(args.output_png))
    return 0


if __name__ == "__main__":
    sys.exit(main())
