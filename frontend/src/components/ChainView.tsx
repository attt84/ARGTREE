"use client";

import React from 'react';
import ReactMarkdown from 'react-markdown';
import { ArrowDown, ExternalLink, Link2 } from 'lucide-react';
import type { DeepSearchResponse } from '../lib/types';

interface ChainViewProps {
  result: DeepSearchResponse | null;
}

/**
 * マルチホップ検索の結果を「調査の鎖」として表示する。
 * 各ホップ = 焦点・遡った理由・分かったこと・根拠発言（一次情報リンク付き）。
 * 最後に鎖全体を統合した解説（Markdown）を表示する。
 */
const ChainView: React.FC<ChainViewProps> = ({ result }) => {
  if (!result) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500 bg-gray-50 rounded-xl border-2 border-dashed border-gray-200 p-8 text-center">
        問いを入力すると、関連する過去の事象を1つずつ手繰って調査します
        <br />
        （例:「なぜ政治資金規正法が改正されたのか」）
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="max-w-3xl mx-auto">
        <h2 className="text-lg font-bold text-slate-800 mb-4 flex items-center gap-2">
          <Link2 className="w-5 h-5 text-blue-600" />
          調査の鎖: {result.query}
        </h2>

        {result.steps.map((step, i) => (
          <div key={step.hop}>
            {i > 0 && (
              <div className="flex items-center gap-2 my-3 ml-4 text-slate-400">
                <ArrowDown className="w-4 h-4" />
                <span className="text-xs">{step.reason}</span>
              </div>
            )}
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
              <div className="flex items-center gap-2 mb-2">
                <span className="px-2 py-0.5 rounded-full bg-blue-600 text-white text-xs font-bold">
                  ホップ {step.hop}
                </span>
                <span className="text-sm font-semibold text-slate-700">{step.focus}</span>
              </div>
              <p className="text-sm text-slate-800 leading-relaxed mb-3">{step.finding}</p>

              <div className="space-y-2">
                {step.evidence.map((ev) => (
                  <div
                    key={ev.speech_id}
                    className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-xs"
                  >
                    <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-slate-500 mb-1">
                      <span className="font-semibold text-slate-700">{ev.date}</span>
                      <span>{ev.meeting}</span>
                      <span className="font-medium text-slate-700">
                        {ev.speaker}
                        {ev.speaker_group ? `（${ev.speaker_group}）` : ''}
                      </span>
                      {ev.url && (
                        <a
                          href={ev.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-blue-600 hover:underline ml-auto"
                        >
                          一次情報 <ExternalLink className="w-3 h-3" />
                        </a>
                      )}
                    </div>
                    <p className="text-slate-600 leading-relaxed">{ev.snippet}…</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ))}

        <div className="mt-6 bg-blue-50 rounded-xl border border-blue-200 p-6">
          <h3 className="font-bold text-blue-900 mb-3">統合解説</h3>
          <div className="prose prose-sm prose-slate prose-a:text-blue-700 max-w-none">
            <ReactMarkdown>{result.synthesis}</ReactMarkdown>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChainView;
