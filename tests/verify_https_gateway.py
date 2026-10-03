"""Exercise the real Nginx templates locally; requires nginx, openssl and curl.

Only paths, listening ports and the upstream address are adapted for this test.
The test certificate is trusted explicitly via --cacert, never via --insecure.
"""
import argparse
import http.server
import json
import os
from pathlib import Path
import socket
import subprocess
import threading
import time


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--nginx", required=True)
    parser.add_argument("--openssl", required=True)
    parser.add_argument("--curl", default="curl.exe" if os.name == "nt" else "curl")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1]
    root = Path(args.output).resolve()
    root.mkdir(parents=True, exist_ok=True)
    for part in ("logs", "conf", "temp", "static", "uploads", "www/.well-known/acme-challenge"):
        (root / part).mkdir(parents=True, exist_ok=True)
    cert, key = root / "test-cert.pem", root / "test-key.pem"
    subprocess.run([
        args.openssl, "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
        "-subj", "/CN=www.sunfan88.com", "-addext",
        "subjectAltName=DNS:www.sunfan88.com,DNS:sunfan88.com",
        "-keyout", str(key), "-out", str(cert),
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    (root / "static/sample.json").write_text('{"value":1}', encoding="utf-8")
    (root / "uploads/sample.txt").write_text("uploaded", encoding="utf-8")
    (root / "www/.well-known/acme-challenge/token").write_text("challenge", encoding="utf-8")

    class Upstream(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            payload = json.dumps({"path": self.path, "proto": self.headers.get("X-Forwarded-Proto")}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *unused):
            pass

    upstream = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
    threading.Thread(target=upstream.serve_forever, daemon=True).start()
    http_port, tls_port = free_port(), free_port()
    while tls_port == http_port:
        tls_port = free_port()

    def adapt(text):
        substitutions = {
            "listen 80": f"listen 127.0.0.1:{http_port}",
            "listen 443": f"listen 127.0.0.1:{tls_port}",
            "/etc/nginx/pear/app.locations.conf": (root / "conf/app.locations.conf").as_posix(),
            "/etc/nginx/https-state/http-mode.conf": (root / "conf/http-mode.conf").as_posix(),
            "/etc/letsencrypt/live/sunfan88.com/fullchain.pem": cert.as_posix(),
            "/etc/letsencrypt/live/sunfan88.com/privkey.pem": key.as_posix(),
            "/var/www/certbot": (root / "www").as_posix(),
            "/app/static/": (root / "static").as_posix() + "/",
            "/app/uploads/": (root / "uploads").as_posix() + "/",
            "http://web:5050": f"http://127.0.0.1:{upstream.server_port}",
        }
        for old, new in substitutions.items():
            text = text.replace(old, new)
        return text

    (root / "conf/app.locations.conf").write_text(adapt((source / "nginx/app.locations.conf").read_text()), encoding="utf-8")
    mode = root / "conf/http-mode.conf"
    mode.write_text(adapt("include /etc/nginx/pear/app.locations.conf;\n"), encoding="utf-8")
    config = root / "conf/nginx.conf"

    def configure(template):
        body = adapt((source / "nginx" / template).read_text())
        config.write_text("worker_processes 1;\npid logs/nginx.pid;\nerror_log logs/error.log;\nevents {}\nhttp {\n" + body + "\n}\n", encoding="utf-8")
        subprocess.run([args.nginx, "-p", root.as_posix() + "/", "-c", "conf/nginx.conf", "-t"], check=True, capture_output=True)

    def request(path, secure=False, domain="www.sunfan88.com"):
        port = tls_port if secure else http_port
        command = [args.curl, "--noproxy", "*", "-sS",
                   "--connect-timeout", "2", "--max-time", "5", "--resolve", f"{domain}:{port}:127.0.0.1",
                   "-i", f"{'https' if secure else 'http'}://{domain}:{port}{path}"]
        if secure:
            command.extend(["--cacert", str(cert)])
        return subprocess.run(command, check=True, capture_output=True, text=True, errors="replace").stdout

    process = None
    checks = []
    try:
        configure("nginx.http.conf")
        process = subprocess.Popen([args.nginx, "-p", root.as_posix() + "/", "-c", "conf/nginx.conf"],
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        for attempt in range(30):
            try:
                response = request("/pc/")
                break
            except subprocess.CalledProcessError:
                time.sleep(0.1)
        else:
            raise AssertionError("Nginx did not start")
        assert '"proto": "http"' in response and "200 OK" in response, response
        checks.append("HTTP bootstrap keeps business requests available")
        assert request("/.well-known/acme-challenge/token").endswith("challenge")
        checks.append("HTTP ACME challenge returns its exact content")

        configure("nginx.https.conf")
        subprocess.run([args.nginx, "-p", root.as_posix() + "/", "-c", "conf/nginx.conf", "-s", "reload"], check=True, capture_output=True)
        last_tls_error = ""
        for attempt in range(30):
            try:
                response = request("/pc/", secure=True)
                break
            except subprocess.CalledProcessError as error:
                last_tls_error = error.stderr
                time.sleep(0.1)
        else:
            raise AssertionError(f"TLS did not become available: {last_tls_error}")
        assert "200 OK" in response and '"proto": "https"' in response, response
        assert "200 OK" in request("/pc/", secure=True, domain="sunfan88.com")
        checks.append("TLS validates both hostnames; upstream receives HTTPS scheme")
        assert "200 OK" in request("/pc/")
        checks.append("HTTP stays available while public TLS is being checked")
        assert request("/uploads/sample.txt", secure=True).endswith("uploaded")
        assert "no-cache, no-store, must-revalidate" in request("/static/sample.json", secure=True)
        checks.append("Uploaded files and static JSON cache policy are preserved")

        mode.write_text("location / { return 301 https://www.sunfan88.com$request_uri; }\n", encoding="utf-8")
        subprocess.run([args.nginx, "-p", root.as_posix() + "/", "-c", "conf/nginx.conf", "-t"], check=True, capture_output=True)
        subprocess.run([args.nginx, "-p", root.as_posix() + "/", "-c", "conf/nginx.conf", "-s", "reload"], check=True, capture_output=True)
        for attempt in range(30):
            response = request("/pc/?next=%2F&check=1")
            if "301 Moved Permanently" in response:
                break
            time.sleep(0.1)
        assert "Location: https://www.sunfan88.com/pc/?next=%2F&check=1" in response, response
        checks.append("HTTP 301 preserves the requested path and query")
        assert request("/.well-known/acme-challenge/token").endswith("challenge")
        assert "404 Not Found" in request("/.well-known/acme-challenge/missing")
        checks.append("Renewal challenge stays reachable after HTTP redirect")
        print(json.dumps({"passed": len(checks), "checks": checks, "scope": "Local Nginx; production is not changed"}, ensure_ascii=False, indent=2))
    finally:
        if process is not None:
            subprocess.run([args.nginx, "-p", root.as_posix() + "/", "-c", "conf/nginx.conf", "-s", "quit"], capture_output=True)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.terminate()
        upstream.shutdown()


if __name__ == "__main__":
    main()
