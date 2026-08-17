#!/usr/bin/env python3
"""
Run the Hackney Tree Map locally with live data.

    python3 run.py

Serves hackney-tree-filter.html and proxies Hackney's GeoServer WFS from the
*same origin*, so the browser never applies cross-origin rules — no CORS, no
editing the HTML. Put this file next to hackney-tree-filter.html and run it.
Stop with Ctrl+C.

Standard library only.
"""

import gzip
import http.server
import os
import re
import socketserver
import sys
import threading
import urllib.error
import urllib.request
import webbrowser

UPSTREAM = "https://map2.hackney.gov.uk/geoserver/ows"
PROXY_PATH = "/geoserver/ows"
HTML_NAME = "index.html"
PREFERRED_PORT = 8080

HERE = os.path.dirname(os.path.abspath(__file__))
HTML_PATH = os.path.join(HERE, HTML_NAME)

# Point the page's data source at this same-origin proxy, whatever it's set to.
GEOSERVER_RE = re.compile(r"geoserver:\s*'[^']*'")
GEOSERVER_SUB = "geoserver: location.origin + '" + PROXY_PATH + "'"


def load_page():
    """Read the HTML once and rewrite its GeoServer URL to the local proxy."""
    if not os.path.exists(HTML_PATH):
        sys.exit(f"Can't find {HTML_NAME} next to this script (looked in {HERE}).")
    with open(HTML_PATH, encoding="utf-8") as f:
        html = f.read()
    if not GEOSERVER_RE.search(html):
        print("Note: couldn't find the geoserver config line to rewrite — "
              "serving the page unchanged.", file=sys.stderr)
    html = GEOSERVER_RE.sub(GEOSERVER_SUB, html, count=1)
    return html.encode("utf-8")


PAGE = load_page()


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.split("?", 1)[0] == PROXY_PATH:
            self.proxy()
        elif self.path.split("?", 1)[0] in ("/", "/index.html", "/" + HTML_NAME):
            self.serve_page()
        else:
            self.send_error(404)

    def serve_page(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(PAGE)))
        self.end_headers()
        self.wfile.write(PAGE)

    def proxy(self):
        query = self.path.split("?", 1)[1] if "?" in self.path else ""
        url = UPSTREAM + ("?" + query if query else "")
        # Hackney's GeoServer honors Accept-Encoding but urllib won't send it (or
        # decode the response) on its own — asking cuts a ~46MB tree response to
        # ~4MB on the wire. Decompress here so the browser gets plain JSON either way.
        req = urllib.request.Request(url, headers={
            "User-Agent": "hackney-tree-filter/1.0",
            "Accept-Encoding": "gzip",
        })
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                status, ctype, encoding, body = r.status, r.headers.get_content_type(), r.headers.get("Content-Encoding"), r.read()
        except urllib.error.HTTPError as e:               # forward upstream 4xx/5xx
            status, ctype, encoding, body = e.code, e.headers.get_content_type(), e.headers.get("Content-Encoding"), e.read()
        except (urllib.error.URLError, TimeoutError) as e:
            status, ctype, encoding = 502, "text/plain", None
            body = f"Upstream fetch failed: {e}".encode("utf-8")
            print(f"  proxy error: {e}", file=sys.stderr)
        if encoding == "gzip":
            body = gzip.decompress(body)
        self.send_response(status)
        self.send_header("Content-Type", ctype or "application/octet-stream")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass  # keep the console quiet; errors still print from proxy()


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main():
    try:
        server = Server(("127.0.0.1", PREFERRED_PORT), Handler)
    except OSError:
        server = Server(("127.0.0.1", 0), Handler)   # preferred port busy → pick any free one
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}/"

    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"Hackney Tree Map running at {url}")
    print("Serving the page and proxying Hackney's WFS on the same origin.")
    print("Press Ctrl+C to stop.")
    try:
        webbrowser.open(url)
    except Exception:
        pass

    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        print("\nStopping.")
        server.shutdown()


if __name__ == "__main__":
    main()