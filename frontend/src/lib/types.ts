// バックエンドAPI（FastAPI）のレスポンス型定義。backend/app/models.py と対応する。

export type NodeType = 'theme' | 'pro' | 'con' | 'neutral' | 'solution';

export interface ArgumentNode {
  id: string;
  label: string;
  type: NodeType;
  source?: string | null;
}

export interface ArgumentEdge {
  id: string;
  source: string;
  target: string;
}

export interface ArgumentTreeData {
  nodes: ArgumentNode[];
  edges: ArgumentEdge[];
}

export interface SearchResponse {
  query: string;
  expanded_queries: string[];
  tree: ArgumentTreeData;
}

export interface NodeDetailResponse {
  node_label: string;
  detail_markdown: string;
}

export interface EvidenceItem {
  speech_id: string;
  date: string;
  meeting: string;
  speaker: string;
  speaker_group?: string | null;
  snippet: string;
  url: string;
}

export interface HopStep {
  hop: number;
  focus: string;
  reason: string;
  finding: string;
  evidence: EvidenceItem[];
}

export interface DeepSearchResponse {
  query: string;
  steps: HopStep[];
  synthesis: string;
}

export interface CorpusStatus {
  ready: boolean;
  speech_count: number;
  date_from?: string | null;
  date_until?: string | null;
  entity_count: number;
  mention_count: number;
  embedding_count: number;
}
