"use client";

import React, { useState } from 'react';
import axios from 'axios';
import { Search, Loader2 } from 'lucide-react';
import ArgumentTree from '../components/ArgumentTree';

export default function Home() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [treeData, setTreeData] = useState(null);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setTreeData(null);

    try {
      const res = await axios.post('http://localhost:8000/api/search', { query });
      setTreeData(res.data.tree);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'エラーが発生しました');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-slate-100 text-slate-900 font-sans">
      {/* Header */}
      <header className="bg-white shadow-sm border-b px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded bg-blue-600 flex items-center justify-center text-white font-bold text-xl">
            A
          </div>
          <h1 className="text-xl font-bold tracking-tight text-slate-800">
            argdrasill <span className="text-sm font-normal text-slate-500 ml-2">議論木形成プラットフォーム</span>
          </h1>
        </div>
        
        <form onSubmit={handleSearch} className="flex-1 max-w-2xl ml-8">
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
        </form>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 p-6 relative flex flex-col min-h-0">
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg flex items-center gap-2">
            <span className="font-semibold">エラー:</span> {error}
          </div>
        )}

        <div className="flex-1 relative rounded-xl shadow-sm border border-slate-200 bg-white overflow-hidden flex flex-col">
          {loading ? (
            <div className="absolute inset-0 z-10 bg-white/80 backdrop-blur-sm flex flex-col items-center justify-center">
              <Loader2 className="w-12 h-12 text-blue-600 animate-spin mb-4" />
              <p className="text-slate-600 font-medium">国会議事録を取得し、Geminiで議論を構造化しています...</p>
              <p className="text-sm text-slate-400 mt-2">これには数十秒かかる場合があります</p>
            </div>
          ) : null}
          
          <ArgumentTree data={treeData} />
        </div>
      </main>
    </div>
  );
}
