# Hackney Tree Filter

A local, single-file version of the [Hackney Tree Map](https://map2.hackney.gov.uk/maps/trees/index.html)
with a species filter: type a **binomial name**, get autocomplete, add/remove species
as chips, and **Select all species** / **Clear all**. The map shows only the selected
species, colour-coded, with a live count.

Just open `hackney-tree-filter.html` in a browser — no build step, no dependencies
beyond Leaflet + CARTO tiles loaded from a CDN.

## Where the data comes from

Hackney publishes its trees from a public GeoServer WFS as GeoJSON:

```
https://map2.hackney.gov.uk/geoserver/ows
```

The official map reads this from the **same origin**, so it never needs CORS.
This local file is a *different* origin, so the browser applies cross-origin rules.
Two outcomes:

- **Live** — if Hackney's GeoServer returns permissive CORS headers, the app loads
  the real trees and the status banner turns green.
- **Sample** — if not (the usual case when you double-click the file and it opens as
  `file://`), the app falls back to a small bundled set of **real Hackney trees** so
  every control still works. Banner turns brown.

The app auto-detects the species/common-name/age fields and builds the autocomplete
list from whatever it loads, so it adapts to either dataset.

## Getting the full ~45,000 live trees locally

Route the WFS through a tiny same-origin proxy, then point the app at it.

**Python (stdlib only):** save as `proxy.py`, run `python3 proxy.py`:

```python
import http.server, urllib.request, urllib.parse
BASE = "https://map2.hackney.gov.uk/geoserver/ows"
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.urlparse(self.path).query
        with urllib.request.urlopen(f"{BASE}?{q}") as r:
            body = r.read()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers(); self.wfile.write(body)
http.server.HTTPServer(("127.0.0.1", 8788), H).serve_forever()
```

Then in `hackney-tree-filter.html`, change one line in `CONFIG`:

```js
geoserver: 'http://127.0.0.1:8788',
```

Serve the HTML from any static server (e.g. `python3 -m http.server 8080`) and open
`http://127.0.0.1:8080/hackney-tree-filter.html`.

## Finding the exact street-tree layer

The layer name for the 45k street-tree dataset isn't documented, so `CONFIG.layers`
tries a list of likely names and stops at the first that returns features. The
tree-preservation-order layer is confirmed-working and sits at the end of the list,
so "live" mode always returns *some* real Hackney data. If you find the real
street-tree `typeName` (Hackney's GeoServer web UI lists all layers), prepend it to
`CONFIG.layers` for the complete dataset.
