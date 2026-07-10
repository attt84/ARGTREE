"use client";

import React, { useState } from 'react';
import axios from 'axios';
import { Search, Loader2, X, ChevronRight } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import ArgumentTree from '../components/ArgumentTree';

export default function Home() {
  const [query, setQuery] = useState('');
  const [useSuperSearch, setUseSuperSearch] = useState(false);
  const [lastQuery, setLastQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [treeData, setTreeData] = useState(null);
  const [error, setError] = useState<string | null>(null);

  // ノード詳細用ステート
  const [selectedNode, setSelectedNode] = useState<any | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [nodeDetail, setNodeDetail] = useState<string | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setTreeData(null);
    setSelectedNode(null);
    setNodeDetail(null);
    setLastQuery(query);

    try {
      const res = await axios.post('http://localhost:8000/api/search', { 
        query, 
        use_super_search: useSuperSearch 
      });
      setTreeData(res.data.tree);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'エラーが発生しました');
    } finally {
      setLoading(false);
    }
  };

  const handleNodeClick = (node: any) => {
    setSelectedNode(node);
    setNodeDetail(null); // 別ノード選択時はリセット
  };

  const fetchNodeDetail = async () => {
    if (!selectedNode || !lastQuery) return;
    setDetailLoading(true);
    try {
      const res = await axios.post('http://localhost:8000/api/node_detail', {
        query: lastQuery,
        node_label: selectedNode.label
      });
      setNodeDetail(res.data.detail_markdown);
    } catch (err: any) {
      setNodeDetail('詳細の取得に失敗しました。');
    } finally {
      setDetailLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-slate-100 text-slate-900 font-sans">
      {/* Header */}
      <header className="bg-white shadow-sm border-b px-6 py-4 flex items-center justify-between shrink-0 z-20">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded bg-blue-600 flex items-center justify-center text-white font-bold text-xl">
            A
          </div>
          <h1 className="text-xl font-bold tracking-tight text-slate-800">
            国会議論木 <span className="text-sm font-normal text-slate-500 ml-2">議論木形成プラットフォーム</span>
          </h1>
        </div>
        
        <form onSubmit={handleSearch} className="flex-1 max-w-2xl ml-8">
          <div className="flex flex-col gap-2">
            <div className="relative flex items-center">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="国会議事録から議論を検索... (例: 消費税, AI規制)"
                className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-shadow shadow-sm"
                disabled={loading}
              />
              <Search className="absolute left-3 w-5 h-5 text-slate-400" />
              <button
                type="submit"
                disabled={loading || !query.trim()}
                className="absolute right-1 px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-full text-sm font-medium transition-colors disabled:opacity-50"
              >
                検索
              </button>
            </div>
            <div className="flex items-center gap-2 pl-2">
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
            </div>
          </div>
        </form>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 p-6 relative flex min-h-0 overflow-hidden gap-6">
        
        {/* Left/Main: Tree View */}
        <div className={`flex-1 relative rounded-xl shadow-sm border border-slate-200 bg-white overflow-hidden flex flex-col transition-all duration-300`}>
          {error && (
            <div className="m-4 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg flex items-center gap-2 shrink-0">
              <span className="font-semibold">エラー:</span> {error}
            </div>
          )}

          {loading && (
            <div className="absolute inset-0 z-10 bg-white/80 backdrop-blur-sm flex flex-col items-center justify-center">
              <Loader2 className="w-12 h-12 text-blue-600 animate-spin mb-4" />
              <p className="text-slate-600 font-medium">
                {useSuperSearch 
                  ? "AIがキーワードを拡張し、多角的に国会議事録を取得・構造化しています..."
                  : "国会議事録を取得し、Geminiで議論を構造化しています..."}
              </p>
              <p className="text-sm text-slate-400 mt-2">これには数十秒かかる場合があります</p>
            </div>
          )}
          
          <ArgumentTree data={treeData} onNodeClick={handleNodeClick} />
        </div>

        {/* Right: Detail Side Panel */}
        {selectedNode && (
          <div className="w-96 shrink-0 bg-white rounded-xl shadow-sm border border-slate-200 flex flex-col overflow-hidden animate-in slide-in-from-right-8 duration-300">
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
                    onClick={fetchNodeDetail}
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
