// Sector-interaction view for multi-market runs — a heatmap of the cross-market
// cost/MAC shifts plus a directed feedback graph, driven ENTIRELY by the link
// columns the backend already stamps on multi-market summary rows.
//
// Config-driven presence (the owner's hard rule): the whole component is inert
// unless the (scenario-scoped) summary rows carry at least one `"Link "`-prefixed
// column. A single-market run has no such column, so this returns null and adds
// NOTHING to the DOM — byte-for-byte unchanged. Both hosts (the pe-shell app and
// the composer) mount it right after JointConvergenceCard, so the multi-market
// surfaces stay in one place rather than being duplicated per host.
//
// Where the numbers come from (dispatch._stamp_multi_market_columns, E6):
//   * "Link {from}->{to} Price In"            — the source market's delivered P_from(t)
//   * "Link {from}->{to} {channel} Input Shift" — phi*P_from(t), the shift on `to` (== row.Market)
// Cyclic-SCC rows additionally carry the four "Joint *" columns; we reuse the
// MultiMarket joint helpers to read whether the loop converged.

import { useMemo, useState } from "react";
import { fmt } from "./MarketChart.jsx";
import { jointRowsFromSummary, JOINT_CONVERGED_COLUMN } from "./MultiMarket.jsx";

const LINK_PREFIX = "Link ";
const PRICE_IN_SUFFIX = " Price In";
const INPUT_SHIFT_SUFFIX = " Input Shift";
const ALL_YEARS = "__all__";

// Scope the whole-run summary to one scenario's rows. The backend keys every
// multi-market row by the composite "{scenario} :: {market}", so a base scenario
// name matches its own composite rows. No name given means take every row (the run
// only holds one scenario).
function scenarioRows(summary, scenarioName) {
  const rows = Array.isArray(summary) ? summary : [];
  if (!scenarioName) return rows;
  const prefix = `${scenarioName} :: `;
  return rows.filter((row) => {
    const s = String(row?.Scenario ?? "");
    return s === scenarioName || s.startsWith(prefix);
  });
}

// Parse the link columns off the scenario-scoped rows into a market list, a year
// list, and per-(year, from, to) shift/price/channel records. Nothing here is
// domain-specific — every market id, year, and channel is read off the columns.
function parseInteractions(rows) {
  const markets = [];
  const marketSeen = new Set();
  const years = [];
  const yearSeen = new Set();
  const raw = new Map(); // year -> Map("{from}>>{to}" -> { from, to, priceIn, channels })
  let hasLinkColumns = false;

  const addMarket = (id) => {
    const s = String(id ?? "");
    if (s && !marketSeen.has(s)) {
      marketSeen.add(s);
      markets.push(s);
    }
  };
  const cellFor = (year, from, to) => {
    if (!raw.has(year)) raw.set(year, new Map());
    const yearMap = raw.get(year);
    const key = `${from}>>${to}`;
    if (!yearMap.has(key)) yearMap.set(key, { from, to, priceIn: null, channels: {} });
    return yearMap.get(key);
  };

  for (const row of rows) {
    if (!row) continue;
    if (row.Market != null) addMarket(row.Market);
    const year = row.Year != null ? String(row.Year) : "";
    if (year && !yearSeen.has(year)) {
      yearSeen.add(year);
      years.push(year);
    }
    for (const key of Object.keys(row)) {
      if (!key.startsWith(LINK_PREFIX)) continue;
      // Column PRESENCE is the config-driven gate (a multi-market run with a
      // link). The receiving market's row carries the finite value; every other
      // row of the same scenario carries the union column as JSON null (pandas
      // back-fill scrubbed by the web layer's _json_safe). Skip those nulls so a
      // non-receiver row never fabricates a zero-magnitude cell.
      hasLinkColumns = true;
      const rawValue = row[key];
      if (rawValue == null) continue;
      const value = Number(rawValue);
      if (!Number.isFinite(value)) continue;
      if (key.endsWith(PRICE_IN_SUFFIX)) {
        const mid = key.slice(LINK_PREFIX.length, key.length - PRICE_IN_SUFFIX.length); // "{from}->{to}"
        const arrow = mid.indexOf("->");
        if (arrow < 0) continue;
        const from = mid.slice(0, arrow);
        const to = mid.slice(arrow + 2);
        addMarket(from);
        addMarket(to);
        cellFor(year, from, to).priceIn = value;
      } else if (key.endsWith(INPUT_SHIFT_SUFFIX)) {
        const mid = key.slice(LINK_PREFIX.length, key.length - INPUT_SHIFT_SUFFIX.length); // "{from}->{to} {channel}"
        const arrow = mid.indexOf("->");
        if (arrow < 0) continue;
        const from = mid.slice(0, arrow);
        const rest = mid.slice(arrow + 2); // "{to} {channel}" (market ids carry no space)
        const gap = rest.indexOf(" ");
        if (gap < 0) continue;
        const to = rest.slice(0, gap);
        const channel = rest.slice(gap + 1);
        addMarket(from);
        addMarket(to);
        const cell = cellFor(year, from, to);
        cell.channels[channel] = (cell.channels[channel] || 0) + value;
      }
    }
  }
  return { hasLinkColumns, markets, years, raw };
}

