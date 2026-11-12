/* Bank Queue Simulation — frontend logic (vanilla JS).
 *
 * All computation happens on the backend; this file only sends requests to the
 * existing API and renders the actual responses. No simulation logic is
 * duplicated here. Response shapes used (from server.py / simulation.py):
 *   /api/health             -> { status, application, endpoints }
 *   /api/simulate           -> { total_arrived, total_served, average_waiting_time,
 *                                 maximum_queue_length, remaining_customers,
 *                                 individual_customer_waiting_times, simulation_parameters }
 *   /api/experiments        -> { count, results: [ <simulate result>, ... ] }
 *   /api/minimum-counters   -> { p, threshold, minimum_counters, found }
 */

"use strict";

/* ------------------------------------------------------------------ utilities */

const $ = (id) => document.getElementById(id);
const SVG_NS = "http://www.w3.org/2000/svg";

// Relative base so the app works locally and after deployment.
async function apiFetch(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  let data = null;
  try {
    data = await res.json();
  } catch (_) {
    // Non-JSON or empty body.
  }
  if (!res.ok) {
    const message = (data && data.error) || `Request failed (HTTP ${res.status})`;
    throw new Error(message);
  }
  return data;
}

function fmt(n, digits = 2) {
  if (typeof n !== "number" || !isFinite(n)) return "—";
  return n.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}
function fmtInt(n) {
  if (typeof n !== "number" || !isFinite(n)) return "—";
  return n.toLocaleString();
}

function svgEl(name, attrs = {}) {
  const el = document.createElementNS(SVG_NS, name);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  return el;
}

/* -------------------------------------------------------------- health check */

async function checkHealth() {
  const dot = $("connDot");
  const label = $("connLabel");
  try {
    const data = await apiFetch("/api/health");
    if (data && data.status === "ok") {
      dot.dataset.state = "ok";
      const name = data.application && data.application.name ? data.application.name : "API";
      label.textContent = `Connected · ${name}`;
      return true;
    }
    throw new Error("Unexpected health response");
  } catch (err) {
    dot.dataset.state = "down";
    label.textContent = "API offline";
    return false;
  }
}

/* --------------------------------------------------------- key metrics panel */

function renderMetrics(result) {
  $("mArrived").textContent = fmtInt(result.total_arrived);
  $("mServed").textContent = fmtInt(result.total_served);
  $("mWait").textContent = fmt(result.average_waiting_time, 2);
  $("mMaxQ").textContent = fmtInt(result.maximum_queue_length);

  const remain = $("mRemain");
  remain.textContent = fmtInt(result.remaining_customers);
  remain.classList.toggle("is-alert", result.remaining_customers > 0);

  const p = result.simulation_parameters;
  $("metricsSource").textContent =
    `From a single run · k=${p.k}, p=${p.p}, ${p.simulation_time} min, seed ${p.seed}.`;
}

/* --------------------------------------------------- simulation configuration */

function validateSimForm() {
  const errors = {};
  const k = Number($("inK").value);
  const p = Number($("inP").value);
  const t = Number($("inTime").value);
  const seed = $("inSeed").value;

  if (!Number.isInteger(k) || k < 1) errors.K = "Enter a whole number of counters (at least 1).";
  if ($("inP").value === "" || isNaN(p) || p < 0 || p > 1) errors.P = "Probability must be between 0 and 1.";
  if (!Number.isInteger(t) || t < 1) errors.Time = "Duration must be a whole number of minutes (at least 1).";
  if (seed === "" || !Number.isInteger(Number(seed))) errors.Seed = "Seed must be an integer.";

  // Paint field errors + aria-invalid.
  const map = { K: "inK", P: "inP", Time: "inTime", Seed: "inSeed" };
  for (const key of ["K", "P", "Time", "Seed"]) {
    $("err" + key).textContent = errors[key] || "";
    $(map[key]).setAttribute("aria-invalid", errors[key] ? "true" : "false");
  }
  return { ok: Object.keys(errors).length === 0, values: { k, p, simulation_time: t, seed: Number(seed) } };
}

async function onSimSubmit(evt) {
  evt.preventDefault();
  const status = $("simStatus");
  const btn = $("runBtn");
  const { ok, values } = validateSimForm();
  if (!ok) {
    status.textContent = "Please fix the highlighted fields.";
    status.className = "form-status is-error";
    return;
  }

  btn.disabled = true;
  status.textContent = "Running simulation…";
  status.className = "form-status";
  try {
    const result = await apiFetch("/api/simulate", {
      method: "POST",
      body: JSON.stringify(values),
    });
    renderMetrics(result);
    status.textContent = "Simulation complete.";
    status.className = "form-status is-ok";
  } catch (err) {
    status.textContent = err.message;
    status.className = "form-status is-error";
  } finally {
    btn.disabled = false;
  }
}

