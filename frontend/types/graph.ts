export interface GraphNode {
  id: number;
  name: string;
  type: string | null;
}

export interface GraphEdge {
  source: number;
  target: number;
  type: string;
  confidence: number;
  source_id: string | null;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}
