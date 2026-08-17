#!/usr/bin/env python3
"""
Build a static, uploadable snapshot of the Hackney Tree Filter.

    python3 build.py

Fetches the current tree data directly from Hackney's GeoServer WFS (this
script makes the HTTP request itself, so no browser and no proxy is
involved), extracts just the fields the app needs, and writes a
self-contained dist/ folder:

    dist/index.html   a copy of the app
    dist/trees.json   cached tree data + a build timestamp

Upload dist/ to any static host (GitHub Pages, Netlify, S3, ...) as-is — the
app loads trees.json directly, so no server or proxy is required there.
Re-run this script whenever you want a fresher snapshot; tree data doesn't
change often, so daily/weekly is plenty.

Standard library only.
"""

import json
import os
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

UPSTREAM = "https://map2.hackney.gov.uk/geoserver/ows"
HTML_NAME = "index.html"
OUT_DIR = "dist"
MAX_FEATURES = 60000

# Keep in sync with CONFIG.layers in index.html.
LAYERS = [
    "greenspaces:tree",                        # confirmed: ~39k street/park trees
    "planning:tree_preservation_order_point",   # confirmed-working fallback
]

# Keep in sync with CONFIG.*Fields in index.html.
BINOMIAL_FIELDS = ["species_name", "botanical_name", "scientific_name", "latin_name",
                    "binomial", "species", "tree_species", "spp"]
COMMON_FIELDS = ["common_name", "commonname", "common_nam", "common", "vernacular"]
AGE_FIELDS = ["age", "maturity", "age_class", "life_stage", "maturity_class"]
ADDRESS_FIELDS = ["full_address", "address", "street", "location", "site_name",
                   "sitename", "treelocn", "addnlocn"]

HERE = os.path.dirname(os.path.abspath(__file__))


def fetch_layer(layer):
    query = urllib.parse.urlencode({
        "service": "WFS", "version": "2.0.0", "request": "GetFeature",
        "typeNames": layer, "outputFormat": "application/json",
        "srsName": "EPSG:4326", "count": str(MAX_FEATURES),
    })
    req = urllib.request.Request(f"{UPSTREAM}?{query}",
                                  headers={"User-Agent": "hackney-tree-filter/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r).get("features") or []


def pick(props, candidates):
    lower = {k.lower(): v for k, v in props.items()}
    for cand in candidates:
        v = lower.get(cand)
        if v is not None and str(v).strip() != "":
            return str(v).strip()
    return None


def ingest(features):
    out = []
    for f in features:
        geom = f.get("geometry") or {}
        coords = geom.get("coordinates")
        if geom.get("type") == "Point" and coords:
            lng, lat = coords[0], coords[1]
        elif geom.get("type") == "MultiPoint" and coords:
            lng, lat = coords[0][0], coords[0][1]
        else:
            continue
        props = f.get("properties") or {}
        sci = pick(props, BINOMIAL_FIELDS)
        if not sci:
            continue
        out.append([sci, pick(props, COMMON_FIELDS), pick(props, AGE_FIELDS),
                     pick(props, ADDRESS_FIELDS), lng, lat])
    return out


def main():
    trees, used_layer = [], None
    for layer in LAYERS:
        print(f"Fetching {layer} ...")
        try:
            trees = ingest(fetch_layer(layer))
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            print(f"  failed: {e}")
            continue
        if trees:
            used_layer = layer
            break
        print("  0 usable features, trying next layer")

    if not trees:
        sys.exit("No layer returned usable data — nothing to bundle.")

    out_dir = os.path.join(HERE, OUT_DIR)
    os.makedirs(out_dir, exist_ok=True)

    trees_path = os.path.join(out_dir, "trees.json")
    with open(trees_path, "w", encoding="utf-8") as f:
        json.dump({
            "builtAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "layer": used_layer,
            "trees": trees,
        }, f, separators=(",", ":"))

    shutil.copyfile(os.path.join(HERE, HTML_NAME), os.path.join(out_dir, HTML_NAME))

    size_mb = os.path.getsize(trees_path) / 1_000_000
    print(f"\nWrote {out_dir}/ — {len(trees):,} trees from {used_layer} ({size_mb:.1f} MB).")
    print("Upload the dist/ folder to any static host; no server or proxy needed there.")


if __name__ == "__main__":
    main()
