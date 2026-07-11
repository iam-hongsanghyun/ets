import { useMemo, useState } from "react";
import { fmt } from "./MarketChart.jsx";

const CHART_W = 720;
const CHART_H = 212;
const PAD = { t: 20, r: 20, b: 40, l: 76 };
const SECTOR_PALETTE = [
  "#1f6f55",
  "#2f6f8f",
  "#8a5a2c",
  "#7a6f9b",
  "#b0543a",
  "#617a55",
  "#6a8f8c",
  "#8c6f5b",
];

function axisY(value, maxValue) {
  const ih = CHART_H - PAD.t - PAD.b;
  return PAD.t + ih - (Number(value || 0) / Math.max(maxValue, 1)) * ih;
}

function axisX(index, count) {
  const iw = CHART_W - PAD.l - PAD.r;
  const n = Math.max(1, count - 1);
  return PAD.l + (index / n) * iw;
}

function AnnualEmissionsBars({ rows, onSelectYear }) {
  const [hoverIndex, setHoverIndex] = useState(null);
  const maxValue = useMemo(
    () => Math.max(...rows.map((row) => Math.max(row.initial, row.residual, 0)), 1) * 1.1,
    [rows]
  );
  const tickValues = [0, maxValue / 2, maxValue];
  const ih = CHART_H - PAD.t - PAD.b;

  return (
    <div className="annual-metric-card">
      <div className="annual-metric-head">
        <div>
          <div className="annual-metric-title">Gross vs residual emissions</div>
          <div className="annual-metric-unit">Mt CO2</div>
        </div>
        <div className="annual-metric-legend annual-emissions-legend">
          <span><i className="annual-swatch" style={{ background: "#d7ccb7" }}></i> Gross emissions</span>
          <span><i className="annual-swatch" style={{ background: "#1f6f55" }}></i> Residual emissions</span>
        </div>
      </div>
      <svg viewBox={`0 0 ${CHART_W} ${CHART_H}`} className="chart annual-metric-chart">
        {tickValues.map((tick, index) => (
          <g key={`emissions-bars-tick-${index}`}>
            <line x1={PAD.l} x2={CHART_W - PAD.r} y1={axisY(tick, maxValue)} y2={axisY(tick, maxValue)} className="gridline subtle" />
            <text x={PAD.l - 10} y={axisY(tick, maxValue)} className="axis-label annual-axis-label" textAnchor="end" dy="0.32em">
              {fmt.num(tick, 1)} Mt
            </text>
          </g>
        ))}
        <line x1={PAD.l} x2={CHART_W - PAD.r} y1={PAD.t + ih} y2={PAD.t + ih} className="axis" />
        <line x1={PAD.l} x2={PAD.l} y1={PAD.t} y2={PAD.t + ih} className="axis" />

        {rows.map((row, index) => {
          const center = axisX(index, rows.length);
          const grossY = axisY(row.initial, maxValue);
          const residualY = axisY(row.residual, maxValue);
          return (
            <g key={`emissions-bars-${row.year}`}>
              <line x1={center} x2={center} y1={PAD.t} y2={PAD.t + ih} className="gridline subtle" />
              <rect x={center - 26} y={grossY} width="22" height={PAD.t + ih - grossY} rx="4" fill="#d7ccb7" />
              <rect x={center + 4} y={residualY} width="22" height={PAD.t + ih - residualY} rx="4" fill="#1f6f55" />
              <rect
                x={center - 34}
                y={PAD.t}
                width="68"
                height={ih}
                fill="transparent"
                style={{ cursor: "pointer" }}
                onMouseEnter={() => setHoverIndex(index)}
                onMouseLeave={() => setHoverIndex(null)}
                onClick={() => onSelectYear?.(row.year)}
              />
              <text x={center} y={CHART_H - 10} className="axis-label annual-axis-label" textAnchor="middle">
                {row.year}
              </text>
            </g>
          );
        })}

        {hoverIndex != null && rows[hoverIndex] && (
          <g transform={`translate(${Math.min(axisX(hoverIndex, rows.length) + 14, CHART_W - 178)},${PAD.t + 8})`}>
            <rect width="164" height="54" rx="6" className="hover-tip" />
            <text x="10" y="16" className="hover-tip-text">{rows[hoverIndex].year}</text>
            <text x="10" y="31" className="hover-tip-text muted">Gross {fmt.num(rows[hoverIndex].initial, 1)} Mt</text>
            <text x="10" y="45" className="hover-tip-text muted">Residual {fmt.num(rows[hoverIndex].residual, 1)} Mt</text>
          </g>
        )}
      </svg>
    </div>
  );
}

