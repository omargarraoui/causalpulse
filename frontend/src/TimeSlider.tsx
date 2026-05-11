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

  return (
    <div className="time-slider">
      <div className="time-readout">
        <span>{fmt(startDate)}</span>
        <span className="time-count">{visibleCount} articles</span>
        <span>{fmt(endDate)}</span>
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
