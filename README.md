# Bank Queue Simulation

A discrete-event simulation of a bank's customer queue, built entirely with the
**Python standard library** — no third-party runtime dependencies. The project
models how customers arrive, wait in a first-in-first-out (FIFO) queue, and are
served by a configurable number of counters, then reports waiting-time
statistics across different scenarios.

It is delivered as three layers:

1. A simulation **engine** with a custom circular-queue data structure.
2. A command-line **experiment runner** and analysis report.
3. A lightweight **HTTP/JSON API** and a responsive **web dashboard**.

---

## Overview

The simulation represents a bank that is open for a fixed number of minutes
(480 by default — one 8-hour day). During each minute:

- A new customer arrives with probability `p` (`random.random() < p`).
- Each customer is assigned a random service duration of 2–8 minutes.
- Customers wait in a FIFO queue and are served by the first available counter.
- Each customer's **waiting time** is `service_start_time − arrival_time`.

The model collects the total customers arrived and served, the average waiting
time, the maximum queue length, and the number of customers still waiting when
the bank closes. A fixed random seed (default 42) makes every run reproducible.

---

## Features

- **Custom circular queue** — a fixed-capacity ring buffer with O(1) `enqueue`
  and `dequeue`, implemented from scratch (no `collections.deque`,
  `queue.Queue`, or `heapq`).
- **Deterministic simulation engine** — pure logic, separated from presentation,
  with full input validation and reproducible results for a given seed.
- **Experiment runner** — evaluates the six reference configurations
  (`p ∈ {0.3, 0.6}` × `k ∈ {1, 2, 3}`) and prints a formatted results table.
- **Minimum-counter search** — finds the smallest number of counters that keeps
  the average waiting time below a threshold (default 5 minutes).
- **Data-driven analysis** — conclusions are computed from actual results, never
  hardcoded.
- **Standard-library HTTP API** — JSON endpoints built on `http.server`, with
  request validation, safe static file serving, and directory-traversal
  protection.
- **Responsive web dashboard** — an enterprise-style analytical interface with
  live metrics, a results table, and native SVG charts (no front-end
  frameworks).
- **Comprehensive tests** — 28 unit tests covering the queue and the simulation
  logic.

---

## Technologies

- **Python 3** (standard library only): `random`, `http.server`, `json`,
  `pathlib`, `urllib.parse`, `mimetypes`, `os`, `unittest`, `dataclasses`,
  `typing`.
- **Frontend**: semantic HTML5, CSS3, and vanilla JavaScript (`fetch`, inline
  SVG). No React/Vue/Angular and no build step.

---

## Project structure

```
.
├── circular_queue.py        # Custom fixed-size circular queue (ring buffer)
├── simulation.py            # Simulation engine: run_simulation()
├── main.py                  # Experiment runner, results table, analysis
├── server.py                # Standard-library HTTP/JSON API + static serving
├── test_circular_queue.py   # 14 unit tests for the queue
├── test_simulation.py       # 14 unit tests for the simulation engine
├── frontend/
│   ├── index.html           # Dashboard markup
│   ├── style.css            # Dashboard styling
│   └── app.js               # API integration and SVG charts
├── .gitignore
└── README.md
```

---

## Requirements

- **Python 3.9 or newer** (developed and tested on Python 3.14).
- No packages to install — the project uses only the standard library.

> On Windows, the examples below use the `py` launcher. On macOS/Linux, use
> `python3` instead.

---

## Installation

```bash
# Clone the repository
git clone <your-repository-url>
cd <repository-folder>
```

That is all — there are no dependencies to install.

---

## Running the tests

All 28 unit tests run through Python's built-in `unittest` framework:

```bash
py -m unittest -v
```

Expected summary:

```
Ran 28 tests
OK
```

---

## Running the command-line experiments

This runs the six reference configurations, prints the results table, performs
the minimum-counter search, and prints the analysis:

```bash
py main.py
```

---

## Starting the web server

The server hosts the JSON API and serves the dashboard from the `frontend/`
directory.

```bash
py server.py
```

Then open:

```
http://127.0.0.1:8000/
```

The port can be changed with the `PORT` environment variable, and the server
binds to `0.0.0.0` for deployment compatibility:

```bash
# Windows (PowerShell)
$env:PORT = "9000"; py server.py

# macOS / Linux
PORT=9000 python3 server.py
```

---

## API reference

| Method & path              | Request body (JSON)                       | Description                                                            |
| -------------------------- | ----------------------------------------- | --------------------------------------------------------------------- |
| `GET  /api/health`         | —                                         | Returns server status and application information.                    |
| `POST /api/simulate`       | `{ "k", "p", "simulation_time?", "seed?" }` | Runs one simulation and returns its full statistics.                  |
| `POST /api/experiments`    | `{}`                                      | Runs the six reference configurations and returns all results.        |
| `POST /api/minimum-counters` | `{ "p", "threshold?" }`                 | Returns the minimum counters needed to meet the waiting-time target.  |

Defaults: `simulation_time = 480`, `seed = 42`, `threshold = 5.0`.

### Example

```bash
curl -X POST http://127.0.0.1:8000/api/simulate \
  -H "Content-Type: application/json" \
  -d '{"k": 2, "p": 0.3}'
```

### Validation rules

- `k` — required integer, `k ≥ 1`.
- `p` — required number, `0 ≤ p ≤ 1`.
- `simulation_time` — optional integer, `> 0`.
- `seed` — optional integer.
- `threshold` — optional number, `> 0`.

Invalid parameters and malformed JSON return HTTP `400` with a descriptive error
message; unknown endpoints return `404`.

---

## How it works

- **Circular queue** — a single pre-allocated list is treated as a ring. A
  `head` index and a `count` track the front and size; the tail is derived as
  `(head + count) % capacity`. Because indices wrap with the modulo operator and
  no elements are ever shifted, both `enqueue` and `dequeue` run in O(1).
- **Simulation loop** — for each minute, the engine (1) generates a possible
  arrival, (2) records the peak queue length, then (3) assigns waiting customers
  to any free counters in FIFO order. Each counter stores the minute it becomes
  free, so counters operate independently.
- **Interpretation** — a higher arrival probability increases queue length and
  waiting time. Adding counters raises the service rate; once it exceeds the
  arrival rate, the queue stops growing and the average waiting time drops
  sharply.

---

## Reproducibility

Every simulation re-seeds Python's random generator before it runs, so the same
parameters and seed always produce identical results. This allows fair
comparison between different counter counts at the same arrival probability.

---

## License

This project was developed for academic purposes. Add a license of your choice
before publishing if required.
