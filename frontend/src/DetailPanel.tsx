import type { GraphNode } from "./types";
import { sourceColor } from "./palette";

interface DetailPanelProps {
  node: GraphNode;
  onClose: () => void;
}

export function DetailPanel({ node, onClose }: DetailPanelProps) {
  const activations = node.source_activations
    .map((value, index) => ({ index, value }))
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value));
  const max = Math.max(...node.source_activations.map(Math.abs), 1e-9);

  return (
    <aside className="detail-panel">
      <button className="close" onClick={onClose} aria-label="close">×</button>
      <div className="meta">
        <span className="outlet">{node.outlet}</span>
        <span className="dot-sep">·</span>
        <time>{new Date(node.dateTime).toLocaleString()}</time>
      </div>
      <h2>
        <a href={node.url} target="_blank" rel="noreferrer">{node.title}</a>
      </h2>
      {node.concepts.length > 0 && (
        <div className="concepts">
          {node.concepts.map((c) => <span key={c} className="concept">{c}</span>)}
        </div>
      )}
      <div className="source-bars">
        <div className="bars-header">latent forces</div>
        {activations.map(({ index, value }) => (
          <div key={index} className="bar-row">
            <span className="bar-label">force {index + 1}</span>
            <div className="bar-track">
              <div
                className="bar-fill"
                style={{
                  width: `${(Math.abs(value) / max) * 100}%`,
                  backgroundColor: sourceColor(index),
                  marginLeft: value < 0 ? "auto" : undefined,
                }}
              />
            </div>
            <span className="bar-value">{value.toFixed(2)}</span>
          </div>
        ))}
      </div>
    </aside>
  );
}
