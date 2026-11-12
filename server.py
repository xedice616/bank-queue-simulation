"""Standard-library HTTP backend for the Bank Queue Simulation.

This server adds a thin web/API layer on top of the EXISTING project. It does
not contain any simulation logic of its own -- every computation is delegated
to functions that already live in the project:

    run_simulation()        -> simulation.py
    run_experiments()       -> main.py
    find_minimum_counters() -> main.py

Responsibilities kept strictly separate:
    * simulation.py / main.py  = the model + experiments (unchanged)
    * server.py (this file)    = HTTP transport, routing, validation, static files

Only the Python standard library is used (http.server, json, pathlib,
urllib.parse, mimetypes, os). No Flask/Django/FastAPI.

Start with:
    py server.py
    PORT=9000 py server.py        # custom port
"""

import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

# Reuse the existing project code -- do NOT reimplement any of it here.
# Importing main.py is safe: its real work is guarded by `if __name__ ...`,
# so only the function/constant definitions load.
from simulation import run_simulation
from main import run_experiments, find_minimum_counters


# --- Configuration -----------------------------------------------------------

BASE_DIR: Path = Path(__file__).resolve().parent
FRONTEND_DIR: Path = (BASE_DIR / "frontend").resolve()

HOST: str = "0.0.0.0"                         # bind-all for deployment compatibility
PORT: int = int(os.environ.get("PORT", "8000"))

MAX_BODY_BYTES: int = 1_000_000               # 1 MB request-body cap
# Sanity ceilings so a single request cannot ask for an unbounded computation.
MAX_SIMULATION_TIME: int = 100_000
MAX_COUNTERS_REQUEST: int = 10_000

APP_INFO = {
    "name": "Bank Queue Simulation API",
    "version": "1.0.0",
    "description": "HTTP/JSON interface over the existing bank queue simulation.",
}

# Make sure common web types are known even on a bare OS install.
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("application/json", ".json")