// Collapse the per-year records to the selected year (or the summed aggregate)
// into a flat cell list. Each cell's `shift` sums its channels; `magnitude` sums
// their absolute values (the single colour ramp's driver).
function cellsForSelection(raw, years, selection) {
  const acc = new Map();
  const selectedYears = selection === ALL_YEARS ? years : [selection];
  for (const year of selectedYears) {
    const yearMap = raw.get(year);
    if (!yearMap) continue;
    for (const [key, cell] of yearMap) {
      let agg = acc.get(key);
      if (!agg) {
        agg = { from: cell.from, to: cell.to, priceIn: cell.priceIn, channels: {} };
        acc.set(key, agg);
      }
      if (agg.priceIn == null && cell.priceIn != null) agg.priceIn = cell.priceIn;
      for (const [channel, value] of Object.entries(cell.channels)) {
        agg.channels[channel] = (agg.channels[channel] || 0) + value;
      }
    }
  }
  const cells = [];
  for (const agg of acc.values()) {
    const values = Object.values(agg.channels);
    const shift = values.reduce((a, b) => a + b, 0);
    const magnitude = values.reduce((a, b) => a + Math.abs(b), 0);
    cells.push({ ...agg, shift, magnitude });
  }
  return cells;
}

function dominantChannel(cell) {
  let best = null;
  let bestAbs = -1;
  for (const [channel, value] of Object.entries(cell.channels || {})) {
    if (Math.abs(value) > bestAbs) {
      bestAbs = Math.abs(value);
      best = channel;
    }
  }
  return best;
}

// The one-line plain reading. Anchors on the strongest link; if a reciprocal
// link closes a loop, reports the feedback and (from the Joint columns) whether
// that loop converged.
function buildReading(cells, cellMap, joint) {
  if (!cells.length) return null;
  const dom = cells.reduce((a, b) => (Math.abs(b.shift) > Math.abs(a.shift) ? b : a));
  const domChannel = dominantChannel(dom);
  let text = `${dom.from} raises ${dom.to}'s marginal cost by ${fmt.num(Math.abs(dom.shift), 1)} (via ${domChannel})`;
  const reverse = cellMap.get(`${dom.to}>>${dom.from}`);
  if (reverse) {
    text += `; ${reverse.from} feeds ${fmt.num(Math.abs(reverse.shift), 1)} back into ${reverse.to}`;
    if (joint.cyclic) {
      text += joint.converged
        ? ` — a converged loop (${joint.iterations} outer iterations)`
        : " — a loop that did not converge";
    } else {
      text += " — a feedback loop";
    }
  }
  return `${text}.`;
}

