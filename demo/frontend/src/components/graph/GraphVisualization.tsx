import { useEffect, useRef, useCallback, useState, useMemo } from 'react';
import Sigma from 'sigma';
import Graph from 'graphology';
import { EdgeArrowProgram, NodeCircleProgram } from 'sigma/rendering';
import forceAtlas2 from 'graphology-layout-forceatlas2';
import { useGraphStore } from '../../stores/graphStore';
import { useInsightStore } from '../../stores/insightStore';
import { useSessionStore } from '../../stores/sessionStore';
import type { GraphNode } from '../../types/graph';
import type { NodeType, EdgeType } from '../../types/atlas';
import NodeDiamondProgram from './programs/node-diamond';
import NodeSquareProgram from './programs/node-square';
import NodeTriangleProgram from './programs/node-triangle';

/**
 * Shape mapping by node type:
 *  - circle:   Event, UserProfile
 *  - triangle: Entity, Workflow
 *  - diamond:  Preference, Skill
 *  - square:   Summary, BehavioralPattern
 */
const NODE_TYPE_SHAPE: Record<NodeType, string> = {
  Event: 'circle',
  UserProfile: 'circle',
  Entity: 'triangle',
  Workflow: 'triangle',
  Preference: 'diamond',
  Skill: 'diamond',
  Summary: 'square',
  BehavioralPattern: 'square',
};

const DIRECTED_EDGE_TYPES = new Set<EdgeType>([
  'FOLLOWS', 'CAUSED_BY', 'REFERENCES', 'DERIVED_FROM',
  'SUMMARIZES', 'HAS_PROFILE', 'HAS_PREFERENCE', 'HAS_SKILL',
  'EXHIBITS_PATTERN', 'INTERESTED_IN', 'ABOUT', 'ABSTRACTED_FROM', 'PARENT_SKILL',
]);

interface TooltipData {
  x: number;
  y: number;
  label: string;
  nodeType: NodeType;
  eventType?: string;
  entityType?: string;
  decayScore: number;
  attributes: Record<string, unknown>;
}

function computeCircularPositions(graph: Graph) {
  const nodes = graph.nodes();
  const count = nodes.length;
  const radius = Math.max(100, count * 8);
  nodes.forEach((node, i) => {
    const angle = (2 * Math.PI * i) / count;
    graph.setNodeAttribute(node, 'x', radius * Math.cos(angle));
    graph.setNodeAttribute(node, 'y', radius * Math.sin(angle));
  });
}

