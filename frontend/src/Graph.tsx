import { useEffect, useRef } from "react";
import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
import fcose from "cytoscape-fcose";
import type { GraphData, GraphNode, ViewMode } from "./types";
import { sourceColor, topicColor } from "./palette";

cytoscape.use(fcose);

interface GraphProps {
  data: GraphData;
  viewMode: ViewMode;
  focusedSource: number | null;
  crossDomain: boolean;
  onSelect: (node: GraphNode) => void;
}

export function Graph({ data, viewMode, focusedSource, crossDomain, onSelect }: GraphProps) {
  const container = useRef<HTMLDivElement>(null);
  const cy = useRef<Core | null>(null);

  // Build only when the node/edge set changes — view-mode and focus updates
  // mutate the style instead, which is several times cheaper than rebuilding
  // the graph from scratch.
  useEffect(() => {
    if (!container.current) return;

    const elements: ElementDefinition[] = [
      ...data.nodes.map((node) => ({ data: { id: `n${node.id}`, label: truncate(node.title, 38), node } })),
      ...data.edges.map((edge, i) => ({
        data: {
          id: `e${i}`,
          source: `n${edge.source}`,
          target: `n${edge.target}`,
          edge,
        },
      })),
    ];

    const instance = cytoscape({
      container: container.current,
      elements,
      layout: {
        name: "fcose",
        animate: false,
        randomize: true,
        nodeRepulsion: 8000,
        idealEdgeLength: 110,
        edgeElasticity: 0.45,
        gravity: 0.15,
        numIter: 1500,
        tile: false,
      } as cytoscape.LayoutOptions,
      minZoom: 0.2,
      maxZoom: 3,
      wheelSensitivity: 0.18,
    });

    instance.on("tap", "node", (event) => {
      onSelect(event.target.data("node"));
    });

    cy.current = instance;
    return () => {
      instance.destroy();
      cy.current = null;
    };
  }, [data, onSelect]);

  useEffect(() => {
    if (!cy.current) return;
    cy.current.style(buildStyle(data, viewMode, focusedSource, crossDomain));
  }, [data, viewMode, focusedSource, crossDomain]);

  return <div ref={container} className="graph-canvas" />;
}

// cytoscape's TS types don't capture function-form style values cleanly, so
// the style array is typed loosely. The runtime contract is what matters.
function buildStyle(
  data: GraphData,
  viewMode: ViewMode,
  focused: number | null,
  crossDomain: boolean,
): cytoscape.StylesheetCSS[] {
  const byId = new Map(data.nodes.map((n) => [n.id, n]));
  const nodeFill = (el: cytoscape.NodeSingular) => {
    const node = el.data("node") as GraphNode;
    return viewMode === "topic" ? topicColor(node.category) : sourceColor(node.dominant_source);
  };
  const nodeSize = (el: cytoscape.NodeSingular) => 10 + 40 * sizeFromShares(el.data("node"));
  const nodeOpacity = (el: cytoscape.NodeSingular) => {
    if (viewMode !== "source" || focused === null) return 1;
    const a = Math.abs((el.data("node") as GraphNode).source_activations[focused] ?? 0);
    return Math.max(0.12, Math.min(1.0, a * 2.5));
  };

  return [
    {
      selector: "node",
      style: {
        "background-color": nodeFill,
        width: nodeSize,
        height: nodeSize,
        "border-width": 0,
        label: "data(label)",
        color: "#cfd0dc",
        "font-size": 8,
        "font-family": "Inter, sans-serif",
        "text-valign": "bottom",
        "text-margin-y": 4,
        "text-max-width": 110,
        "text-wrap": "ellipsis",
        opacity: nodeOpacity,
      },
    },
    {
      selector: "node:selected",
      style: { "border-width": 2, "border-color": "#ffffff" },
    },
    {
      selector: "edge",
      style: {
        width: (el: cytoscape.EdgeSingular) => 0.4 + 3 * (el.data("edge").weight as number),
        "line-color": (el: cytoscape.EdgeSingular) => edgeColor(el.data("edge"), byId, crossDomain, viewMode),
        opacity: (el: cytoscape.EdgeSingular) => edgeOpacity(el.data("edge"), byId, viewMode, focused),
        "curve-style": "haystack",
      },
    },
  ] as cytoscape.StylesheetCSS[];
}

function edgeColor(
  edge: GraphData["edges"][number],
  byId: Map<number, GraphNode>,
  crossDomain: boolean,
  viewMode: ViewMode,
): string {
  if (crossDomain) {
    const a = byId.get(edge.source)!;
    const b = byId.get(edge.target)!;
    if (a.category !== b.category && edge.source_cosine > 0.55) {
      return "#ffce4f";
    }
  }
  const base = viewMode === "source" ? "#5a4f9f" : "#3a4055";
  return shade(base, edge.weight);
}

function edgeOpacity(
  edge: GraphData["edges"][number],
  byId: Map<number, GraphNode>,
  viewMode: ViewMode,
  focused: number | null,
): number {
  if (viewMode === "source" && focused !== null) {
    const a = Math.abs(byId.get(edge.source)!.source_activations[focused] ?? 0);
    const b = Math.abs(byId.get(edge.target)!.source_activations[focused] ?? 0);
    return Math.max(0.05, Math.min(0.9, (a + b) * 0.6));
  }
  return 0.55;
}

function sizeFromShares(node: GraphNode): number {
  return Math.min(1, Math.log1p(node.social_score) / 12);
}

function truncate(text: string, n: number): string {
  return text.length > n ? text.slice(0, n - 1) + "…" : text;
}

function shade(hex: string, intensity: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  const t = Math.min(1, intensity);
  return `rgb(${Math.round(r + (210 - r) * t)},${Math.round(g + (210 - g) * t)},${Math.round(b + (210 - b) * t)})`;
}