/* ----------------------------------------------------- minimum counter search */

async function onMinSubmit(evt) {
  evt.preventDefault();
  const status = $("minStatus");
  const btn = $("minBtn");
  const card = $("minResult");

  const p = Number($("inMinP").value);
  const threshold = Number($("inThreshold").value);
  const errEl = $("errThreshold");

  if (isNaN(threshold) || threshold <= 0) {
    errEl.textContent = "Threshold must be greater than 0.";
    $("inThreshold").setAttribute("aria-invalid", "true");
    return;
  }
  errEl.textContent = "";
  $("inThreshold").setAttribute("aria-invalid", "false");

  btn.disabled = true;
  status.textContent = "Searching…";
  status.className = "form-status";
  try {
    const data = await apiFetch("/api/minimum-counters", {
      method: "POST",
      body: JSON.stringify({ p, threshold }),
    });
    card.hidden = false;
    if (data.found) {
      $("minValue").textContent = data.minimum_counters;
      $("minText").textContent =
        `With arrival probability p = ${data.p}, at least ${data.minimum_counters} ` +
        `counter${data.minimum_counters === 1 ? "" : "s"} are needed to keep the average ` +
        `waiting time below ${data.threshold} minutes.`;
    } else {
      $("minValue").textContent = "—";
      $("minText").textContent =
        `No counter count within the search bound achieved an average wait below ${data.threshold} minutes.`;
    }
    status.textContent = "";
    status.className = "form-status";
  } catch (err) {
    status.textContent = err.message;
    status.className = "form-status is-error";
  } finally {
    btn.disabled = false;
  }
}

/* ---------------------------------------------------------- experiments table */

function renderExperimentTable(results) {
  const body = $("expBody");
  body.innerHTML = "";
  for (const r of results) {
    const prm = r.simulation_parameters;
    const tr = document.createElement("tr");

    const pClass = prm.p <= 0.3 ? "badge-low" : "badge-high";
    const remainCell = r.remaining_customers > 0
      ? `<td class="num cell-warn">${fmtInt(r.remaining_customers)}</td>`
      : `<td class="num">${fmtInt(r.remaining_customers)}</td>`;

    tr.innerHTML =
      `<td class="row-p"><span class="badge ${pClass}">${prm.p}</span></td>` +
      `<td>${prm.k}</td>` +
      `<td class="num">${fmtInt(r.total_arrived)}</td>` +
      `<td class="num">${fmtInt(r.total_served)}</td>` +
      `<td class="num">${fmt(r.average_waiting_time, 2)}</td>` +
      `<td class="num">${fmtInt(r.maximum_queue_length)}</td>` +
      remainCell;
    body.appendChild(tr);
  }
  $("expTable").hidden = false;
}

/* ----------------------------------------------------------------- SVG charts */

// Group experiment results into { k, low (p=0.3), high (p=0.6) } rows.
function groupByCounter(results, metricKey) {
  const byK = new Map();
  for (const r of results) {
    const prm = r.simulation_parameters;
    if (!byK.has(prm.k)) byK.set(prm.k, { k: prm.k, low: null, high: null });
    const slot = byK.get(prm.k);
    if (prm.p <= 0.3) slot.low = r[metricKey];
    else slot.high = r[metricKey];
  }
  return [...byK.values()].sort((a, b) => a.k - b.k);
}

