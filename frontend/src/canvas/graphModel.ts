import type { Edge, Node } from '@xyflow/react'
import type { EdgeOut, EntityTypeOut, NodeOut } from '../api/generated'

/** Our renderer-facing graph model (ADR-005): app code builds/reads this shape,
 * not `@xyflow/react`'s `Node`/`Edge` types directly, so the underlying canvas
 * library can be swapped later without touching callers. */
export interface EntityNodeData extends Record<string, unknown> {
  node: NodeOut
  entityType: EntityTypeOut | undefined
}

export interface RelationshipEdgeData extends Record<string, unknown> {
  edge: EdgeOut
}

export type EntityNode = Node<EntityNodeData, 'entity'>
export type RelationshipEdge = Edge<RelationshipEdgeData>

export function toFlowNodes(
  nodes: NodeOut[],
  entityTypesById: Map<string, EntityTypeOut>,
  selectedNodeIds: ReadonlySet<string>,
): EntityNode[] {
  return nodes.map((node) => ({
    id: node.id,
    type: 'entity',
    position: { x: node.position_x, y: node.position_y },
    selected: selectedNodeIds.has(node.id),
    data: { node, entityType: entityTypesById.get(node.entity_type_id) },
  }))
}

export function toFlowEdges(
  edges: EdgeOut[],
  selectedEdgeIds: ReadonlySet<string>,
): RelationshipEdge[] {
  return edges.map((edge) => ({
    id: edge.id,
    source: edge.src_node_id,
    target: edge.dst_node_id,
    label: edge.label ?? edge.relationship,
    selected: selectedEdgeIds.has(edge.id),
    data: { edge },
  }))
}

export function entityTypesById(entityTypes: EntityTypeOut[]): Map<string, EntityTypeOut> {
  return new Map(entityTypes.map((entityType) => [entityType.id, entityType]))
}
