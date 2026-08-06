from __future__ import annotations

import http.server
from pathlib import Path
import socketserver
import webbrowser

PORT = 8000
root_dir = Path(__file__).resolve().parents[1]


def main():
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(root_dir), **kwargs)

    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        url = f"http://localhost:{PORT}/dashboard.html"
        print("=" * 70)
        print(f"🚀 DATA OBSERVABILITY & RAG PIPELINE DASHBOARD SERVING AT:")
        print(f"👉 {url}")
        print("=" * 70)
        print("Press Ctrl+C to stop the server.\n")

        webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nDashboard server stopped.")


if __name__ == "__main__":
    main()
