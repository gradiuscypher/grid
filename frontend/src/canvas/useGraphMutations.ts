import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  createEdgeRequest,
  deleteEdgeRequest,
  edgesQueryOptions,
  updateEdgeRequest,
} from '../api/edges'
import type {
  EdgeCreateRequest,
  EdgeOut,
  EdgeUpdateRequest,
  NodeCreateRequest,
  NodeOut,
  NodeUpdateRequest,
} from '../api/generated'
import {
  createNodeRequest,
  deleteNodeRequest,
  nodesQueryOptions,
  updateNodeRequest,
} from '../api/nodes'
import { removeByIds, upsertById } from '../api/queryCache'

/** Node/edge CRUD wired to the case's Query cache. Every mutation patches the
 * cache directly from its response instead of waiting on the WS round trip
 * (events/applyCaseEvent.ts skips re-processing self-originated create/update
 * events for exactly this reason — this is the side that already did the
 * patch). Deletes patch immediately too, rather than waiting for the
 * node.deleted event's cascaded_edge_ids, so the canvas doesn't lag the
 * user's own action. */
export function useGraphMutations(caseId: string) {
  const queryClient = useQueryClient()
  const nodesKey = nodesQueryOptions(caseId).queryKey
  const edgesKey = edgesQueryOptions(caseId).queryKey

  const createNode = useMutation({
    mutationFn: (body: NodeCreateRequest) => createNodeRequest(caseId, body),
    onSuccess: (node) => {
      queryClient.setQueryData<NodeOut[]>(nodesKey, (current) =>
        current ? upsertById(current, node) : current,
      )
    },
  })

  const updateNode = useMutation({
    mutationFn: ({ nodeId, body }: { nodeId: string; body: NodeUpdateRequest }) =>
      updateNodeRequest(caseId, nodeId, body),
    onSuccess: (node) => {
      queryClient.setQueryData<NodeOut[]>(nodesKey, (current) =>
        current ? upsertById(current, node) : current,
      )
    },
  })

  const deleteNode = useMutation({
    mutationFn: (nodeId: string) => deleteNodeRequest(caseId, nodeId),
    onSuccess: (_void, nodeId) => {
      queryClient.setQueryData<NodeOut[]>(nodesKey, (current) =>
        current ? removeByIds(current, new Set([nodeId])) : current,
      )
      queryClient.setQueryData<EdgeOut[]>(edgesKey, (current) =>
        current
          ? current.filter((edge) => edge.src_node_id !== nodeId && edge.dst_node_id !== nodeId)
          : current,
      )
    },
  })

  const createEdge = useMutation({
    mutationFn: (body: EdgeCreateRequest) => createEdgeRequest(caseId, body),
    onSuccess: (edge) => {
      queryClient.setQueryData<EdgeOut[]>(edgesKey, (current) =>
        current ? upsertById(current, edge) : current,
      )
    },
  })

  const updateEdge = useMutation({
    mutationFn: ({ edgeId, body }: { edgeId: string; body: EdgeUpdateRequest }) =>
      updateEdgeRequest(caseId, edgeId, body),
    onSuccess: (edge) => {
      queryClient.setQueryData<EdgeOut[]>(edgesKey, (current) =>
        current ? upsertById(current, edge) : current,
      )
    },
  })

  const deleteEdge = useMutation({
    mutationFn: (edgeId: string) => deleteEdgeRequest(caseId, edgeId),
    onSuccess: (_void, edgeId) => {
      queryClient.setQueryData<EdgeOut[]>(edgesKey, (current) =>
        current ? removeByIds(current, new Set([edgeId])) : current,
      )
    },
  })

  return { createNode, updateNode, deleteNode, createEdge, updateEdge, deleteEdge }
}
