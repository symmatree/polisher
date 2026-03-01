#!/usr/bin/env python3
"""
Compare ODM images.json (all inputs) to odm_report/shots.geojson (reconstructed)
to identify dropped images and produce:
  1. A map PNG: green = reconstructed, red = dropped
  2. A markdown file listing dropped images with position and camera info

Usage:
  polisher/.venv/bin/python polisher/facts/analyze_odm_reconstruction.py \
      <odm_output_dir> <output_dir>

<odm_output_dir>  ODM output on NAS (e.g. /mnt/d/odm-maps/bond_ave-2026-02-21-house-2)
<output_dir>      Where to write reconstruction_status.png and dropped-images.md
                  (typically the map doc dir in the facts repo)

Requires: matplotlib, rasterio (for orthophoto background)
"""

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def load_input_images(odm_dir: Path) -> list[dict]:
    path = odm_dir / "images.json"
    if not path.exists():
        print(f"Not found: {path}", file=sys.stderr)
        sys.exit(1)
    with open(path) as f:
        return json.load(f)


def load_reconstructed_shots(odm_dir: Path) -> dict[str, dict]:
    """Return {filename: {lon, lat, translation: [x,y,z]}} for reconstructed shots."""
    path = odm_dir / "odm_report" / "shots.geojson"
    if not path.exists():
        print(f"Not found: {path}", file=sys.stderr)
        sys.exit(1)
    with open(path) as f:
        gj = json.load(f)
    result = {}
    for feat in gj["features"]:
        props = feat["properties"]
        coords = feat["geometry"]["coordinates"]
        result[props["filename"]] = {
            "lon": coords[0],
            "lat": coords[1],
            "translation": props["translation"],
        }
    return result


def find_ortho(odm_dir: Path) -> Path | None:
    for p in (
        odm_dir / "odm_orthophoto" / "odm_orthophoto.tif",
        odm_dir / "odm_orthophoto.tif",
    ):
        if p.exists():
            return p
    return None


def transform_coords(lons, lats, target_crs):
    """Transform WGS84 lon/lat lists to target CRS. Returns (xs, ys)."""
    from rasterio.warp import transform
    xs, ys = transform("EPSG:4326", target_crs, lons, lats)
    return xs, ys


