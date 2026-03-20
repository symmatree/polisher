#!/usr/bin/env python3
"""
Extract ODM run record from a map output directory: non-default options (from log.json
vs odm_option_defaults.json) and key stats (from odm_report/stats.json). Output is
markdown tables for pasting into map docs or aggregating into experiments comparison.

Usage: polisher/.venv/bin/python polisher/facts/collect_odm_run_record.py <map_output_dir>

Requires: log.json and odm_report/stats.json in the map dir. Defaults are read from
odm_option_defaults.json next to this script (generated from NodeODM odm_options_schema.json).
See facts repo kb/odm-maps-data-collection.md.
"""

import json
import sys
from pathlib import Path


def script_dir() -> Path:
    return Path(__file__).resolve().parent


def load_defaults() -> dict:
    p = script_dir() / "odm_option_defaults.json"
    if not p.exists():
        raise FileNotFoundError(f"Defaults file not found: {p}")
    return json.loads(p.read_text())


def option_value_display(opts: dict, key: str) -> str:
    v = opts.get(key)
    if v is None:
        return "—"
    if key == "boundary" and isinstance(v, dict):
        geom = v.get("geometry") or v
        coords = geom.get("coordinates") if isinstance(geom, dict) else None
        if coords and coords[0]:
            return f"custom polygon ({len(coords[0])} points)"
        return "custom polygon"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    return str(v)[:60]


def is_default(run_val, default_val, key: str) -> bool:
    if default_val is None and run_val is None:
        return True
    if default_val is None and run_val in ({}, ""):
        return True
    if key == "boundary":
        # Default is no boundary; run has boundary if it's a dict with coordinates
        if default_val in (None, "", {}):
            return not (isinstance(run_val, dict) and run_val.get("geometry"))
        return run_val == default_val
    if run_val == default_val:
        return True
    # Numeric coercion for comparison (e.g. 0 vs 0.0)
    if isinstance(run_val, (int, float)) and isinstance(default_val, (int, float)):
        return float(run_val) == float(default_val)
    return False


def _looks_like_zero_default(val) -> bool:
    """True for values that are very likely at their default (None, '', 0, False)."""
    if val is None or val == "":
        return True
    if val is False:
        return True
    if isinstance(val, (int, float)) and val == 0:
        return True
    return False


def non_default_options(log_options: dict, defaults: dict) -> list[tuple[str, str, bool]]:
    """Return (key, display_value, unknown) for each non-default option."""
    skip = {"project_path", "name"}
    out = []
    for key in sorted(log_options.keys()):
        if key in skip:
            continue
        unknown = key not in defaults
        run_val = log_options[key]
        default_val = defaults.get(key)
        if not unknown and is_default(run_val, default_val, key):
            continue
        if unknown and _looks_like_zero_default(run_val):
            continue
        out.append((key, option_value_display(log_options, key), unknown))
    return out


