import type { QueryClient } from '@tanstack/react-query'
import { edgesQueryOptions } from '../api/edges'
import type { EdgeOut, NodeOut } from '../api/generated'
import { getEdge, getNode } from '../api/generated'
import { nodesQueryOptions } from '../api/nodes'
import { removeByIds, upsertById } from '../api/queryCache'
import type { CaseEvent } from './types'

/** Patches the TanStack Query cache from one live/replayed case event. Event
 * payloads are intentionally thin (ids only — see `events/service.py`), so
 * create/update events re-fetch the affected row; delete events already carry
 * everything needed to remove it. Skips events this client caused itself: our
 * own mutations already patch the cache from the mutation response, so
 * re-fetching would just be a redundant round trip. */
export async function applyCaseEvent(
  queryClient: QueryClient,
  caseId: string,
  event: CaseEvent,
  currentUserId: string | undefined,
): Promise<void> {
  const isSelf = currentUserId !== undefined && event.actor_user_id === currentUserId
  const nodesKey = nodesQueryOptions(caseId).queryKey
  const edgesKey = edgesQueryOptions(caseId).queryKey

  switch (event.type) {
    case 'node.created':
    case 'node.updated': {
      if (isSelf) return
      const nodeId = String(event.payload.node_id)
      const { data } = await getNode({ path: { case_id: caseId, node_id: nodeId } })
      if (!data) return
      queryClient.setQueryData<NodeOut[]>(nodesKey, (current) =>
        current ? upsertById(current, data) : current,
      )
      return
    }
    case 'node.deleted': {
      const nodeId = String(event.payload.node_id)
      const cascadedEdgeIds = new Set(
        Array.isArray(event.payload.cascaded_edge_ids)
          ? event.payload.cascaded_edge_ids.map(String)
          : [],
      )
      queryClient.setQueryData<NodeOut[]>(nodesKey, (current) =>
        current ? removeByIds(current, new Set([nodeId])) : current,
      )
      if (cascadedEdgeIds.size > 0) {
        queryClient.setQueryData<EdgeOut[]>(edgesKey, (current) =>
          current ? removeByIds(current, cascadedEdgeIds) : current,
        )
      }
      return
    }
    case 'edge.created':
    case 'edge.updated': {
      if (isSelf) return
      const edgeId = String(event.payload.edge_id)
      const { data } = await getEdge({ path: { case_id: caseId, edge_id: edgeId } })
      if (!data) return
      queryClient.setQueryData<EdgeOut[]>(edgesKey, (current) =>
        current ? upsertById(current, data) : current,
      )
      return
    }
    case 'edge.deleted': {
      const edgeId = String(event.payload.edge_id)
      queryClient.setQueryData<EdgeOut[]>(edgesKey, (current) =>
        current ? removeByIds(current, new Set([edgeId])) : current,
      )
      return
    }
    case 'note.created': {
      if (isSelf) return
      const targetType = event.payload.target_type
      const targetId = event.payload.target_id
      if (typeof targetType === 'string' && typeof targetId === 'string') {
        await queryClient.invalidateQueries({
          queryKey: ['cases', caseId, 'notes', targetType, targetId],
        })
      }
      return
    }
    case 'note.updated':
    case 'note.deleted': {
      if (isSelf) return
      // Thin payload has no target scope — invalidate every open notes query
      // for this case rather than guessing which target it belonged to.
      await queryClient.invalidateQueries({
        predicate: (query) =>
          query.queryKey[0] === 'cases' &&
          query.queryKey[1] === caseId &&
          query.queryKey[2] === 'notes',
      })
      return
    }
    default:
      return
  }
}