// Grouped vertical bar chart rendered as responsive SVG.
function buildBarChart(host, groups, { yLabel, valueDigits }) {
  host.innerHTML = "";
  if (!groups.length) {
    host.innerHTML = '<p class="chart-empty">No data to display.</p>';
    return;
  }

  const W = 440, H = 260;
  const m = { top: 16, right: 14, bottom: 42, left: 48 };
  const plotW = W - m.left - m.right;
  const plotH = H - m.top - m.bottom;

  const values = [];
  for (const g of groups) { if (g.low != null) values.push(g.low); if (g.high != null) values.push(g.high); }
  const rawMax = Math.max(1, ...values);
  // Round the axis top to a tidy number.
  const niceMax = roundUpNice(rawMax);

  const svg = svgEl("svg", {
    viewBox: `0 0 ${W} ${H}`,
    role: "img",
    "aria-label": `${yLabel} by number of counters, for p=0.3 and p=0.6`,
  });

  const y = (v) => m.top + plotH - (v / niceMax) * plotH;

  // Gridlines + y ticks.
  const ticks = 4;
  const grid = svgEl("g", { class: "grid" });
  const axis = svgEl("g", { class: "axis" });
  for (let i = 0; i <= ticks; i++) {
    const val = (niceMax / ticks) * i;
    const yy = y(val);
    grid.appendChild(svgEl("line", { x1: m.left, y1: yy, x2: m.left + plotW, y2: yy }));
    const lbl = svgEl("text", { x: m.left - 8, y: yy + 4, class: "tick-label", "text-anchor": "end" });
    lbl.textContent = formatTick(val, valueDigits);
    axis.appendChild(lbl);
  }
  svg.appendChild(grid);

  // Axis lines.
  axis.appendChild(svgEl("line", { x1: m.left, y1: m.top, x2: m.left, y2: m.top + plotH }));
  axis.appendChild(svgEl("line", { x1: m.left, y1: m.top + plotH, x2: m.left + plotW, y2: m.top + plotH }));

  // Y axis title.
  const yTitle = svgEl("text", {
    x: 12, y: m.top + plotH / 2, class: "axis-title",
    "text-anchor": "middle", transform: `rotate(-90 12 ${m.top + plotH / 2})`,
  });
  yTitle.textContent = yLabel;
  axis.appendChild(yTitle);

  // Bars: one group per k, two bars (low/high).
  const groupW = plotW / groups.length;
  const barW = Math.min(34, groupW / 3);
  const gap = 6;
  const colors = { low: "#2f7d78", high: "#b8792b" };

  groups.forEach((g, i) => {
    const cx = m.left + groupW * i + groupW / 2;
    const pairW = barW * 2 + gap;
    const x0 = cx - pairW / 2;

    [["low", g.low, x0], ["high", g.high, x0 + barW + gap]].forEach(([series, val, bx]) => {
      if (val == null) return;
      const barH = Math.max(0, (val / niceMax) * plotH);
      svg.appendChild(svgEl("rect", {
        x: bx, y: m.top + plotH - barH, width: barW, height: barH,
        fill: colors[series], rx: 1,
      }));
      const vt = svgEl("text", {
        x: bx + barW / 2, y: m.top + plotH - barH - 5,
        class: "bar-value", "text-anchor": "middle",
      });
      vt.textContent = formatTick(val, valueDigits);
      svg.appendChild(vt);
    });

    // X label.
    const xl = svgEl("text", {
      x: cx, y: m.top + plotH + 18, class: "tick-label", "text-anchor": "middle",
    });
    xl.textContent = `k = ${g.k}`;
    svg.appendChild(xl);
  });

  // X axis title.
  const xTitle = svgEl("text", {
    x: m.left + plotW / 2, y: H - 6, class: "axis-title", "text-anchor": "middle",
  });
  xTitle.textContent = "Number of counters";
  svg.appendChild(xTitle);

  svg.appendChild(axis);
  host.appendChild(svg);
}

function roundUpNice(v) {
  if (v <= 0) return 1;
  const mag = Math.pow(10, Math.floor(Math.log10(v)));
  const n = v / mag;
  let step;
  if (n <= 1) step = 1; else if (n <= 2) step = 2; else if (n <= 5) step = 5; else step = 10;
  return step * mag;
}
function formatTick(v, digits) {
  if (digits && v % 1 !== 0) return v.toFixed(digits);
  return Math.round(v).toString();
}

function renderCharts(results) {
  const waitGroups = groupByCounter(results, "average_waiting_time");
  const queueGroups = groupByCounter(results, "maximum_queue_length");
  buildBarChart($("chartWait"), waitGroups, { yLabel: "Avg wait (min)", valueDigits: 1 });
  buildBarChart($("chartQueue"), queueGroups, { yLabel: "Max queue", valueDigits: 0 });
}

/* ------------------------------------------------------- experiments loading */

async function loadExperiments() {
  const status = $("expStatus");
  const table = $("expTable");
  const btn = $("reloadExp");
  btn.disabled = true;
  status.textContent = "Loading experiments…";
  status.className = "table-status";
  table.hidden = true;
  try {
    const data = await apiFetch("/api/experiments", { method: "POST", body: "{}" });
    const results = (data && data.results) || [];
    if (!results.length) {
      status.textContent = "No experiment results were returned.";
      status.className = "table-status is-error";
      return;
    }
    renderExperimentTable(results);
    renderCharts(results);
    status.textContent = `Loaded ${results.length} configurations.`;
    status.className = "table-status";
  } catch (err) {
    status.textContent = `Could not load experiments: ${err.message}`;
    status.className = "table-status is-error";
  } finally {
    btn.disabled = false;
  }
}

/* --------------------------------------------------------------- bootstrap */

function init() {
  $("simForm").addEventListener("submit", onSimSubmit);
  $("minForm").addEventListener("submit", onMinSubmit);
  $("reloadExp").addEventListener("click", loadExperiments);

  checkHealth().then((online) => {
    if (online) loadExperiments();
    else {
      $("expStatus").textContent = "API offline — experiment data unavailable.";
      $("expStatus").className = "table-status is-error";
    }
  });
}

document.addEventListener("DOMContentLoaded", init);
