#!/usr/bin/env python3

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from io import BytesIO

HOST = "0.0.0.0"
PORT = 8080


def _flatten_qs(qs_dict):
    """Flatten query string dict, returning first value when multiple exist."""
    result = {}
    for k, v in qs_dict.items():
        if isinstance(v, list):
            result[k] = v[0] if len(v) > 0 else ""
        else:
            result[k] = v
    return result


def _parse_form_urlencoded(body_bytes):
    """Parse application/x-www-form-urlencoded body."""
    try:
        body_str = body_bytes.decode("utf-8")
        return _flatten_qs(parse_qs(body_str, keep_blank_values=True))
    except (UnicodeDecodeError, ValueError):
        return {}


def _parse_multipart(body_bytes, boundary):
    """Parse multipart/form-data body using only stdlib."""
    if not boundary:
        return {}

    try:
        boundary = boundary.encode("utf-8") if isinstance(boundary, str) else boundary
        parts = body_bytes.split(b"--" + boundary)
        form_data = {}

        for part in parts[1:-1]:  # Skip preamble and epilogue
            if not part.strip():
                continue

            # Split headers and content
            try:
                header_end = part.find(b"\r\n\r\n")
                if header_end == -1:
                    header_end = part.find(b"\n\n")
                    if header_end == -1:
                        continue
                    content = part[header_end + 2:].rstrip(b"\r\n")
                else:
                    content = part[header_end + 4:].rstrip(b"\r\n")

                headers = part[:header_end].decode("utf-8", errors="ignore")

                # Extract field name from Content-Disposition
                name = None
                for line in headers.split("\n"):
                    if "Content-Disposition" in line:
                        for segment in line.split(";"):
                            segment = segment.strip()
                            if segment.startswith("name="):
                                name = segment[5:].strip('"')
                                break

                if name:
                    try:
                        form_data[name] = content.decode("utf-8")
                    except UnicodeDecodeError:
                        form_data[name] = content.hex()  # Binary data as hex

            except (ValueError, UnicodeDecodeError):
                continue

        return form_data
    except Exception:
        return {}


class CatchAllHandler(BaseHTTPRequestHandler):
    server_version = "StdlibServer/1.0"

    def log_message(self, format, *args):
        """Suppress default request logging."""
        pass

    def _log_request_details(self, body_bytes):
        """Parse and log all request details, return as JSON."""
        try:
            # Headers
            headers_dict = dict(self.headers.items())

            # URL pieces
            parsed = urlparse(self.path)
            flat_query = _flatten_qs(parse_qs(parsed.query, keep_blank_values=True))

            # Form parsing
            post_form = {}
            content_type = self.headers.get("Content-Type", "")

            if self.command in {"POST", "PUT", "DELETE", "PATCH"}:
                if content_type.startswith("application/x-www-form-urlencoded"):
                    post_form = _parse_form_urlencoded(body_bytes)
                elif content_type.startswith("multipart/form-data"):
                    # Extract boundary
                    boundary = None
                    for part in content_type.split(";"):
                        part = part.strip()
                        if part.startswith("boundary="):
                            boundary = part[9:].strip('"')
                            break
                    post_form = _parse_multipart(body_bytes, boundary)

            # JSON body
            json_body = None
            if content_type.startswith("application/json"):
                try:
                    json_body = json.loads(body_bytes.decode("utf-8") or "null")
                except (json.JSONDecodeError, UnicodeDecodeError):
                    json_body = None

            # Build response structure
            response_data = {
                "method": self.command,
                "path": parsed.path,
                "query": flat_query,
                "headers": headers_dict,
                "form": post_form,
            }

            if content_type.startswith("application/json"):
                response_data["json"] = json_body

            # Pretty print to stdout
            print(json.dumps(response_data, indent=2))
            sys.stdout.flush()

            return response_data

        except Exception as e:
            error_data = {
                "error": "Failed to parse request",
                "message": str(e),
                "method": self.command,
                "path": self.path,
            }
            print(json.dumps(error_data, indent=2))
            sys.stdout.flush()
            return error_data

    def _read_body(self):
        """Read request body safely."""
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length > 0:
                return self.rfile.read(length)
        except (ValueError, OSError):
            pass
        return b""

    def _write_json_response(self, data):
        """Send JSON response to client."""
        try:
            body = json.dumps(data).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _handle(self):
        """Handle all request types."""
        body = self._read_body()
        response_data = self._log_request_details(body)

        # Only write response body for non-HEAD requests
        if self.command != "HEAD":
            self._write_json_response(response_data)
        else:
            # HEAD requests only send headers
            try:
                body = json.dumps(response_data).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
            except (BrokenPipeError, ConnectionResetError):
                pass

    def do_GET(self):
        self._handle()

    def do_POST(self):
        self._handle()

    def do_PUT(self):
        self._handle()

    def do_DELETE(self):
        self._handle()

    def do_PATCH(self):
        self._handle()

    def do_HEAD(self):
        self._handle()

    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS and capabilities."""
        try:
            allow = "GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS"
            self.send_response(204)
            self.send_header("Allow", allow)
            self.end_headers()
        except (BrokenPipeError, ConnectionResetError):
            pass


def main():
    print(f"Serving on http://{HOST}:{PORT}")
    httpd = HTTPServer((HOST, PORT), CatchAllHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