class SimulationRequestHandler(BaseHTTPRequestHandler):
    """Routes API calls to the existing simulation code and serves static files."""

    server_version = "BankQueueSim/1.0"

    # ------------------------------------------------------------------ helpers

    def _send_json(self, status: int, payload: dict) -> None:
        """Serialize `payload` as JSON and send it with the given status code."""
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, status: int, message: str) -> None:
        """Send a uniform JSON error envelope."""
        self._send_json(status, {"error": message, "status": status})

    def _read_json_body(self):
        """Read and parse a JSON request body.

        Returns (data_dict, None) on success, or (None, error_response_already_sent)
        where the caller should simply `return`. An absent/empty body is treated
        as an empty object, so parameterless POSTs (e.g. /api/experiments) work.
        """
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            return {}, False

        try:
            length = int(raw_length)
        except ValueError:
            self._error(400, "Invalid Content-Length header")
            return None, True

        if length < 0:
            self._error(400, "Invalid Content-Length header")
            return None, True
        if length > MAX_BODY_BYTES:
            self._error(413, f"Request body too large (max {MAX_BODY_BYTES} bytes)")
            return None, True
        if length == 0:
            return {}, False

        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._error(400, "Malformed JSON in request body")
            return None, True

        if not isinstance(data, dict):
            self._error(400, "Request body must be a JSON object")
            return None, True

        return data, False

    # ------------------------------------------------------------- validation

    @staticmethod
    def _require_number(data: dict, field: str, *, as_int: bool):
        """Fetch and type-check a numeric field. Raises ValueError with a clear
        message if missing or the wrong type. Rejects bool (which is an int)."""
        if field not in data:
            raise ValueError(f"Missing required field: '{field}'")
        value = data[field]
        if isinstance(value, bool):
            raise ValueError(f"Field '{field}' must be a number, not a boolean")
        if as_int:
            if not isinstance(value, int):
                raise ValueError(f"Field '{field}' must be an integer")
        else:
            if not isinstance(value, (int, float)):
                raise ValueError(f"Field '{field}' must be a number")
        return value

    # -------------------------------------------------------------- API routes

    def _route_health(self) -> None:
        self._send_json(200, {
            "status": "ok",
            "application": APP_INFO,
            "endpoints": [
                "GET  /api/health",
                "POST /api/simulate",
                "POST /api/experiments",
                "POST /api/minimum-counters",
            ],
        })

    def _route_simulate(self) -> None:
        data, handled = self._read_json_body()
        if handled:
            return
        try:
            k = self._require_number(data, "k", as_int=True)
            p = self._require_number(data, "p", as_int=False)
            # Optional with the same defaults as run_simulation().
            simulation_time = data.get("simulation_time", 480)
            seed = data.get("seed", 42)
            if isinstance(simulation_time, bool) or not isinstance(simulation_time, int):
                raise ValueError("Field 'simulation_time' must be an integer")
            if isinstance(seed, bool) or not isinstance(seed, int):
                raise ValueError("Field 'seed' must be an integer")
            if simulation_time > MAX_SIMULATION_TIME:
                raise ValueError(f"simulation_time must be <= {MAX_SIMULATION_TIME}")
            if k > MAX_COUNTERS_REQUEST:
                raise ValueError(f"k must be <= {MAX_COUNTERS_REQUEST}")
        except ValueError as exc:
            self._error(400, str(exc))
            return

        try:
            # All domain validation (k>0, 0<=p<=1, ...) is enforced inside
            # run_simulation itself -- we do not duplicate it here.
            result = run_simulation(
                k=k, p=p, simulation_time=simulation_time, seed=seed
            )
        except ValueError as exc:
            self._error(400, str(exc))
            return

        self._send_json(200, result)

    def _route_experiments(self) -> None:
        # No parameters needed; this reproduces the six required configurations.
        results = run_experiments()
        self._send_json(200, {"count": len(results), "results": results})

    def _route_minimum_counters(self) -> None:
        data, handled = self._read_json_body()
        if handled:
            return
        try:
            p = self._require_number(data, "p", as_int=False)
            # Threshold is optional; defaults to the project's 5-minute target.
            threshold = data.get("threshold", 5.0)
            if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
                raise ValueError("Field 'threshold' must be a number")
            if not (0.0 <= p <= 1.0):
                raise ValueError("p must be a number between 0 and 1 inclusive")
            if threshold <= 0:
                raise ValueError("threshold must be greater than 0")
        except ValueError as exc:
            self._error(400, str(exc))
            return

        k_min = find_minimum_counters(p, threshold=threshold)
        self._send_json(200, {
            "p": p,
            "threshold": threshold,
            "minimum_counters": k_min,
            "found": k_min != -1,
        })

    # ----------------------------------------------------------- static files

    def _serve_static(self, url_path: str) -> None:
        """Serve a file from FRONTEND_DIR, with directory-traversal protection."""
        rel = unquote(urlparse(url_path).path)
        if rel in ("", "/"):
            rel = "/index.html"

        # Resolve the candidate and confirm it stays inside FRONTEND_DIR.
        candidate = (FRONTEND_DIR / rel.lstrip("/")).resolve()
        if candidate != FRONTEND_DIR and not candidate.is_relative_to(FRONTEND_DIR):
            self._error(403, "Forbidden")
            return

        if not candidate.is_file():
            self._error(404, "Not found")
            return

        content_type, _ = mimetypes.guess_type(str(candidate))
        content_type = content_type or "application/octet-stream"
        try:
            body = candidate.read_bytes()
        except OSError:
            self._error(500, "Could not read file")
            return

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # --------------------------------------------------------- HTTP verb entry

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            self._route_health()
        elif path.startswith("/api/"):
            self._error(404, f"Unknown API endpoint: {path}")
        else:
            self._serve_static(self.path)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/simulate":
            self._route_simulate()
        elif path == "/api/experiments":
            self._route_experiments()
        elif path == "/api/minimum-counters":
            self._route_minimum_counters()
        else:
            self._error(404, f"Unknown API endpoint: {path}")

    def log_message(self, fmt: str, *args) -> None:
        # Compact one-line access log to stderr.
        print(f"[server] {self.address_string()} - {fmt % args}")


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), SimulationRequestHandler)
    print(f"Bank Queue Simulation API listening on http://{HOST}:{PORT}")
    print(f"Serving static files from: {FRONTEND_DIR}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