export function GraphVisualization() {
  const containerRef = useRef<HTMLDivElement>(null);
  const rendererRef = useRef<Sigma | null>(null);
  const graphRef = useRef<Graph | null>(null);
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);

  const nodes = useGraphStore((s) => s.nodes);
  const edges = useGraphStore((s) => s.edges);
  const selectedNodeId = useGraphStore((s) => s.selectedNodeId);
  const visibleNodeTypes = useGraphStore((s) => s.visibleNodeTypes);
  const visibleEdgeTypes = useGraphStore((s) => s.visibleEdgeTypes);
  const sessionFilter = useGraphStore((s) => s.sessionFilter);
  const layoutType = useGraphStore((s) => s.layoutType);
  const selectNode = useGraphStore((s) => s.selectNode);

  const setInsightActiveTab = useInsightStore((s) => s.setActiveTab);
  const highlightedNodeIds = useSessionStore((s) => s.highlightedNodeIds);

  // O(1) node lookups instead of O(N) .find() in reducers
  const nodeMap = useMemo(() => {
    const map = new Map<string, GraphNode>();
    for (const node of nodes) {
      map.set(node.id, node);
    }
    return map;
  }, [nodes]);
  const nodeMapRef = useRef(nodeMap);
  nodeMapRef.current = nodeMap;

  const handleClickNode = useCallback(
    ({ node }: { node: string }) => {
      selectNode(node);
      setInsightActiveTab('scores');
    },
    [selectNode, setInsightActiveTab],
  );

  const handleClickStage = useCallback(() => {
    selectNode(null);
  }, [selectNode]);

  // Build graph + renderer
  useEffect(() => {
    if (!containerRef.current) return;

    const graph = new Graph({ multi: true, type: 'directed' });
    graphRef.current = graph;

    // Add nodes with shape based on node type
    for (const n of nodes) {
      graph.addNode(n.id, {
        x: n.x,
        y: n.y,
        size: n.size,
        color: n.color,
        label: n.label,
        type: NODE_TYPE_SHAPE[n.node_type] ?? 'circle',
        node_type: n.node_type,
        session_id: n.session_id ?? null,
        event_type: n.event_type ?? null,
        entity_type: (n.attributes.entity_type as string) ?? null,
        decay_score: n.decay_score,
        importance: n.importance,
      });
    }

    // Add edges
    for (const e of edges) {
      graph.addEdgeWithKey(e.id, e.source, e.target, {
        color: e.color,
        size: e.size,
        label: e.label ?? null,
        type: DIRECTED_EDGE_TYPES.has(e.edge_type) ? 'arrow' : 'line',
        edge_type: e.edge_type,
        forceLabel: false,
      });
    }

    // Apply ForceAtlas2 layout
    const inferredSettings = forceAtlas2.inferSettings(graph);
    forceAtlas2.assign(graph, {
      iterations: 100,
      settings: {
        ...inferredSettings,
        gravity: 1,
        scalingRatio: 10,
        barnesHutOptimize: true,
      },
    });

    const renderer = new Sigma(graph, containerRef.current, {
      renderEdgeLabels: true,
      defaultEdgeType: 'arrow',
      defaultNodeType: 'circle',
      nodeProgramClasses: {
        circle: NodeCircleProgram,
        diamond: NodeDiamondProgram,
        square: NodeSquareProgram,
        triangle: NodeTriangleProgram,
      },
      edgeProgramClasses: {
        arrow: EdgeArrowProgram,
      },
      labelColor: { color: '#9ca3af' },
      labelSize: 11,
      labelFont: 'Inter',
      edgeLabelFont: 'Inter',
      edgeLabelSize: 9,
      edgeLabelColor: { color: '#6b7280' },
      labelDensity: 0.5,
      labelRenderedSizeThreshold: 6,
      zIndex: true,
      defaultNodeColor: '#6b7280',
      defaultEdgeColor: '#374151',
      minEdgeThickness: 0.5,

      nodeReducer: (node, data) => {
        const res = { ...data };
        const graphState = useGraphStore.getState();
        const sessionState = useSessionStore.getState();

        // O(1) lookup via map ref
        const nodeData = nodeMapRef.current.get(node);

        // Hide nodes of hidden types
        if (nodeData && !graphState.visibleNodeTypes.has(nodeData.node_type)) {
          res.hidden = true;
          return res;
        }

        // Dim nodes not matching session filter
        if (graphState.sessionFilter) {
          if (nodeData?.session_id && nodeData.session_id !== graphState.sessionFilter) {
            res.color = '#1e1e24';
            res.label = '';
            res.zIndex = 0;
          }
        }

        // Highlight selected node
        if (node === graphState.selectedNodeId) {
          res.highlighted = true;
          res.zIndex = 10;
        }

        // Highlight provenance nodes from chat
        if (sessionState.highlightedNodeIds.includes(node)) {
          res.highlighted = true;
          res.color = '#f59e0b';
          res.zIndex = 9;
        }

        return res;
      },

      edgeReducer: (edge, data) => {
        const res = { ...data };
        const graphState = useGraphStore.getState();
        const edgeData = graphState.edges.find((e) => e.id === edge);

        // Hide edges of hidden types
        if (edgeData && !graphState.visibleEdgeTypes.has(edgeData.edge_type)) {
          res.hidden = true;
          return res;
        }

        // Hide edges connected to hidden nodes (O(1) via nodeMapRef)
        if (graphRef.current) {
          const source = graphRef.current.source(edge);
          const target = graphRef.current.target(edge);
          const sourceNode = nodeMapRef.current.get(source);
          const targetNode = nodeMapRef.current.get(target);

          if (sourceNode && !graphState.visibleNodeTypes.has(sourceNode.node_type)) {
            res.hidden = true;
            return res;
          }
          if (targetNode && !graphState.visibleNodeTypes.has(targetNode.node_type)) {
            res.hidden = true;
            return res;
          }

          // Dim edges not in current session filter
          if (graphState.sessionFilter) {
            const sourceInSession = !sourceNode?.session_id || sourceNode.session_id === graphState.sessionFilter;
            const targetInSession = !targetNode?.session_id || targetNode.session_id === graphState.sessionFilter;

            if (!sourceInSession || !targetInSession) {
              res.color = '#1a1a22';
              res.size = 0.5;
            }
          }
        }

        return res;
      },
    });

    rendererRef.current = renderer;

    // Event handlers
    renderer.on('clickNode', handleClickNode);
    renderer.on('clickStage', handleClickStage);

    renderer.on('enterNode', ({ node }) => {
      const nodePosition = renderer.getNodeDisplayData(node);
      const nodeData = nodeMapRef.current.get(node);
      if (nodePosition && nodeData) {
        const viewportCoords = renderer.graphToViewport({ x: nodePosition.x, y: nodePosition.y });
        setTooltip({
          x: viewportCoords.x,
          y: viewportCoords.y,
          label: nodeData.label,
          nodeType: nodeData.node_type,
          eventType: nodeData.event_type,
          entityType: nodeData.attributes.entity_type as string | undefined,
          decayScore: nodeData.decay_score,
          attributes: nodeData.attributes,
        });
      }
    });

    renderer.on('leaveNode', () => {
      setTooltip(null);
    });

    return () => {
      renderer.off('clickNode', handleClickNode);
      renderer.off('clickStage', handleClickStage);
      renderer.kill();
      rendererRef.current = null;
      graphRef.current = null;
    };
    // We only want to rebuild the graph when nodes/edges change, not on every state change
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes, edges]);

  // Refresh renderer when visual state changes (selection, filters, highlights)
  useEffect(() => {
    if (rendererRef.current) {
      rendererRef.current.refresh();
    }
  }, [selectedNodeId, visibleNodeTypes, visibleEdgeTypes, sessionFilter, highlightedNodeIds]);

  // Re-run layout when layoutType changes
  useEffect(() => {
    const graph = graphRef.current;
    const renderer = rendererRef.current;
    if (!graph || !renderer) return;

    if (layoutType === 'circular') {
      computeCircularPositions(graph);
    } else {
      const inferredSettings = forceAtlas2.inferSettings(graph);
      forceAtlas2.assign(graph, {
        iterations: 100,
        settings: {
          ...inferredSettings,
          gravity: 1,
          scalingRatio: 10,
          barnesHutOptimize: true,
        },
      });
    }

    renderer.refresh();
  }, [layoutType]);

  // Animate camera to session nodes when session filter changes
  useEffect(() => {
    const renderer = rendererRef.current;
    const graph = graphRef.current;
    if (!renderer || !graph || !sessionFilter) return;

    const sessionNodes = nodes.filter((n) => n.session_id === sessionFilter);
    if (sessionNodes.length === 0) return;

    // Compute bounding box of session nodes
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (const n of sessionNodes) {
      const displayData = renderer.getNodeDisplayData(n.id);
      if (displayData) {
        if (displayData.x < minX) minX = displayData.x;
        if (displayData.x > maxX) maxX = displayData.x;
        if (displayData.y < minY) minY = displayData.y;
        if (displayData.y > maxY) maxY = displayData.y;
      }
    }

    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;

    renderer.getCamera().animate(
      { x: centerX, y: centerY, ratio: 0.8 },
      { duration: 500 },
    );
  }, [sessionFilter, nodes]);

  const nodeTypeColor: Record<string, string> = {
    Event: '#3b82f6',
    Entity: '#14b8a6',
    Summary: '#4b5563',
    UserProfile: '#8b5cf6',
    Preference: '#22c55e',
    Skill: '#a855f7',
    Workflow: '#f59e0b',
    BehavioralPattern: '#f59e0b',
  };

  return (
    <div className="relative w-full h-full">
      <div
        ref={containerRef}
        className="w-full h-full"
        style={{ background: '#0a0a0c' }}
      />

      {/* Tooltip */}
      {tooltip && (
        <div
          className="absolute z-50 pointer-events-none bg-surface-card border border-muted-dark/50 rounded-lg px-3 py-2 shadow-xl max-w-[240px]"
          style={{
            left: tooltip.x + 12,
            top: tooltip.y - 10,
            transform: 'translateY(-100%)',
          }}
        >
          <div className="flex items-center gap-2 mb-1">
            <span
              className="inline-block w-2.5 h-2.5 rounded-full shrink-0"
              style={{ backgroundColor: nodeTypeColor[tooltip.nodeType] ?? '#6b7280' }}
            />
            <span className="text-[10px] font-mono uppercase tracking-wider text-muted-light">
              {tooltip.nodeType}
            </span>
          </div>
          <p className="text-sm text-gray-100 font-medium truncate">{tooltip.label}</p>
          {tooltip.eventType && (
            <p className="text-xs text-muted-light mt-0.5 font-mono">{tooltip.eventType}</p>
          )}
          {tooltip.entityType && (
            <p className="text-xs text-muted-light mt-0.5 font-mono">{tooltip.entityType}</p>
          )}
          <div className="mt-1.5 flex items-center gap-2">
            <span className="text-[10px] text-muted">Decay</span>
            <div className="flex-1 h-1 bg-muted-dark rounded-full overflow-hidden">
              <div
                className="h-full rounded-full"
                style={{
                  width: `${tooltip.decayScore * 100}%`,
                  backgroundColor:
                    tooltip.decayScore > 0.7 ? '#22c55e' : tooltip.decayScore > 0.4 ? '#f59e0b' : '#ef4444',
                }}
              />
            </div>
            <span className="text-[10px] text-muted-light tabular-nums">
              {tooltip.decayScore.toFixed(2)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
