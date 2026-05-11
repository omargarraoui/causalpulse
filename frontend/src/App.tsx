import { useEffect, useMemo, useState } from "react";
import { Controls } from "./Controls";
import { DetailPanel } from "./DetailPanel";
import { Graph } from "./Graph";
import { InfoModal } from "./InfoModal";
import { MobileWarning } from "./MobileWarning";
import { TimeSlider } from "./TimeSlider";
import type { GraphData, GraphNode, ViewMode } from "./types";

const DATA_URL = `${import.meta.env.BASE_URL}data.json`;

export function App() {
  const [data, setData] = useState<GraphData | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("source");
  const [focusedSource, setFocusedSource] = useState<number | null>(null);
  const [crossDomain, setCrossDomain] = useState(true);
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [window, setWindow] = useState<[number, number]>([0, 1]);
  const [infoOpen, setInfoOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [dismissedMobileWarning, setDismissedMobileWarning] = useState(false);

  useEffect(() => {
    const checkMobile = () => globalThis.window.innerWidth <= 768;
    setIsMobile(checkMobile());
    globalThis.window.addEventListener("resize", () => setIsMobile(checkMobile()));
  }, []);

  useEffect(() => {
    fetch(DATA_URL).then((r) => r.json()).then(setData);
  }, []);

  const dateRange = useMemo(() => {
    if (!data || data.nodes.length === 0) return null;
    const times = data.nodes.map((n) => new Date(n.dateTime).getTime());
    return { min: new Date(Math.min(...times)), max: new Date(Math.max(...times)) };
  }, [data]);

  const filtered = useMemo(() => {
    if (!data || !dateRange) return null;
    const span = dateRange.max.getTime() - dateRange.min.getTime() || 1;
    const lo = dateRange.min.getTime() + span * window[0];
    const hi = dateRange.min.getTime() + span * window[1];
    const keepIds = new Set(
      data.nodes
        .filter((n) => {
          const t = new Date(n.dateTime).getTime();
          return t >= lo && t <= hi;
        })
        .map((n) => n.id),
    );
    return {
      ...data,
      nodes: data.nodes.filter((n) => keepIds.has(n.id)),
      edges: data.edges.filter((e) => keepIds.has(e.source) && keepIds.has(e.target)),
    };
  }, [data, dateRange, window]);

  if (!data) return <div className="loading">loading…</div>;
  if (!filtered || !dateRange) {
    return <div className="loading">no data yet · waiting for the next scheduled refresh</div>;
  }

  return (
    <div className="app">
      <header className="header">
        <div className="brand">
          <h1>CausalPulse</h1>
          <span className="subtitle">
            {data.n_articles} articles · {data.n_sources} latent forces · updated {timeAgo(data.generated_at)}
          </span>
        </div>
        <button className="info-button" onClick={() => setInfoOpen(true)} title="About CausalPulse">
          ℹ
        </button>
        <Controls
          viewMode={viewMode}
          setViewMode={setViewMode}
          focusedSource={focusedSource}
          setFocusedSource={setFocusedSource}
          crossDomain={crossDomain}
          setCrossDomain={setCrossDomain}
          nSources={data.n_sources}
          lengthScales={data.length_scales_hours}
        />
      </header>

      <main className="main">
        <Graph
          data={filtered}
          viewMode={viewMode}
          focusedSource={focusedSource}
          crossDomain={crossDomain}
          onSelect={setSelected}
        />
        {selected && <DetailPanel node={selected} onClose={() => setSelected(null)} />}
      </main>

      <footer className="footer">
        <TimeSlider
          value={window}
          onChange={setWindow}
          dateMin={dateRange.min}
          dateMax={dateRange.max}
          visibleCount={filtered.nodes.length}
        />
      </footer>

      <InfoModal open={infoOpen} onClose={() => setInfoOpen(false)} />
      {isMobile && !dismissedMobileWarning && (
        <MobileWarning onDismiss={() => setDismissedMobileWarning(true)} />
      )}
    </div>
  );
}

function timeAgo(iso: string): string {
  const hours = (Date.now() - new Date(iso).getTime()) / 3.6e6;
  if (hours < 1) return `${Math.max(1, Math.round(hours * 60))}m ago`;
  if (hours < 24) return `${Math.round(hours)}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}