def format_table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return ""
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))
    sep = "| " + " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers)) + " |"
    line = "|" + "|".join("-" * (w + 2) for w in col_widths) + "|"
    lines = [sep, line]
    for row in rows:
        lines.append("| " + " | ".join(str(c).ljust(col_widths[i]) for i, c in enumerate(row)) + " |")
    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: collect_odm_run_record.py <map_output_dir>", file=sys.stderr)
        return 1
    map_dir = Path(sys.argv[1])
    if not map_dir.is_dir():
        print(f"Not a directory: {map_dir}", file=sys.stderr)
        return 1

    log_path = map_dir / "log.json"
    stats_path = map_dir / "odm_report" / "stats.json"
    if not log_path.exists():
        print(f"Missing: {log_path}", file=sys.stderr)
        return 1
    if not stats_path.exists():
        print(f"Missing: {stats_path}", file=sys.stderr)
        return 1

    defaults = load_defaults()
    log_data = json.loads(log_path.read_text())
    stats_data = json.loads(stats_path.read_text())
    options = log_data.get("options", {})

    # --- Non-default options ---
    non_default = non_default_options(options, defaults)
    print("### ODM options (non-default only)\n")
    if non_default:
        rows = [[k, v + (" (?)" if unknown else "")] for k, v, unknown in non_default]
        print(format_table(["Option", "Value"], rows))
        unknowns = [k for k, _, u in non_default if u]
        if unknowns:
            print(f"\n(?) Not in defaults file: {', '.join(unknowns)}")
    else:
        print("All options at default values.\n")
    print()

    # --- Processing statistics (date, start/end, area, steps_times) ---
    ps = stats_data.get("processing_statistics", {}) or {}
    print("### Processing statistics\n")
    rows = []
    if ps.get("date"):
        rows.append(["Report date", str(ps["date"])])
    if ps.get("start_date"):
        rows.append(["Capture start", str(ps["start_date"])])
    if ps.get("end_date"):
        rows.append(["Capture end", str(ps["end_date"])])
    if "area" in ps:
        rows.append(["Area (m²)", f"{ps['area']:.2f}"])
    steps = ps.get("steps_times", {}) or {}
    for name, secs in steps.items():
        if name == "Total Time":
            rows.append(["OpenSfM total (s)", f"{secs:.2f}"])
        else:
            rows.append([f"  {name} (s)", f"{secs:.2f}"])
    if rows:
        print(format_table(["Metric", "Value"], rows))
    print()

    # --- Features statistics ---
    fs = stats_data.get("features_statistics", {}) or {}
    print("### Features statistics\n")
    rows = []
    for group in ("detected_features", "reconstructed_features"):
        g = fs.get(group, {}) or {}
        for k, v in g.items():
            rows.append([f"{group}.{k}", str(v)])
    if rows:
        print(format_table(["Metric", "Value"], rows))
    print()

    # --- Reconstruction (subset) ---
    rs = stats_data.get("reconstruction_statistics", {}) or {}
    print("### Reconstruction\n")
    keys = [
        "initial_points_count", "initial_shots_count", "reconstructed_points_count",
        "reconstructed_shots_count", "observations_count", "average_track_length",
        "average_track_length_over_two",
    ]
    rows = []
    for k in keys:
        v = rs.get(k)
        if v is None:
            continue
        if k in ("average_track_length", "average_track_length_over_two"):
            rows.append([k, f"{float(v):.4f}"])
        else:
            rows.append([k, str(v)])
    if rows:
        print(format_table(["Metric", "Value"], rows))
    print()

    # --- Reprojection errors ---
    print("### Reprojection errors\n")
    rows = []
    for k in ("reprojection_error_normalized", "reprojection_error_pixels", "reprojection_error_angular"):
        v = rs.get(k)
        if v is not None:
            rows.append([k, f"{v:.6g}"])
    if rows:
        print(format_table(["Metric", "Value"], rows))
    print()

    # --- GPS errors ---
    gps = stats_data.get("gps_errors", {}) or {}
    print("### GPS errors\n")
    rows = []
    for key in ("mean", "std", "error", "average_error", "ce90", "le90"):
        v = gps.get(key)
        if v is None:
            continue
        if isinstance(v, dict) and "x" in v and "y" in v and "z" in v:
            rows.append([key, f"x={v['x']:.4f} y={v['y']:.4f} z={v['z']:.4f}"])
        elif isinstance(v, (int, float)):
            rows.append([key, f"{v:.6g}"])
        else:
            rows.append([key, str(v)])
    if rows:
        print(format_table(["Metric", "Value"], rows))
    print()

    # --- ODM processing statistics ---
    odm = stats_data.get("odm_processing_statistics", {}) or {}
    print("### ODM processing\n")
    rows = []
    if "total_time" in odm:
        rows.append(["Total time (s)", f"{odm['total_time']:.2f}"])
    if odm.get("total_time_human"):
        rows.append(["Total time (human)", str(odm["total_time_human"])])
    if "average_gsd" in odm:
        rows.append(["Average GSD (cm/px)", f"{odm['average_gsd']:.4f}"])
    if rows:
        print(format_table(["Metric", "Value"], rows))

    return 0


if __name__ == "__main__":
    sys.exit(main())