// ---------- Heatmap ----------
function InteractionMatrix({ markets, cells, cellMap }) {
  const CELL = 46;
  const M_TOP = 48;
  const M_LEFT = 68;
  const n = markets.length;
  const W = M_LEFT + n * CELL + 10;
  const H = M_TOP + n * CELL + 10;
  const maxMag = Math.max(1e-9, ...cells.map((c) => c.magnitude));

  return (
    <div className="chart-wrap">
      <svg viewBox={`0 0 ${W} ${H}`} className="chart">
        <text x={M_LEFT + (n * CELL) / 2} y={14} className="axis-title" textAnchor="middle">
          to (receiving market)
        </text>
        <text
          transform={`translate(16, ${M_TOP + (n * CELL) / 2}) rotate(-90)`}
          className="axis-title"
          textAnchor="middle"
        >
          from (source market)
        </text>
        {markets.map((to, j) => (
          <text
            key={`col-${to}`}
            x={M_LEFT + j * CELL + CELL / 2}
            y={M_TOP - 8}
            className="axis-label"
            textAnchor="middle"
          >
            {to}
          </text>
        ))}
        {markets.map((from, i) => (
          <text
            key={`row-${from}`}
            x={M_LEFT - 8}
            y={M_TOP + i * CELL + CELL / 2}
            className="axis-label"
            textAnchor="end"
            dy="0.32em"
          >
            {from}
          </text>
        ))}
        {markets.map((from, i) =>
          markets.map((to, j) => {
            const x = M_LEFT + j * CELL;
            const y = M_TOP + i * CELL;
            const isDiagonal = from === to;
            const cell = cellMap.get(`${from}>>${to}`);
            const op = cell ? 0.1 + 0.8 * (cell.magnitude / maxMag) : 0;
            const style = isDiagonal
              ? { fill: "var(--panel-2)", stroke: "var(--line)" }
              : cell
                ? { fill: "var(--accent)", fillOpacity: op, stroke: "var(--line-2)" }
                : { fill: "none", stroke: "var(--line)" };
            return (
              <g key={`cell-${from}-${to}`}>
                <rect x={x + 1} y={y + 1} width={CELL - 2} height={CELL - 2} style={style} />
                {cell && (
                  <text
                    x={x + CELL / 2}
                    y={y + CELL / 2}
                    className="axis-label"
                    textAnchor="middle"
                    dy="0.32em"
                    style={{ paintOrder: "stroke", stroke: "var(--panel)", strokeWidth: 3 }}
                  >
                    {fmt.num(cell.shift, 1)}
                  </text>
                )}
              </g>
            );
          })
        )}
      </svg>
      <div className="chart-legend">
        <span>
          <i className="sw" style={{ background: "var(--accent)", opacity: 0.18 }}></i>lower shift
        </span>
        <span>
          <i className="sw" style={{ background: "var(--accent)", opacity: 0.9 }}></i>higher shift ({fmt.num(maxMag, 1)})
        </span>
        <span className="muted">Cell: cost shift `from` imposes on `to`. Blank = no link.</span>
      </div>
    </div>
  );
}

// ---------- Feedback graph ----------
function FeedbackGraph({ markets, cells }) {
  const W = 360;
  const H = 300;
  const cx = W / 2;
  const cy = H / 2;
  const n = markets.length;
  const R = Math.max(48, Math.min(cx, cy) - 56);
  const NODE_R = 24;

  const pos = useMemo(() => {
    const out = {};
    markets.forEach((market, i) => {
      const theta = -Math.PI / 2 + (2 * Math.PI * i) / Math.max(1, n);
      out[market] = n === 1 ? { x: cx, y: cy } : { x: cx + R * Math.cos(theta), y: cy + R * Math.sin(theta) };
    });
    return out;
  }, [markets, n, cx, cy, R]);

  const index = useMemo(() => new Map(markets.map((m, i) => [m, i])), [markets]);
  const maxMag = Math.max(1e-9, ...cells.map((c) => c.magnitude));

  const trim = (point, toward, r) => {
    const dx = toward.x - point.x;
    const dy = toward.y - point.y;
    const d = Math.hypot(dx, dy) || 1;
    return { x: point.x + (dx / d) * r, y: point.y + (dy / d) * r };
  };

  return (
    <div className="chart-wrap">
      <svg viewBox={`0 0 ${W} ${H}`} className="chart">
        <defs>
          <marker
            id="si-arrow"
            markerWidth="9"
            markerHeight="9"
            refX="7"
            refY="3"
            orient="auto"
            markerUnits="userSpaceOnUse"
          >
            <path d="M0,0 L7,3 L0,6 Z" style={{ fill: "var(--accent)" }} />
          </marker>
        </defs>
        {cells.map((cell) => {
          const a = pos[cell.from];
          const b = pos[cell.to];
          if (!a || !b) return null;
          const bow = (index.get(cell.from) ?? 0) < (index.get(cell.to) ?? 0) ? 1 : -1;
          const mx0 = (a.x + b.x) / 2;
          const my0 = (a.y + b.y) / 2;
          const dx = b.x - a.x;
          const dy = b.y - a.y;
          const d = Math.hypot(dx, dy) || 1;
          const control = { x: mx0 + (-dy / d) * bow * 30, y: my0 + (dx / d) * bow * 30 };
          const s = trim(a, control, NODE_R);
          const e = trim(b, control, NODE_R + 6);
          const label = { x: 0.25 * s.x + 0.5 * control.x + 0.25 * e.x, y: 0.25 * s.y + 0.5 * control.y + 0.25 * e.y };
          const opacity = 0.35 + 0.55 * (cell.magnitude / maxMag);
          return (
            <g key={`edge-${cell.from}-${cell.to}`}>
              <path
                d={`M${s.x},${s.y} Q${control.x},${control.y} ${e.x},${e.y}`}
                markerEnd="url(#si-arrow)"
                style={{ fill: "none", stroke: "var(--accent)", strokeOpacity: opacity, strokeWidth: 1.8 }}
              />
              <text
                x={label.x}
                y={label.y}
                className="axis-label"
                textAnchor="middle"
                dy="0.32em"
                style={{ paintOrder: "stroke", stroke: "var(--panel)", strokeWidth: 3 }}
              >
                {`${fmt.num(cell.shift, 1)} ${dominantChannel(cell)}`}
              </text>
            </g>
          );
        })}
        {markets.map((market) => {
          const p = pos[market];
          return (
            <g key={`node-${market}`}>
              <circle cx={p.x} cy={p.y} r={NODE_R} style={{ fill: "var(--panel-2)", stroke: "var(--accent)", strokeWidth: 1.6 }} />
              <text x={p.x} y={p.y} className="axis-label" textAnchor="middle" dy="0.32em" style={{ fill: "var(--ink)" }}>
                {market}
              </text>
            </g>
          );
        })}
      </svg>
      <div className="chart-legend">
        <span className="muted">Arrow points from the source market to the receiving market; label is the cost shift and channel.</span>
      </div>
    </div>
  );
}

