import { QueryClient } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { edgesQueryOptions } from '../api/edges'
import type { EdgeOut, NodeOut } from '../api/generated'
import { nodesQueryOptions } from '../api/nodes'
import { applyCaseEvent } from './applyCaseEvent'
import { markSelfMutated } from './selfMutationTracker'
import type { CaseEvent } from './types'

const mockGetNode = vi.fn()
const mockGetEdge = vi.fn()

vi.mock('../api/generated', () => ({
  getNode: (...args: unknown[]) => mockGetNode(...args),
  getEdge: (...args: unknown[]) => mockGetEdge(...args),
}))

const CASE_ID = 'case-1'

function baseEvent(overrides: Partial<CaseEvent>): CaseEvent {
  return {
    seq: 1,
    case_id: CASE_ID,
    type: 'node.created',
    actor_type: 'user',
    actor_user_id: 'user-1',
    payload: {},
    created_at: new Date().toISOString(),
    ...overrides,
  }
}

function makeNode(overrides: Partial<NodeOut> = {}): NodeOut {
  return {
    id: 'node-1',
    case_id: CASE_ID,
    entity_type_id: 'et-1',
    value: 'example.com',
    canonical_value: 'example.com',
    properties: {},
    position_x: 0,
    position_y: 0,
    confidence: 1,
    created_via: 'user',
    created_by_user_id: 'user-1',
    ...overrides,
  }
}

function makeEdge(overrides: Partial<EdgeOut> = {}): EdgeOut {
  return {
    id: 'edge-1',
    case_id: CASE_ID,
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

describe('applyCaseEvent', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient()
    mockGetNode.mockReset()
    mockGetEdge.mockReset()
  })

  it('node.created fetches the node and appends it to the cached list', async () => {
    queryClient.setQueryData(nodesQueryOptions(CASE_ID).queryKey, [])
    const node = makeNode({ id: 'node-new' })
    mockGetNode.mockResolvedValue({ data: node })

    await applyCaseEvent(
      queryClient,
      CASE_ID,
      baseEvent({ type: 'node.created', payload: { node_id: 'node-new' } }),
    )

    expect(mockGetNode).toHaveBeenCalledWith({
      path: { case_id: CASE_ID, node_id: 'node-new' },
    })
    expect(queryClient.getQueryData(nodesQueryOptions(CASE_ID).queryKey)).toEqual([node])
  })

  it('node.updated replaces the existing entry by id', async () => {
    const original = makeNode({ id: 'node-1', value: 'old.example.com' })
    queryClient.setQueryData(nodesQueryOptions(CASE_ID).queryKey, [original])
    const updated = makeNode({ id: 'node-1', value: 'new.example.com' })
    mockGetNode.mockResolvedValue({ data: updated })

    await applyCaseEvent(
      queryClient,
      CASE_ID,
      baseEvent({ type: 'node.updated', payload: { node_id: 'node-1' } }),
    )

    expect(queryClient.getQueryData(nodesQueryOptions(CASE_ID).queryKey)).toEqual([updated])
  })

  it('node.deleted removes the node and any cascaded edges without a re-fetch', async () => {
    queryClient.setQueryData(nodesQueryOptions(CASE_ID).queryKey, [
      makeNode({ id: 'node-1' }),
      makeNode({ id: 'node-2' }),
    ])
    queryClient.setQueryData(edgesQueryOptions(CASE_ID).queryKey, [
      makeEdge({ id: 'edge-1' }),
      makeEdge({ id: 'edge-2' }),
    ])

    await applyCaseEvent(
      queryClient,
      CASE_ID,
      baseEvent({
        type: 'node.deleted',
        payload: { node_id: 'node-1', cascaded_edge_ids: ['edge-1'] },
      }),
    )

    expect(queryClient.getQueryData(nodesQueryOptions(CASE_ID).queryKey)).toEqual([
      makeNode({ id: 'node-2' }),
    ])
    expect(queryClient.getQueryData(edgesQueryOptions(CASE_ID).queryKey)).toEqual([
      makeEdge({ id: 'edge-2' }),
    ])
    expect(mockGetNode).not.toHaveBeenCalled()
  })

  it('edge.deleted removes just that edge', async () => {
    queryClient.setQueryData(edgesQueryOptions(CASE_ID).queryKey, [
      makeEdge({ id: 'edge-1' }),
      makeEdge({ id: 'edge-2' }),
    ])

    await applyCaseEvent(
      queryClient,
      CASE_ID,
      baseEvent({ type: 'edge.deleted', payload: { edge_id: 'edge-1' } }),
    )

    expect(queryClient.getQueryData(edgesQueryOptions(CASE_ID).queryKey)).toEqual([
      makeEdge({ id: 'edge-2' }),
    ])
  })

  it('skips the re-fetch for a node this tab already mutated itself', async () => {
    markSelfMutated('node-self')
    queryClient.setQueryData(nodesQueryOptions(CASE_ID).queryKey, [])

    await applyCaseEvent(
      queryClient,
      CASE_ID,
      baseEvent({ type: 'node.created', payload: { node_id: 'node-self' } }),
    )

    expect(mockGetNode).not.toHaveBeenCalled()
    expect(queryClient.getQueryData(nodesQueryOptions(CASE_ID).queryKey)).toEqual([])
  })

  it('ignores unknown event types', async () => {
    await expect(
      applyCaseEvent(queryClient, CASE_ID, baseEvent({ type: 'group.created', payload: {} })),
    ).resolves.toBeUndefined()
  })
})
