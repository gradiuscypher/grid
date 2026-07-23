import {
  applyEdgeChanges,
  applyNodeChanges,
  Background,
  type Connection,
  ConnectionMode,
  Controls,
  type EdgeChange,
  type NodeChange,
  type OnSelectionChangeFunc,
  ReactFlow,
  ReactFlowProvider,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { EdgeOut, EntityTypeOut, NodeOut } from '../api/generated'
import { debounce } from './debounce'
import { EntityNode } from './EntityNode'
import styles from './GraphCanvas.module.css'
import {
  type EntityNode as EntityNodeType,
  entityTypesById,
  type RelationshipEdge,
  toFlowEdges,
  toFlowNodes,
} from './graphModel'

const nodeTypes = { entity: EntityNode }

const POSITION_DEBOUNCE_MS = 300

interface GraphCanvasProps {
  nodes: NodeOut[]
  edges: EdgeOut[]
  entityTypes: EntityTypeOut[]
  selectedNodeIds: ReadonlySet<string>
  selectedEdgeIds: ReadonlySet<string>
  onSelectionChange: (nodeIds: string[], edgeIds: string[]) => void
  onConnectNodes: (sourceId: string, targetId: string) => void
  onMoveNode: (nodeId: string, x: number, y: number) => void
  onDeleteNodes: (nodeIds: string[]) => void
  onDeleteEdges: (edgeIds: string[]) => void
}

function GraphCanvasInner(props: GraphCanvasProps) {
  const {
    nodes,
    edges,
    entityTypes,
    selectedNodeIds,
    selectedEdgeIds,
    onSelectionChange,
    onConnectNodes,
    onMoveNode,
    onDeleteNodes,
    onDeleteEdges,
  } = props

  const entityTypesMap = useMemo(() => entityTypesById(entityTypes), [entityTypes])
  const draggingIdsRef = useRef<Set<string>>(new Set())

  const [flowNodes, setFlowNodes] = useState<EntityNodeType[]>(() =>
    toFlowNodes(nodes, entityTypesMap, selectedNodeIds),
  )
  const [flowEdges, setFlowEdges] = useState<RelationshipEdge[]>(() =>
    toFlowEdges(edges, selectedEdgeIds),
  )

  // Server state (Query cache, patched by our own mutations and by live WS
  // events) is the source of truth. Positions of nodes mid-drag are the one
  // exception: a resync here would otherwise snap a node back to its last
  // persisted position on every unrelated cache update.
  useEffect(() => {
    setFlowNodes((current) => {
      const currentById = new Map(current.map((node) => [node.id, node]))
      return toFlowNodes(nodes, entityTypesMap, selectedNodeIds).map((node) => {
        if (draggingIdsRef.current.has(node.id)) {
          const inFlight = currentById.get(node.id)
          if (inFlight) return { ...node, position: inFlight.position }
        }
        return node
      })
    })
  }, [nodes, entityTypesMap, selectedNodeIds])

  useEffect(() => {
    setFlowEdges(toFlowEdges(edges, selectedEdgeIds))
  }, [edges, selectedEdgeIds])

  const debouncedMoveRef = useRef(
    new Map<string, ReturnType<typeof debounce<[string, number, number]>>>(),
  )
  const moveNodeFor = useCallback(
    (nodeId: string) => {
      let fn = debouncedMoveRef.current.get(nodeId)
      if (!fn) {
        fn = debounce(onMoveNode, POSITION_DEBOUNCE_MS)
        debouncedMoveRef.current.set(nodeId, fn)
      }
      return fn
    },
    [onMoveNode],
  )

  const handleNodesChange = useCallback((changes: NodeChange<EntityNodeType>[]) => {
    setFlowNodes((current) => applyNodeChanges(changes, current))
  }, [])

  const handleEdgesChange = useCallback((changes: EdgeChange<RelationshipEdge>[]) => {
    setFlowEdges((current) => applyEdgeChanges(changes, current))
  }, [])

  const handleNodeDragStart = useCallback((_event: unknown, node: { id: string }) => {
    draggingIdsRef.current.add(node.id)
  }, [])

  const handleNodeDrag = useCallback(
    (_event: unknown, node: { id: string; position: { x: number; y: number } }) => {
      moveNodeFor(node.id)(node.id, node.position.x, node.position.y)
    },
    [moveNodeFor],
  )

  const handleNodeDragStop = useCallback(
    (_event: unknown, node: { id: string; position: { x: number; y: number } }) => {
      debouncedMoveRef.current.get(node.id)?.cancel()
      onMoveNode(node.id, node.position.x, node.position.y)
      draggingIdsRef.current.delete(node.id)
    },
    [onMoveNode],
  )

  const handleConnect = useCallback(
    (connection: Connection) => {
      if (!connection.source || !connection.target) return
      onConnectNodes(connection.source, connection.target)
    },
    [onConnectNodes],
  )

  const handleSelectionChange: OnSelectionChangeFunc = useCallback(
    ({ nodes: selected, edges: selectedEdges }) => {
      onSelectionChange(
        selected.map((node) => node.id),
        selectedEdges.map((edge) => edge.id),
      )
    },
    [onSelectionChange],
  )

  const handleNodesDelete = useCallback(
    (deleted: { id: string }[]) => onDeleteNodes(deleted.map((node) => node.id)),
    [onDeleteNodes],
  )

  const handleEdgesDelete = useCallback(
    (deleted: { id: string }[]) => onDeleteEdges(deleted.map((edge) => edge.id)),
    [onDeleteEdges],
  )

  return (
    <div className={styles.canvas}>
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        nodeTypes={nodeTypes}
        connectionMode={ConnectionMode.Loose}
        deleteKeyCode={['Backspace', 'Delete']}
        onNodesChange={handleNodesChange}
        onEdgesChange={handleEdgesChange}
        onNodeDragStart={handleNodeDragStart}
        onNodeDrag={handleNodeDrag}
        onNodeDragStop={handleNodeDragStop}
        onConnect={handleConnect}
        onSelectionChange={handleSelectionChange}
        onNodesDelete={handleNodesDelete}
        onEdgesDelete={handleEdgesDelete}
        proOptions={{ hideAttribution: true }}
        fitView
      >
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  )
}

export function GraphCanvas(props: GraphCanvasProps) {
  return (
    <ReactFlowProvider>
      <GraphCanvasInner {...props} />
    </ReactFlowProvider>
  )
}