function AnnualResidualStack({ rows, participants, onSelectYear }) {
  const [hoverState, setHoverState] = useState(null);
  const maxValue = useMemo(
    () => Math.max(...rows.map((row) => row.residual || 0), 1) * 1.1,
    [rows]
  );
  const tickValues = [0, maxValue / 2, maxValue];
  const ih = CHART_H - PAD.t - PAD.b;

  return (
    <div className="annual-metric-card">
      <div className="annual-metric-head">
        <div>
          <div className="annual-metric-title">Residual emissions by participant</div>
          <div className="annual-metric-unit">Mt CO2</div>
        </div>
        <div className="annual-metric-legend annual-emissions-legend annual-emissions-legend-wrap">
          {participants.map((participant) => (
            <span key={participant.name}>
              <i className="annual-swatch" style={{ background: participant.color }}></i>
              {participant.name}
            </span>
          ))}
        </div>
      </div>
      <svg viewBox={`0 0 ${CHART_W} ${CHART_H}`} className="chart annual-metric-chart">
        {tickValues.map((tick, index) => (
          <g key={`residual-stack-tick-${index}`}>
            <line x1={PAD.l} x2={CHART_W - PAD.r} y1={axisY(tick, maxValue)} y2={axisY(tick, maxValue)} className="gridline subtle" />
            <text x={PAD.l - 10} y={axisY(tick, maxValue)} className="axis-label annual-axis-label" textAnchor="end" dy="0.32em">
              {fmt.num(tick, 1)} Mt
            </text>
          </g>
        ))}
        <line x1={PAD.l} x2={CHART_W - PAD.r} y1={PAD.t + ih} y2={PAD.t + ih} className="axis" />
        <line x1={PAD.l} x2={PAD.l} y1={PAD.t} y2={PAD.t + ih} className="axis" />

        {rows.map((row, index) => {
          const center = axisX(index, rows.length);
          let runningTop = PAD.t + ih;
          return (
            <g key={`residual-stack-${row.year}`}>
              <line x1={center} x2={center} y1={PAD.t} y2={PAD.t + ih} className="gridline subtle" />
              {row.parts.map((part) => {
                const height = (Number(part.value || 0) / Math.max(maxValue, 1)) * ih;
                const y = runningTop - height;
                runningTop = y;
                return (
                  <rect
                    key={`${row.year}-${part.name}`}
                    x={center - 20}
                    y={y}
                    width="40"
                    height={Math.max(height, 0)}
                    rx="3"
                    fill={part.color}
                    onMouseEnter={() => setHoverState({ year: row.year, participant: part.name, value: part.value, x: center })}
                    onMouseLeave={() => setHoverState(null)}
                  />
                );
              })}
              <rect
                x={center - 24}
                y={PAD.t}
                width="48"
                height={ih}
                fill="transparent"
                style={{ cursor: "pointer" }}
                onClick={() => onSelectYear?.(row.year)}
              />
              <text x={center} y={CHART_H - 10} className="axis-label annual-axis-label" textAnchor="middle">
                {row.year}
              </text>
            </g>
          );
        })}

        {hoverState && (
          <g transform={`translate(${Math.min(hoverState.x + 14, CHART_W - 178)},${PAD.t + 8})`}>
            <rect width="164" height="54" rx="6" className="hover-tip" />
            <text x="10" y="16" className="hover-tip-text">{hoverState.year}</text>
            <text x="10" y="31" className="hover-tip-text muted">{hoverState.participant}</text>
            <text x="10" y="45" className="hover-tip-text muted">{fmt.num(hoverState.value, 1)} Mt residual</text>
          </g>
        )}
      </svg>
    </div>
  );
}

export function AnnualEmissionsChart({ scenario, results, onSelectYear }) {
  const participants = useMemo(() => {
    const names = [];
    const colors = new Map();
    (scenario?.years || []).forEach((year) => {
      (year.participants || []).forEach((participant) => {
        if (!colors.has(participant.name)) {
          colors.set(participant.name, SECTOR_PALETTE[names.length % SECTOR_PALETTE.length]);
          names.push(participant.name);
        }
      });
    });
    return names.map((name) => ({ name, color: colors.get(name) }));
  }, [scenario]);

  const rows = useMemo(
    () =>
      (scenario?.years || []).map((year) => {
        const run = results?.[scenario.name]?.[String(year.year)] || {};
        const perParticipant = run.perParticipant || [];
        const initial = perParticipant.reduce((sum, participant) => sum + Number(participant.initial || 0), 0);
        const residual = perParticipant.reduce((sum, participant) => sum + Number(participant.residual || 0), 0);
        const parts = participants.map((participant) => {
          const match = perParticipant.find((item) => item.name === participant.name);
          return { name: participant.name, color: participant.color, value: Number(match?.residual || 0) };
        });
        return {
          year: String(year.year),
          initial,
          residual,
          abatement: perParticipant.reduce((sum, participant) => sum + Number(participant.abatement || 0), 0),
          parts,
        };
      }),
    [scenario, results, participants]
  );

  const summary = useMemo(() => {
    const first = rows[0] || { initial: 0, residual: 0 };
    const last = rows[rows.length - 1] || { initial: 0, residual: 0 };
    const latestAbatementShare = last.initial > 0 ? ((last.initial - last.residual) / last.initial) * 100 : 0;
    return {
      peakResidual: Math.max(...rows.map((row) => row.residual || 0), 0),
      latestResidual: last.residual || 0,
      latestAbatementShare,
    };
  }, [rows]);

  return (
    <div className="annual-emissions-grid">
      <div className="annual-emissions-summary">
        <div className="review-item">
          <span className="review-label">Peak residual emissions</span>
          <strong>{fmt.num(summary.peakResidual, 1)} Mt</strong>
        </div>
        <div className="review-item">
          <span className="review-label">Residual emissions in {rows[rows.length - 1]?.year || "latest year"}</span>
          <strong>{fmt.num(summary.latestResidual, 1)} Mt</strong>
        </div>
        <div className="review-item">
          <span className="review-label">Latest abatement share</span>
          <strong>{fmt.num(summary.latestAbatementShare, 1)}%</strong>
        </div>
      </div>
      <AnnualEmissionsBars rows={rows} onSelectYear={onSelectYear} />
      <AnnualResidualStack rows={rows} participants={participants} onSelectYear={onSelectYear} />
    </div>
  );
}
