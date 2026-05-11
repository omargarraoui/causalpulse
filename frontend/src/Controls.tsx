import type { ViewMode } from "./types";
import { sourceColor } from "./palette";

interface ControlsProps {
  viewMode: ViewMode;
  setViewMode: (mode: ViewMode) => void;
  focusedSource: number | null;
  setFocusedSource: (index: number | null) => void;
  crossDomain: boolean;
  setCrossDomain: (value: boolean) => void;
  nSources: number;
  lengthScales: number[];
}

export function Controls({
  viewMode,
  setViewMode,
  focusedSource,
  setFocusedSource,
  crossDomain,
  setCrossDomain,
  nSources,
  lengthScales,
}: ControlsProps) {
  return (
    <div className="controls">
      <div className="toggle">
        <button
          className={viewMode === "topic" ? "active" : ""}
          onClick={() => {
            setViewMode("topic");
            setFocusedSource(null);
          }}
        >
          Topic
        </button>
        <button
          className={viewMode === "source" ? "active" : ""}
          onClick={() => setViewMode("source")}
        >
          Source
        </button>
      </div>

      <label className="checkbox">
        <input type="checkbox" checked={crossDomain} onChange={(e) => setCrossDomain(e.target.checked)} />
        <span>cross-domain links</span>
      </label>

      {viewMode === "source" && (
        <div className="source-legend">
          <button
            className={focusedSource === null ? "chip active" : "chip"}
            onClick={() => setFocusedSource(null)}
          >
            all
          </button>
          {Array.from({ length: nSources }, (_, i) => (
            <button
              key={i}
              className={focusedSource === i ? "chip active" : "chip"}
              onClick={() => setFocusedSource(i)}
              style={{ borderColor: sourceColor(i) }}
            >
              <span className="dot" style={{ backgroundColor: sourceColor(i) }} />
              <span className="chip-label">force {i + 1}</span>
              <span className="chip-scale">{formatHours(lengthScales[i])}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function formatHours(h: number): string {
  if (h < 1) return `${Math.round(h * 60)}m`;
  if (h < 48) return `${h.toFixed(1)}h`;
  return `${(h / 24).toFixed(1)}d`;
}