def render_map(reconstructed: list[dict], dropped: list[dict], shots: dict[str, dict],
               output_png: Path, odm_dir: Path | None = None):
    fig, ax = plt.subplots(figsize=(8, 6), dpi=120)

    use_ortho = False
    ortho_crs = None

    if odm_dir:
        ortho_path = find_ortho(odm_dir)
        if ortho_path:
            try:
                import rasterio
                with rasterio.open(ortho_path) as src:
                    ortho_crs = src.crs
                    h, w = src.height, src.width
                    scale = min(800 / w, 600 / h, 1.0)
                    out_shape = (src.count, int(h * scale), int(w * scale))
                    data = src.read(out_shape=out_shape)
                    left, bottom, right, top = src.bounds

                    if src.count >= 3:
                        import numpy as np
                        rgb = np.moveaxis(data[:3], 0, -1)
                        ax.imshow(rgb, extent=(left, right, bottom, top), origin="upper",
                                  zorder=0, alpha=0.8)
                    else:
                        ax.imshow(data[0], extent=(left, right, bottom, top),
                                  cmap="gray", origin="upper", zorder=0, alpha=0.8)
                    use_ortho = True
                    print(f"Ortho: {ortho_path} ({src.crs})")
            except Exception as e:
                print(f"Warning: could not load ortho: {e}", file=sys.stderr)

    if use_ortho and ortho_crs:
        # Reconstructed: arrow from original GPS to reconstructed position
        if reconstructed:
            orig_lons = [img["longitude"] for img in reconstructed]
            orig_lats = [img["latitude"] for img in reconstructed]
            orig_xs, orig_ys = transform_coords(orig_lons, orig_lats, ortho_crs)

            for i, img in enumerate(reconstructed):
                shot = shots.get(img["filename"])
                if shot and "translation" in shot:
                    recon_x, recon_y = shot["translation"][0], shot["translation"][1]
                    ax.annotate(
                        "", xy=(recon_x, recon_y), xytext=(orig_xs[i], orig_ys[i]),
                        arrowprops=dict(arrowstyle="->", color="#4CAF50", lw=0.6, alpha=0.5),
                        zorder=2,
                    )

            recon_xs = []
            recon_ys = []
            for img in reconstructed:
                shot = shots.get(img["filename"])
                if shot and "translation" in shot:
                    recon_xs.append(shot["translation"][0])
                    recon_ys.append(shot["translation"][1])
            ax.scatter(recon_xs, recon_ys, c="#3D8B40", s=12, alpha=1.0, zorder=4,
                       label=f"Reconstructed ({len(reconstructed)})", edgecolors="white", linewidths=0.3)

        if dropped:
            dx, dy = transform_coords(
                [img["longitude"] for img in dropped],
                [img["latitude"] for img in dropped],
                ortho_crs,
            )
            ax.scatter(dx, dy, c="#F44336", s=30, alpha=0.9, zorder=5, marker="x",
                       linewidths=1.5, label=f"Dropped ({len(dropped)})")
    else:
        if reconstructed:
            rx = [img["longitude"] for img in reconstructed]
            ry = [img["latitude"] for img in reconstructed]
            ax.scatter(rx, ry, c="#4CAF50", s=6, alpha=0.5, zorder=2,
                       label=f"Reconstructed ({len(reconstructed)})")
        if dropped:
            dx = [img["longitude"] for img in dropped]
            dy = [img["latitude"] for img in dropped]
            ax.scatter(dx, dy, c="#F44336", s=20, alpha=0.9, zorder=3, marker="x",
                       label=f"Dropped ({len(dropped)})")

    ax.set_aspect("equal")
    ax.legend(loc="upper left", fontsize=8, framealpha=0.8)
    total = len(reconstructed) + len(dropped)
    ax.set_title(f"Reconstruction status: {len(reconstructed)} used, {len(dropped)} dropped of {total} input",
                 fontsize=10)
    ax.axis("off")
    output_png.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(output_png, bbox_inches="tight", pad_inches=0.1)
    plt.close()
    print(f"Map: {output_png}")


def render_markdown(dropped: list[dict], total: int, reconstructed_count: int, output_md: Path):
    lines = [
        f"# Dropped images ({len(dropped)} of {total})",
        "",
        f"Reconstructed: {reconstructed_count} | Dropped: {len(dropped)} | Total: {total}",
        "",
        "Images present in `images.json` but absent from `odm_report/shots.geojson`.",
        "",
        "| Filename | Latitude | Longitude | Altitude (m) | Exposure | ISO | f/ |",
        "|----------|----------|-----------|-------------|----------|-----|----|",
    ]
    for img in sorted(dropped, key=lambda x: x["filename"]):
        exp = img.get("exposure_time")
        exp_str = f"1/{int(1/exp)}" if exp and exp > 0 and exp < 1 else (str(exp) if exp else "")
        iso = img.get("iso_speed", "")
        fn = img.get("fnumber", "")
        lines.append(
            f"| {img['filename']} | {img['latitude']:.6f} | {img['longitude']:.6f} "
            f"| {img.get('altitude', ''):.1f} | {exp_str} | {iso} | {fn} |"
        )

    lines.append("")
    lines.append("![[reconstruction_status.png]]")
    lines.append("")

    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text("\n".join(lines))
    print(f"Markdown: {output_md}")


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: analyze_odm_reconstruction.py <odm_output_dir> <output_dir>", file=sys.stderr)
        return 1

    odm_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])

    all_images = load_input_images(odm_dir)
    shots = load_reconstructed_shots(odm_dir)

    reconstructed = []
    dropped = []
    for img in all_images:
        if img["filename"] in shots:
            reconstructed.append(img)
        else:
            dropped.append(img)

    print(f"Total: {len(all_images)}, Reconstructed: {len(reconstructed)}, Dropped: {len(dropped)}")

    render_map(reconstructed, dropped, shots, output_dir / "reconstruction_status.png", odm_dir)
    render_markdown(dropped, len(all_images), len(reconstructed), output_dir / "dropped-images.md")

    return 0


if __name__ == "__main__":
    sys.exit(main())
