"use client";

import React, { useEffect } from 'react';
import {
  ReactFlow,
  ReactFlowProvider,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  useNodesInitialized,
  useReactFlow,
  Node,
  Edge,
  MarkerType,
  Position,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import dagre from 'dagre';
import type { ArgumentNode, ArgumentTreeData } from '../lib/types';

interface ArgumentTreeProps {
  data: ArgumentTreeData | null;
  onNodeClick?: (nodeData: ArgumentNode) => void;
}

const NODE_WIDTH = 250;
const NODE_HEIGHT = 80;

// dagreによる自動レイアウト（上から下へのツリー配置）
const layoutElements = (nodes: Node[], edges: Edge[]): Node[] => {
  const graph = new dagre.graphlib.Graph();
  graph.setDefaultEdgeLabel(() => ({}));
  graph.setGraph({ rankdir: 'TB', ranksep: 100, nodesep: 50 });

  nodes.forEach((node) => {
    graph.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  });
  edges.forEach((edge) => {
    graph.setEdge(edge.source, edge.target);
  });

  dagre.layout(graph);

  return nodes.map((node) => {
    const { x, y } = graph.node(node.id);
    return {
      ...node,
      targetPosition: Position.Top,
      sourcePosition: Position.Bottom,
      // dagreは中心座標、React Flowは左上座標を使うため変換する
      position: { x: x - NODE_WIDTH / 2, y: y - NODE_HEIGHT / 2 },
    };
  });
};

// ミニマップ用の色（ノード本体は透過スタイルのため、別途色を与えないと描画されない）
const MINIMAP_COLORS: Record<string, string> = {
  pro: '#4ade80',
  con: '#f87171',
  theme: '#2563eb',
  solution: '#facc15',
};

const nodeStyle = (type: ArgumentNode['type']): string => {
  switch (type) {
    case 'pro':
      return 'bg-green-50 border-green-400 text-green-900';
    case 'con':
      return 'bg-red-50 border-red-400 text-red-900';
    case 'theme':
      return 'bg-blue-600 border-blue-800 text-white font-bold';
    case 'solution':
      return 'bg-yellow-50 border-yellow-400 text-yellow-900';
    default:
      return 'bg-white border-gray-300';
  }
};

const ArgumentTreeInner: React.FC<ArgumentTreeProps> = ({ data, onNodeClick }) => {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const nodesInitialized = useNodesInitialized();
  const { fitView } = useReactFlow();

  // fitViewプロパティはマウント時にしか効かず、ノードは検索後に非同期で入るため、
  // ノードの実寸が確定したタイミングで明示的に全体表示に合わせる
  useEffect(() => {
    if (nodesInitialized && nodes.length > 0) {
      fitView({ padding: 0.15 });
    }
  }, [nodesInitialized, nodes.length, fitView]);

  useEffect(() => {
    if (!data) return;

    const initialNodes: Node[] = data.nodes.map((n) => ({
      id: n.id,
      position: { x: 0, y: 0 },
      data: {
        argType: n.type,
        label: (
          <div className={`p-3 rounded-lg shadow-sm border-2 w-60 text-sm ${nodeStyle(n.type)}`}>
            <div className="font-semibold mb-1">{n.label}</div>
            {n.source && <div className="text-xs opacity-75 truncate">発言: {n.source}</div>}
          </div>
        ),
      },
      type: 'default',
      style: { border: 'none', background: 'transparent', padding: 0 },
    }));

    const initialEdges: Edge[] = data.edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
    }));

    setNodes(layoutElements(initialNodes, initialEdges));
    setEdges(initialEdges);
  }, [data, setNodes, setEdges]);

  if (!data) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500 bg-gray-50 rounded-xl border-2 border-dashed border-gray-200">
        キーワードを入力して議論木を生成してください
      </div>
    );
  }

  return (
    <div className="w-full h-full bg-slate-50 rounded-xl overflow-hidden border border-gray-200 shadow-inner relative">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={(_, node) => {
          if (onNodeClick && data) {
            const originalNode = data.nodes.find((n) => n.id === node.id);
            if (originalNode) onNodeClick(originalNode);
          }
        }}
        fitView
        attributionPosition="bottom-right"
      >
        <Controls />
        <MiniMap
          zoomable
          pannable
          nodeColor={(node) => MINIMAP_COLORS[node.data?.argType as string] ?? '#cbd5e1'}
          nodeStrokeWidth={3}
        />
        <Background color="#aaa" gap={16} />
      </ReactFlow>
    </div>
  );
};

// useReactFlow を使うため Provider 配下に置く
const ArgumentTree: React.FC<ArgumentTreeProps> = (props) => (
  <ReactFlowProvider>
    <ArgumentTreeInner {...props} />
  </ReactFlowProvider>
);

export default ArgumentTree;
