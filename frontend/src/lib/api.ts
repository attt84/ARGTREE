import axios from 'axios';
import type {
  CorpusStatus,
  DeepSearchResponse,
  NodeDetailResponse,
  SearchResponse,
} from './types';

const baseURL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

// マルチホップ検索はLLM呼び出しを繰り返すため長めのタイムアウトを取る
const client = axios.create({ baseURL, timeout: 300_000 });

export async function searchTree(
  query: string,
  useSuperSearch: boolean,
): Promise<SearchResponse> {
  const res = await client.post<SearchResponse>('/api/search', {
    query,
    use_super_search: useSuperSearch,
  });
  return res.data;
}

export async function fetchNodeDetail(
  query: string,
  nodeLabel: string,
): Promise<NodeDetailResponse> {
  const res = await client.post<NodeDetailResponse>('/api/node_detail', {
    query,
    node_label: nodeLabel,
  });
  return res.data;
}

export async function deepSearch(
  query: string,
  maxHops = 4,
): Promise<DeepSearchResponse> {
  const res = await client.post<DeepSearchResponse>('/api/deep_search', {
    query,
    max_hops: maxHops,
  });
  return res.data;
}

export async function fetchCorpusStatus(): Promise<CorpusStatus> {
  const res = await client.get<CorpusStatus>('/api/corpus_status');
  return res.data;
}

/** APIエラーからユーザー向けメッセージを取り出す */
export function errorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    return err.message;
  }
  if (err instanceof Error) return err.message;
  return 'エラーが発生しました';
}
