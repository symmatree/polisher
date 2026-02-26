#!/usr/bin/env python3
"""
Render a small PNG preview of an ODM map: orthophoto as base, boundary = ortho extent.
Optional: if boundary.geojson (or *.geojson) exists in map dir, overlay it (coordinates
must be in the same CRS as the ortho, e.g. both UTM).
Usage: polisher/.venv/bin/python facts/render_odm_map_preview.py <map_output_dir> <output_png>
Requires: rasterio, matplotlib.
"""

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import rasterio


def find_ortho(map_dir: Path) -> Path | None:
    for p in (
        map_dir / "odm_orthophoto.tif",
        map_dir / "odm_orthophoto" / "odm_orthophoto.tif",
    ):
        if p.exists():
            return p
    return None


def find_geojson(map_dir: Path) -> Path | None:
    for name in ("boundary.geojson", "footprint.geojson"):
        if (map_dir / name).exists():
            return map_dir / name
    for p in map_dir.glob("*.geojson"):
        return p
    return None


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: render_odm_map_preview.py <map_output_dir> <output_png>", file=sys.stderr)
        return 1
    map_dir = Path(sys.argv[1])
    output_png = Path(sys.argv[2])
    if not map_dir.is_dir():
        print(f"Not a directory: {map_dir}", file=sys.stderr)
        return 1

    ortho_path = find_ortho(map_dir)
    if not ortho_path:
        print(f"No orthophoto found under {map_dir}", file=sys.stderr)
        return 1

    out_width = 600
    fig, ax = plt.subplots(figsize=(6, 4), dpi=100)

    with rasterio.open(ortho_path) as src:
        h, w = src.height, src.width
        scale = min(out_width / w, 400 / h, 1.0)
        out_shape = (int(h * scale), int(w * scale))
        data = src.read(1, out_shape=out_shape)
        left, bottom, right, top = src.bounds
        ax.imshow(data, extent=(left, right, bottom, top), cmap="gray", origin="upper")
        ax.set_aspect("equal")

        geojson_path = find_geojson(map_dir)
        if geojson_path:
            with open(geojson_path) as f:
                gj = json.load(f)
            xs, ys = [], []
            if gj.get("type") == "FeatureCollection" and gj.get("features"):
                for feat in gj["features"]:
                    geom = feat.get("geometry")
                    if geom and geom.get("type") == "Polygon":
                        ring = geom["coordinates"][0]
                        xs = [c[0] for c in ring]
                        ys = [c[1] for c in ring]
                        break
            elif gj.get("type") == "Polygon":
                ring = gj["coordinates"][0]
                xs, ys = [c[0] for c in ring], [c[1] for c in ring]
            if xs and ys:
                ax.plot(xs, ys, "r-", linewidth=1.5)
        else:
            ax.plot(
                [left, right, right, left, left],
                [bottom, bottom, top, top, bottom],
                "r-", linewidth=1.5,
            )

    ax.axis("off")
    output_png.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout(pad=0.1)
    plt.savefig(output_png, bbox_inches="tight", pad_inches=0.05)
    plt.close()
    print(str(output_png))
    return 0


if __name__ == "__main__":
    sys.exit(main())
