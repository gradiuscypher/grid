import { describe, expect, it } from 'vitest'
import type { EdgeOut, EntityTypeOut, NodeOut } from '../api/generated'
import { entityTypesById, toFlowEdges, toFlowNodes } from './graphModel'

const domainType: EntityTypeOut = {
  id: 'et-domain',
  name: 'domain',
  display_name: 'Domain',
  is_builtin: true,
  json_schema: { type: 'object' },
  icon: 'globe',
  color: '#4f8cff',
}

function makeNode(overrides: Partial<NodeOut> = {}): NodeOut {
  return {
    id: 'node-1',
    case_id: 'case-1',
    entity_type_id: 'et-domain',
    value: 'example.com',
    canonical_value: 'example.com',
    properties: {},
    position_x: 10,
    position_y: 20,
    confidence: 1,
    created_via: 'user',
    created_by_user_id: 'user-1',
    ...overrides,
  }
}

function makeEdge(overrides: Partial<EdgeOut> = {}): EdgeOut {
  return {
    id: 'edge-1',
    case_id: 'case-1',
    src_node_id: 'node-1',
    dst_node_id: 'node-2',
    relationship: 'resolves_to',
    label: null,
    properties: {},
    created_via: 'user',
    created_by_user_id: 'user-1',
    ...overrides,
  }
}

describe('entityTypesById', () => {
  it('indexes entity types by id', () => {
    const map = entityTypesById([domainType])
    expect(map.get('et-domain')).toBe(domainType)
    expect(map.size).toBe(1)
  })
})

describe('toFlowNodes', () => {
  it('maps position, entity type lookup, and selection state', () => {
    const node = makeNode()
    const map = entityTypesById([domainType])
    const [flowNode] = toFlowNodes([node], map, new Set(['node-1']))

    expect(flowNode.id).toBe('node-1')
    expect(flowNode.type).toBe('entity')
    expect(flowNode.position).toEqual({ x: 10, y: 20 })
    expect(flowNode.selected).toBe(true)
    expect(flowNode.data.node).toBe(node)
    expect(flowNode.data.entityType).toBe(domainType)
  })

  it('leaves entityType undefined for an unknown entity_type_id', () => {
    const node = makeNode({ entity_type_id: 'missing' })
    const [flowNode] = toFlowNodes([node], entityTypesById([domainType]), new Set())
    expect(flowNode.data.entityType).toBeUndefined()
    expect(flowNode.selected).toBe(false)
  })
})

describe('toFlowEdges', () => {
  it('maps source/target and falls back label to relationship', () => {
    const edge = makeEdge()
    const [flowEdge] = toFlowEdges([edge], new Set())
    expect(flowEdge.source).toBe('node-1')
    expect(flowEdge.target).toBe('node-2')
    expect(flowEdge.label).toBe('resolves_to')
    expect(flowEdge.selected).toBe(false)
  })

  it('prefers an explicit label over the relationship', () => {
    const edge = makeEdge({ label: 'known DNS record' })
    const [flowEdge] = toFlowEdges([edge], new Set(['edge-1']))
    expect(flowEdge.label).toBe('known DNS record')
    expect(flowEdge.selected).toBe(true)
  })
})
