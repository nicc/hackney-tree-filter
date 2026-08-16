# Hackney Tree Filter

A local, single-file version of the [Hackney Tree Map](https://map2.hackney.gov.uk/maps/trees/index.html)
with a species filter: type a **binomial name**, get autocomplete, add/remove species
as chips, and **Select all species** / **Clear all**. The map shows only the selected
species, colour-coded, with a live count.

Everything lives in [`index.html`](index.html) — no build step, no dependencies beyond
Leaflet + CARTO tiles loaded from a CDN.

## Running it

```
python3 run.py
```

This serves `index.html` and proxies Hackney's WFS from the **same origin**
(`/geoserver/ows`), so the browser's cross-origin checks never apply, and opens
your browser automatically. Stdlib only — no dependencies. Stop with `Ctrl+C`.

You can also just open `index.html` directly from disk, but the live fetch will
almost always be blocked by CORS (see below) and you'll get the small bundled
sample instead of live data.

## Where the data comes from

Hackney publishes its trees from a public GeoServer WFS as GeoJSON:

```
https://map2.hackney.gov.uk/geoserver/ows
```

The real dataset is the **`greenspaces:tree`** layer — confirmed via the WFS's
`GetCapabilities` listing, currently around **38,800 features**. Each feature carries
a `species` (binomial), `common_name`, `age`, and location fields (`sitename`,
`treelocn`, `addnlocn`). `CONFIG.layers` in `index.html` tries this layer first, then
falls back to `planning:tree_preservation_order_point` (~630 TPO trees) if it's ever
renamed. The app auto-detects which field names are present on whatever layer
responds, so it isn't hardcoded to one schema.

The official Hackney map reads this same endpoint from the same origin, so it never
needs CORS. Opening `index.html` straight from disk (`file://`) is a *different*
origin, so the browser blocks the request unless Hackney's GeoServer sends permissive
CORS headers:

- **Live** — the app loads the real trees and the status banner turns green.
- **Sample** — if the request is blocked, it falls back to a small bundled set of
  real Hackney trees so every control still works. Banner turns brown.

Running via `run.py` sidesteps this entirely by serving the page and proxying the WFS
from the same origin.

## Filter semantics

Everything is selected by default (full map). **Clear all** empties the selection
(blank map); **Select all species** restores it; typing a name and picking it from
autocomplete adds one species; a chip's `×` removes one.
