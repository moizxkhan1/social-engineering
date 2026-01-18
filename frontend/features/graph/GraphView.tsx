"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import { Card, Tag } from "@/components";
import type { GraphData, GraphNode, GraphEdge } from "@/types";
import { formatRelationshipType } from "@/lib/format";

interface GraphViewProps {
  data: GraphData | null;
  isLoading?: boolean;
}

interface PositionedNode extends GraphNode {
  x: number;
  y: number;
}

function getNodeColor(type: string | null): string {
  switch (type?.toLowerCase()) {
    case "company":
    case "organization":
      return "#3b82f6"; // blue
    case "person":
      return "#10b981"; // emerald
    default:
      return "#6b7280"; // gray
  }
}

function getEdgeColor(type: string): string {
  switch (type) {
    case "founder":
    case "ceo":
      return "#8b5cf6"; // violet
    case "investor":
      return "#10b981"; // emerald
    case "competitor":
      return "#ef4444"; // red
    case "employee":
      return "#3b82f6"; // blue
    default:
      return "#9ca3af"; // gray
  }
}

export function GraphView({ data, isLoading }: GraphViewProps) {
  const [hoveredNode, setHoveredNode] = useState<number | null>(null);
  const [hoveredEdge, setHoveredEdge] = useState<number | null>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 500 });

  // Simple force-directed layout calculation
  const positionedNodes = useMemo<PositionedNode[]>(() => {
    if (!data || data.nodes.length === 0) return [];

    const nodes = data.nodes;
    const edges = data.edges;
    const width = dimensions.width;
    const height = dimensions.height;
    const padding = 60;

    // Initialize positions in a circle
    const positions: { x: number; y: number }[] = nodes.map((_, i) => {
      const angle = (2 * Math.PI * i) / nodes.length;
      const radius = Math.min(width, height) / 3;
      return {
        x: width / 2 + radius * Math.cos(angle),
        y: height / 2 + radius * Math.sin(angle),
      };
    });

    // Simple force simulation (run a few iterations)
    const nodeIdToIndex = new Map(nodes.map((n, i) => [n.id, i]));

    for (let iter = 0; iter < 50; iter++) {
      // Repulsion between all nodes
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = positions[j].x - positions[i].x;
          const dy = positions[j].y - positions[i].y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = 2000 / (dist * dist);
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;
          positions[i].x -= fx;
          positions[i].y -= fy;
          positions[j].x += fx;
          positions[j].y += fy;
        }
      }

      // Attraction along edges
      for (const edge of edges) {
        const sourceIdx = nodeIdToIndex.get(edge.source);
        const targetIdx = nodeIdToIndex.get(edge.target);
        if (sourceIdx === undefined || targetIdx === undefined) continue;

        const dx = positions[targetIdx].x - positions[sourceIdx].x;
        const dy = positions[targetIdx].y - positions[sourceIdx].y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = dist * 0.01;
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        positions[sourceIdx].x += fx;
        positions[sourceIdx].y += fy;
        positions[targetIdx].x -= fx;
        positions[targetIdx].y -= fy;
      }

      // Center gravity
      for (let i = 0; i < nodes.length; i++) {
        positions[i].x += (width / 2 - positions[i].x) * 0.01;
        positions[i].y += (height / 2 - positions[i].y) * 0.01;
      }
    }

    // Clamp to bounds
    for (let i = 0; i < nodes.length; i++) {
      positions[i].x = Math.max(padding, Math.min(width - padding, positions[i].x));
      positions[i].y = Math.max(padding, Math.min(height - padding, positions[i].y));
    }

    return nodes.map((node, i) => ({
      ...node,
      x: positions[i].x,
      y: positions[i].y,
    }));
  }, [data, dimensions]);

  const nodeMap = useMemo(
    () => new Map(positionedNodes.map((n) => [n.id, n])),
    [positionedNodes]
  );

  const highlightedEdges = useMemo(() => {
    if (hoveredNode === null || !data) return new Set<number>();
    return new Set(
      data.edges
        .filter((e) => e.source === hoveredNode || e.target === hoveredNode)
        .map((_, i) => i)
    );
  }, [hoveredNode, data]);

  if (isLoading) {
    return (
      <Card className="h-[500px] flex items-center justify-center">
        <div className="animate-pulse text-slate-500 dark:text-slate-400">
          Loading graph...
        </div>
      </Card>
    );
  }

  if (!data || data.nodes.length === 0) {
    return (
      <Card className="text-center py-8">
        <p className="text-slate-500 dark:text-slate-400">No graph data available</p>
      </Card>
    );
  }

  const hoveredNodeData = hoveredNode !== null ? nodeMap.get(hoveredNode) : null;
  const hoveredEdgeData = hoveredEdge !== null ? data.edges[hoveredEdge] : null;

  return (
    <Card padding="none" className="overflow-hidden">
      <div className="relative">
        <svg
          width="100%"
          height={dimensions.height}
          viewBox={`0 0 ${dimensions.width} ${dimensions.height}`}
          className="bg-slate-50 dark:bg-slate-900"
        >
          <defs>
            <marker
              id="arrowhead"
              markerWidth="10"
              markerHeight="7"
              refX="20"
              refY="3.5"
              orient="auto"
            >
              <polygon points="0 0, 10 3.5, 0 7" fill="#9ca3af" />
            </marker>
          </defs>

          {/* Edges */}
          {data.edges.map((edge, i) => {
            const source = nodeMap.get(edge.source);
            const target = nodeMap.get(edge.target);
            if (!source || !target) return null;

            const isHighlighted =
              hoveredEdge === i ||
              (hoveredNode !== null && highlightedEdges.has(i));
            const opacity = hoveredNode === null ? 0.6 : isHighlighted ? 1 : 0.15;

            return (
              <g key={`edge-${i}`}>
                <line
                  x1={source.x}
                  y1={source.y}
                  x2={target.x}
                  y2={target.y}
                  stroke={getEdgeColor(edge.type)}
                  strokeWidth={isHighlighted ? 2.5 : 1.5}
                  opacity={opacity}
                  markerEnd="url(#arrowhead)"
                  className="transition-all duration-150"
                  onMouseEnter={() => setHoveredEdge(i)}
                  onMouseLeave={() => setHoveredEdge(null)}
                  style={{ cursor: "pointer" }}
                />
              </g>
            );
          })}

          {/* Nodes */}
          {positionedNodes.map((node) => {
            const isHighlighted =
              hoveredNode === node.id ||
              (hoveredNode !== null &&
                data.edges.some(
                  (e) =>
                    (e.source === hoveredNode && e.target === node.id) ||
                    (e.target === hoveredNode && e.source === node.id)
                ));
            const opacity = hoveredNode === null ? 1 : isHighlighted ? 1 : 0.3;

            return (
              <g
                key={`node-${node.id}`}
                transform={`translate(${node.x}, ${node.y})`}
                onMouseEnter={() => setHoveredNode(node.id)}
                onMouseLeave={() => setHoveredNode(null)}
                style={{ cursor: "pointer" }}
                className="transition-opacity duration-150"
                opacity={opacity}
              >
                <circle
                  r={hoveredNode === node.id ? 14 : 10}
                  fill={getNodeColor(node.type)}
                  stroke="white"
                  strokeWidth={2}
                  className="transition-all duration-150"
                />
                <text
                  y={-16}
                  textAnchor="middle"
                  className="text-xs font-medium fill-slate-700 dark:fill-slate-300"
                  style={{ pointerEvents: "none" }}
                >
                  {node.name.length > 15 ? node.name.slice(0, 15) + "..." : node.name}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Tooltip */}
        {(hoveredNodeData || hoveredEdgeData) && (
          <div className="absolute bottom-4 left-4 bg-white dark:bg-slate-800 rounded-lg shadow-lg p-3 border border-slate-200 dark:border-slate-700 max-w-xs">
            {hoveredNodeData && (
              <div>
                <p className="font-medium text-slate-900 dark:text-white">
                  {hoveredNodeData.name}
                </p>
                {hoveredNodeData.type && (
                  <Tag variant="primary" size="sm" className="mt-1">
                    {hoveredNodeData.type}
                  </Tag>
                )}
              </div>
            )}
            {hoveredEdgeData && !hoveredNodeData && (
              <div>
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-slate-700 dark:text-slate-300">
                    {nodeMap.get(hoveredEdgeData.source)?.name}
                  </span>
                  <Tag variant="info" size="sm">
                    {formatRelationshipType(hoveredEdgeData.type)}
                  </Tag>
                  <span className="text-slate-700 dark:text-slate-300">
                    {nodeMap.get(hoveredEdgeData.target)?.name}
                  </span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Legend */}
        <div className="absolute top-4 right-4 bg-white/90 dark:bg-slate-800/90 rounded-lg p-3 border border-slate-200 dark:border-slate-700">
          <p className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-2">Legend</p>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-blue-500" />
              <span className="text-xs text-slate-600 dark:text-slate-300">Company</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-emerald-500" />
              <span className="text-xs text-slate-600 dark:text-slate-300">Person</span>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}
