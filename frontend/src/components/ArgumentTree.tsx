"use client";

import React, { useCallback, useEffect } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  Node,
  Edge,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

interface TreeData {
  nodes: { id: string; label: string; type: string; source?: string }[];
  edges: { id: string; source: string; target: string }[];
}

interface ArgumentTreeProps {
  data: TreeData | null;
  onNodeClick?: (nodeData: { id: string; label: string; type: string; source?: string }) => void;
}

// 簡単な自動レイアウト（簡易版のダグリッジ）
const getLayoutedElements = (nodes: any[], edges: any[], direction = 'TB') => {
  const isHorizontal = direction === 'LR';
  const dagreGraph = new (require('dagre')).graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  const nodeWidth = 250;
  const nodeHeight = 80;

  dagreGraph.setGraph({ rankdir: direction, ranksep: 100, nodesep: 50 });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  require('dagre').layout(dagreGraph);

  nodes.forEach((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    node.targetPosition = isHorizontal ? 'left' : 'top';
    node.sourcePosition = isHorizontal ? 'right' : 'bottom';

    // We are shifting the dagre node position (anchor=center center) to the top left
    // so it matches the React Flow node anchor point (top left).
    node.position = {
      x: nodeWithPosition.x - nodeWidth / 2,
      y: nodeWithPosition.y - nodeHeight / 2,
    };

    return node;
  });

  return { nodes, edges };
};

const ArgumentTree: React.FC<ArgumentTreeProps> = ({ data, onNodeClick }) => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  useEffect(() => {
    if (!data) return;

    const initialNodes: Node[] = data.nodes.map((n) => {
      let bgClass = 'bg-white border-gray-300';
      if (n.type === 'pro') bgClass = 'bg-green-50 border-green-400 text-green-900';
      if (n.type === 'con') bgClass = 'bg-red-50 border-red-400 text-red-900';
      if (n.type === 'theme') bgClass = 'bg-blue-600 border-blue-800 text-white font-bold';
      if (n.type === 'solution') bgClass = 'bg-yellow-50 border-yellow-400 text-yellow-900';

      return {
        id: n.id,
        position: { x: 0, y: 0 },
        data: {
          label: (
            <div className={`p-3 rounded-lg shadow-sm border-2 w-60 text-sm ${bgClass}`}>
              <div className="font-semibold mb-1">{n.label}</div>
              {n.source && <div className="text-xs opacity-75 truncate">発言: {n.source}</div>}
            </div>
          ),
        },
        type: 'default',
        style: { border: 'none', background: 'transparent', padding: 0 },
      };
    });

    const initialEdges: Edge[] = data.edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      animated: true,
      markerEnd: {
        type: MarkerType.ArrowClosed,
      },
    }));

    try {
        const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
            initialNodes,
            initialEdges,
            'TB'
        );
        setNodes(layoutedNodes);
        setEdges(layoutedEdges);
    } catch (e) {
        // Fallback without dagre if not installed
        setNodes(initialNodes.map((n, i) => ({ ...n, position: { x: (i % 3) * 300, y: Math.floor(i / 3) * 150 } })));
        setEdges(initialEdges);
    }

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
            const originalNode = data.nodes.find(n => n.id === node.id);
            if (originalNode) onNodeClick(originalNode);
          }
        }}
        fitView
        attributionPosition="bottom-right"
      >
        <Controls />
        <MiniMap zoomable pannable nodeClassName={(n) => 'bg-blue-500'} />
        <Background color="#aaa" gap={16} />
      </ReactFlow>
    </div>
  );
};

export default ArgumentTree;
