"use client";

import React, { useEffect, useState } from 'react';
import { Search, Loader2, X, ChevronRight, Database } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import ArgumentTree from '../components/ArgumentTree';
import ChainView from '../components/ChainView';
import {
  deepSearch,
  errorMessage,
  fetchCorpusStatus,
  fetchNodeDetail,
  searchTree,
} from '../lib/api';
import type {
  ArgumentNode,
  ArgumentTreeData,
  CorpusStatus,
  DeepSearchResponse,
} from '../lib/types';

type Mode = 'tree' | 'chain';

export default function Home() {
  const [mode, setMode] = useState<Mode>('tree');
  const [query, setQuery] = useState('');
  const [useSuperSearch, setUseSuperSearch] = useState(false);
  const [lastQuery, setLastQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 議論木モード
  const [treeData, setTreeData] = useState<ArgumentTreeData | null>(null);
  const [expandedQueries, setExpandedQueries] = useState<string[]>([]);
  const [selectedNode, setSelectedNode] = useState<ArgumentNode | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [nodeDetail, setNodeDetail] = useState<string | null>(null);

  // 深掘り追跡（マルチホップ）モード
  const [chainResult, setChainResult] = useState<DeepSearchResponse | null>(null);
  const [corpus, setCorpus] = useState<CorpusStatus | null>(null);

  useEffect(() => {
    fetchCorpusStatus().then(setCorpus).catch(() => setCorpus(null));
  }, []);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || loading) return;

    setLoading(true);
    setError(null);
    setLastQuery(query);

    try {
      if (mode === 'tree') {
        setTreeData(null);
        setExpandedQueries([]);
        setSelectedNode(null);
        setNodeDetail(null);
        const res = await searchTree(query, useSuperSearch);
        setTreeData(res.tree);
        setExpandedQueries(res.expanded_queries);
      } else {
        setChainResult(null);
        const res = await deepSearch(query);
        setChainResult(res);
      }
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleNodeClick = (node: ArgumentNode) => {
    setSelectedNode(node);
    setNodeDetail(null);
  };

  const loadNodeDetail = async () => {
    if (!selectedNode || !lastQuery) return;
    setDetailLoading(true);
    try {
      const res = await fetchNodeDetail(lastQuery, selectedNode.label);
      setNodeDetail(res.detail_markdown);
    } catch (err) {
      setNodeDetail(`詳細の取得に失敗しました: ${errorMessage(err)}`);
    } finally {
      setDetailLoading(false);
    }
  };

  const tabClass = (m: Mode) =>
    `px-4 py-1.5 rounded-full text-sm font-semibold transition-colors ${
      mode === m
        ? 'bg-blue-600 text-white'
        : 'text-slate-600 hover:bg-slate-200'
    }`;

  return (
    <div className="flex flex-col h-screen bg-slate-100 text-slate-900 font-sans">
      {/* Header */}
      <header className="bg-white shadow-sm border-b px-6 py-3 shrink-0 z-20">
        <div className="flex items-center gap-6 flex-wrap">
          <div className="flex items-center gap-2 shrink-0">
            <div className="w-8 h-8 rounded bg-blue-600 flex items-center justify-center text-white font-bold text-xl">
              A
            </div>
            <h1 className="text-xl font-bold tracking-tight text-slate-800">
              国会議論木
            </h1>
          </div>

          <div className="flex items-center gap-1 bg-slate-100 rounded-full p-1">
            <button className={tabClass('tree')} onClick={() => setMode('tree')}>
              議論木
            </button>
            <button className={tabClass('chain')} onClick={() => setMode('chain')}>
              深掘り追跡
            </button>
          </div>

          <form onSubmit={handleSearch} className="flex-1 min-w-[300px] max-w-2xl">
            <div className="relative flex items-center">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={
                  mode === 'tree'
                    ? '国会議事録から議論を検索... (例: 消費税, AI規制)'
                    : '問いを入力... (例: なぜ政治資金規正法が改正されたのか)'
                }
                className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-shadow shadow-sm"
                disabled={loading}
              />
              <Search className="absolute left-3 w-5 h-5 text-slate-400" />
              <button
                type="submit"
                disabled={loading || !query.trim()}
                className="absolute right-1 px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-full text-sm font-medium transition-colors disabled:opacity-50"
              >
                {mode === 'tree' ? '検索' : '追跡'}
              </button>
            </div>
          </form>
        </div>

        <div className="flex items-center gap-4 mt-2 pl-1 min-h-[24px]">
          {mode === 'tree' ? (
            <label className="flex items-center gap-2 cursor-pointer text-sm text-slate-600 font-medium">
              <input
                type="checkbox"
                checked={useSuperSearch}
                onChange={(e) => setUseSuperSearch(e.target.checked)}
                disabled={loading}
                className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"
              />
              超検索 (AIによるキーワード拡張で周辺議論も取得)
            </label>
          ) : (
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <Database className="w-4 h-4" />
              {corpus?.ready ? (
                <span>
                  コーパス: {corpus.speech_count.toLocaleString()}発言（
                  {corpus.date_from}〜{corpus.date_until}）／ エンティティ{' '}
                  {corpus.entity_count.toLocaleString()} ／ ベクトル索引{' '}
                  {corpus.embedding_count.toLocaleString()}
                </span>
              ) : (
                <span className="text-amber-600">
                  コーパス未構築です（backendで python -m app.ingest を実行してください）
                </span>
              )}
            </div>
          )}
          {mode === 'tree' && expandedQueries.length > 1 && (
            <div className="flex items-center gap-1 flex-wrap text-xs">
              <span className="text-slate-400">検索クエリ:</span>
              {expandedQueries.map((q) => (
                <span
                  key={q}
                  className="px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200"
                >
                  {q}
                </span>
              ))}
            </div>
          )}
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 p-6 relative flex min-h-0 overflow-hidden gap-6">
        <div className="flex-1 relative rounded-xl shadow-sm border border-slate-200 bg-white overflow-hidden flex flex-col transition-all duration-300">
          {error && (
            <div className="m-4 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg flex items-center gap-2 shrink-0">
              <span className="font-semibold">エラー:</span> {error}
            </div>
          )}

          {loading && (
            <div className="absolute inset-0 z-10 bg-white/80 backdrop-blur-sm flex flex-col items-center justify-center">
              <Loader2 className="w-12 h-12 text-blue-600 animate-spin mb-4" />
              <p className="text-slate-600 font-medium">
                {mode === 'tree'
                  ? useSuperSearch
                    ? 'AIがキーワードを拡張し、多角的に国会議事録を取得・構造化しています...'
                    : '国会議事録を取得し、Geminiで議論を構造化しています...'
                  : '関連する過去の事象を1つずつ手繰っています（複数ホップの調査のため数分かかることがあります）...'}
              </p>
              <p className="text-sm text-slate-400 mt-2">これには時間がかかる場合があります</p>
            </div>
          )}

          {mode === 'tree' ? (
            <ArgumentTree data={treeData} onNodeClick={handleNodeClick} />
          ) : (
            <ChainView result={chainResult} />
          )}
        </div>

        {/* Right: Detail Side Panel (議論木モードのみ) */}
        {mode === 'tree' && selectedNode && (
          <div className="w-96 shrink-0 bg-white rounded-xl shadow-sm border border-slate-200 flex flex-col overflow-hidden">
            <div className="p-4 border-b flex justify-between items-center bg-slate-50 shrink-0">
              <h2 className="font-bold text-slate-800 flex items-center gap-2">
                論点の深掘り
              </h2>
              <button
                onClick={() => setSelectedNode(null)}
                className="p-1 hover:bg-slate-200 rounded-full transition-colors text-slate-500"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto flex-1">
              <div className="mb-6">
                <div className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">
                  対象ノード
                </div>
                <div className="text-lg font-semibold text-slate-800 border-l-4 border-blue-500 pl-3">
                  {selectedNode.label}
                </div>
                {selectedNode.source && (
                  <div className="text-sm text-slate-500 mt-2">
                    発言者: {selectedNode.source}
                  </div>
                )}
              </div>

              {!nodeDetail && !detailLoading && (
                <div className="bg-blue-50 rounded-lg p-5 border border-blue-100 text-center mt-8">
                  <p className="text-sm text-blue-800 mb-4">
                    この論点について、AIが実際の国会議事録を参照し、詳細な背景や引用、対立意見を深掘りします。
                  </p>
                  <button
                    onClick={loadNodeDetail}
                    className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-semibold transition-colors flex items-center justify-center gap-2"
                  >
                    AIで深掘り解説を生成 <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              )}

              {detailLoading && (
                <div className="flex flex-col items-center justify-center py-12 text-slate-500">
                  <Loader2 className="w-8 h-8 animate-spin mb-4 text-blue-500" />
                  <p className="text-sm">議事録を参照して解説を生成中...</p>
                </div>
              )}

              {nodeDetail && !detailLoading && (
                <div className="prose prose-sm prose-slate prose-h3:text-blue-700 prose-h3:text-base prose-h3:mt-6 prose-h3:mb-2 prose-p:leading-relaxed max-w-none">
                  <ReactMarkdown>{nodeDetail}</ReactMarkdown>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
