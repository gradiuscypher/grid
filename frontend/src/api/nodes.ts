import { queryOptions } from '@tanstack/react-query'
import type { NodeCreateRequest, NodeOut, NodeUpdateRequest } from './generated'
import { createNode, deleteNode, listNodes, updateNode } from './generated'

export function nodesQueryOptions(caseId: string) {
  return queryOptions({
    queryKey: ['cases', caseId, 'nodes'] as const,
    queryFn: async (): Promise<NodeOut[]> => {
      const { data, error } = await listNodes({ path: { case_id: caseId } })
      if (error) throw error
      return data
    },
  })
}

export async function createNodeRequest(caseId: string, body: NodeCreateRequest): Promise<NodeOut> {
  const { data, error } = await createNode({ path: { case_id: caseId }, body })
  if (error) throw error
  return data
}

export async function updateNodeRequest(
  caseId: string,
  nodeId: string,
  body: NodeUpdateRequest,
): Promise<NodeOut> {
  const { data, error } = await updateNode({ path: { case_id: caseId, node_id: nodeId }, body })
  if (error) throw error
  return data
}

export async function deleteNodeRequest(caseId: string, nodeId: string): Promise<void> {
  const { error } = await deleteNode({ path: { case_id: caseId, node_id: nodeId } })
  if (error) throw error
}