export function SectorInteraction({ summary, scenarioName = null }) {
  const rows = useMemo(() => scenarioRows(summary, scenarioName), [summary, scenarioName]);
  const parsed = useMemo(() => parseInteractions(rows), [rows]);
  const [selection, setSelection] = useState(ALL_YEARS);

  // Present-guard: no "Link "-prefixed column means render nothing at all. This is
  // the config-driven gate — a single-market run is byte-for-byte unchanged.
  const { hasLinkColumns, markets, years, raw } = parsed;

  const activeSelection = selection !== ALL_YEARS && !years.includes(selection) ? ALL_YEARS : selection;
  const cells = useMemo(
    () => cellsForSelection(raw, years, activeSelection),
    [raw, years, activeSelection]
  );
  const cellMap = useMemo(() => new Map(cells.map((c) => [`${c.from}>>${c.to}`, c])), [cells]);

  const joint = useMemo(() => {
    const jrows = jointRowsFromSummary(rows);
    if (!jrows.length) return { cyclic: false, converged: false, iterations: 0 };
    return {
      cyclic: true,
      converged: Number(jrows[0][JOINT_CONVERGED_COLUMN]) === 1,
      iterations: Number(jrows[0]["Joint Outer Iterations"]) || 0,
    };
  }, [rows]);

  const reading = useMemo(() => buildReading(cells, cellMap, joint), [cells, cellMap, joint]);

  if (!hasLinkColumns || markets.length === 0) return null;

  return (
    <div className="builder-card">
      <div className="builder-card-head">
        <div>
          <div className="eyebrow">Sector interaction</div>
          <h4>Cross-market feedback</h4>
        </div>
      </div>
      {reading && <p className="lede">{reading}</p>}
      {years.length > 1 && (
        <nav className="hdr-scenarios">
          {years.map((year) => (
            <button
              key={year}
              type="button"
              className={"pill-btn " + (activeSelection === year ? "on" : "")}
              onClick={() => setSelection(year)}
            >
              {year}
            </button>
          ))}
          <button
            type="button"
            className={"pill-btn " + (activeSelection === ALL_YEARS ? "on" : "")}
            onClick={() => setSelection(ALL_YEARS)}
          >
            All years
          </button>
        </nav>
      )}
      <div className="review-grid">
        <div className="review-item review-item-wide">
          <span className="review-label">Interaction matrix</span>
          <InteractionMatrix markets={markets} cells={cells} cellMap={cellMap} />
        </div>
        <div className="review-item review-item-wide">
          <span className="review-label">Feedback graph</span>
          <FeedbackGraph markets={markets} cells={cells} />
        </div>
      </div>
    </div>
  );
}
