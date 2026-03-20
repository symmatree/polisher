#!/usr/bin/env python3
"""
Fetch every UniFi device from the Integration API, get full detail (interfaces.ports
and interfaces.radios), dump to a JSON file.
Usage: UNIFI_API_KEY=xxx python3 fetch_device_interfaces.py [output.json]
"""
import json
import os
import sys
import urllib.request
import ssl

SITE_UUID = "88f7af54-98f8-306a-a1c7-c9349722b1f6"
BASE = "https://10.0.0.1/proxy/network/integration/v1"
DEFAULT_OUTPUT = "unifi_devices_interfaces.json"


def req(path: str, api_key: str) -> bytes:
    url = f"{BASE}{path}"
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    r = urllib.request.Request(url, headers={"Accept": "application/json", "X-API-Key": api_key})
    with urllib.request.urlopen(r, context=ctx, timeout=15) as res:
        return res.read()


def main():
    api_key = os.environ.get("UNIFI_API_KEY", "").strip()
    if not api_key:
        print("Set UNIFI_API_KEY", file=sys.stderr)
        raise SystemExit(1)

    out_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUTPUT

    raw = req(f"/sites/{SITE_UUID}/devices?limit=100", api_key)
    devices = json.loads(raw)
    if not isinstance(devices, list):
        devices = devices.get("data", devices) or []

    result = []
    for d in devices:
        if not isinstance(d, dict):
            continue
        dev_id = d.get("id")
        if not dev_id:
            continue
        detail_raw = req(f"/sites/{SITE_UUID}/devices/{dev_id}", api_key)
        detail = json.loads(detail_raw)
        interfaces = detail.get("interfaces") or {}
        result.append({
            "id": detail.get("id"),
            "name": detail.get("name"),
            "macAddress": detail.get("macAddress"),
            "model": detail.get("model"),
            "state": detail.get("state"),
            "interfaces": {
                "ports": interfaces.get("ports"),
                "radios": interfaces.get("radios"),
            },
        })

    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)

    print(out_path, file=sys.stderr)


if __name__ == "__main__":
    main()
