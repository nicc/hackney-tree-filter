# Hackney Tree Map

A local, single-file version of the [Hackney Tree Map](https://map2.hackney.gov.uk/maps/trees/index.html)
with a species filter: type a **binomial name**, get autocomplete, add/remove species
as chips, and **Select all species** / **Clear all**. The map shows only the selected
species, colour-coded, with a live count.

Everything lives in [`index.html`](index.html) — no build step, no dependencies beyond
Leaflet + CARTO tiles loaded from a CDN.

## Running it

Two modes, depending on whether you want fresh data on every load or a static
site you can upload somewhere.

**Live**, fetching current data on each page load:

```
python3 run.py
```

This serves `index.html` and proxies Hackney's WFS from the **same origin**
(`/geoserver/ows`), so the browser's cross-origin checks never apply, and opens
your browser automatically. Stdlib only — no dependencies. Stop with `Ctrl+C`.

**Static bundle**, for uploading somewhere with no server-side code at all:

```
python3 build.py
```

Fetches the current tree data once and writes a self-contained `dist/` folder
(`index.html` + `trees.json`). Upload `dist/` as-is to any static host — GitHub
Pages, Netlify, S3, etc. The app loads `trees.json` directly, so no proxy is
needed there. Tree data doesn't change often, so re-run `build.py` occasionally
(the status banner in the app shows the snapshot's build date) rather than on
every deploy.

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
CORS headers.

`index.html` tries three sources, in order, and uses whichever works first:

1. **Bundled cache** — a `trees.json` sitting next to it, written by `build.py`.
   Status banner shows the snapshot date.
2. **Live WFS** — a direct fetch (works when served via `run.py`'s proxy, or if
   the browser happens to allow the cross-origin request). Banner turns green.
3. **Sample** — a small bundled set of real Hackney trees, so every control still
   works even with no network. Banner turns brown.

## Filter semantics

Everything is selected by default (full map). **Clear all** empties the selection
(blank map); **Select all species** restores it; typing a name and picking it from
autocomplete adds one species; a chip's `×` removes one.
