import { useMemo } from "react";

interface TimeSliderProps {
  value: [number, number];
  onChange: (value: [number, number]) => void;
  dateMin: Date;
  dateMax: Date;
  visibleCount: number;
}

const MIN_WINDOW = 0.04;

export function TimeSlider({ value, onChange, dateMin, dateMax, visibleCount }: TimeSliderProps) {
  const [start, end] = value;
  const spanMs = dateMax.getTime() - dateMin.getTime();
  const startDate = useMemo(() => new Date(dateMin.getTime() + spanMs * start), [dateMin, spanMs, start]);
  const endDate = useMemo(() => new Date(dateMin.getTime() + spanMs * end), [dateMin, spanMs, end]);

  const handlePreset = (days: number | null) => {
    if (days === null) {
      // All time
      onChange([0, 1]);
    } else {
      // Calculate window for last N days
      const now = dateMax.getTime();
      const nDaysAgo = now - days * 24 * 60 * 60 * 1000;
      const newStart = Math.max(0, (nDaysAgo - dateMin.getTime()) / spanMs);
      onChange([newStart, 1]);
    }
  };

  const currentSpanDays = (endDate.getTime() - startDate.getTime()) / (24 * 60 * 60 * 1000);

  return (
    <div className="time-slider">
      <div className="time-slider-header">
        <div className="time-slider-title">
          <span className="label">Time Span</span>
          <span className="span-info">{currentSpanDays.toFixed(1)} days</span>
        </div>
        <div className="preset-buttons">
          <button
            className={`preset ${end === 1 && start === 0 ? "active" : ""}`}
            onClick={() => handlePreset(null)}
            title="Show all available data"
          >
            All
          </button>
          <button
            className={`preset ${end === 1 && currentSpanDays <= 7.5 && currentSpanDays > 6.5 ? "active" : ""}`}
            onClick={() => handlePreset(7)}
            title="Last 7 days"
          >
            1w
          </button>
          <button
            className={`preset ${end === 1 && currentSpanDays <= 31.5 && currentSpanDays > 28.5 ? "active" : ""}`}
            onClick={() => handlePreset(30)}
            title="Last 30 days"
          >
            1m
          </button>
          <button
            className={`preset ${end === 1 && currentSpanDays <= 92.5 && currentSpanDays > 88.5 ? "active" : ""}`}
            onClick={() => handlePreset(90)}
            title="Last 90 days"
          >
            3m
          </button>
        </div>
      </div>
      <div className="time-readout">
        <span className="time-date">{fmt(startDate)}</span>
        <span className="time-count">{visibleCount} articles</span>
        <span className="time-date">{fmt(endDate)}</span>
      </div>
      <div className="dual-track">
        <input
          type="range"
          min={0}
          max={1000}
          value={Math.round(start * 1000)}
          onChange={(e) => {
            const v = Number(e.target.value) / 1000;
            onChange([Math.min(v, end - MIN_WINDOW), end]);
          }}
        />
        <input
          type="range"
          min={0}
          max={1000}
          value={Math.round(end * 1000)}
          onChange={(e) => {
            const v = Number(e.target.value) / 1000;
            onChange([start, Math.max(v, start + MIN_WINDOW)]);
          }}
        />
      </div>
    </div>
  );
}

function fmt(d: Date): string {
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
