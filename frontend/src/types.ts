export type ViewMode = "topic" | "source";

export interface GraphNode {
  id: number;
  uri: string;
  title: string;
  url: string;
  outlet: string;
  dateTime: string;
  category: string;
  concepts: string[];
  social_score: number;
  sentiment: number | null;
  image: string | null;
  dominant_source: number;
  source_activations: number[];
  source_norm: number;
}

export interface GraphEdge {
  source: number;
  target: number;
  weight: number;
  semantic: number;
  source_cosine: number;
  entity_jaccard: number;
  temporal: number;
}

export interface GraphData {
  generated_at: string;
  n_articles: number;
  n_sources: number;
  length_scales_hours: number[];
  nodes: GraphNode[];
  edges: GraphEdge[];
  training_history: Array<Record<string, number>>;
}
