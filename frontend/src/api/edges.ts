import { queryOptions } from '@tanstack/react-query'
import type { EdgeCreateRequest, EdgeOut, EdgeUpdateRequest } from './generated'
import { createEdge, deleteEdge, listEdges, updateEdge } from './generated'

export function edgesQueryOptions(caseId: string) {
  return queryOptions({
    queryKey: ['cases', caseId, 'edges'] as const,
    queryFn: async (): Promise<EdgeOut[]> => {
      const { data, error } = await listEdges({ path: { case_id: caseId } })
      if (error) throw error
      return data
    },
  })
}

export async function createEdgeRequest(caseId: string, body: EdgeCreateRequest): Promise<EdgeOut> {
  const { data, error } = await createEdge({ path: { case_id: caseId }, body })
  if (error) throw error
  return data
}

export async function updateEdgeRequest(
  caseId: string,
  edgeId: string,
  body: EdgeUpdateRequest,
): Promise<EdgeOut> {
  const { data, error } = await updateEdge({ path: { case_id: caseId, edge_id: edgeId }, body })
  if (error) throw error
  return data
}

export async function deleteEdgeRequest(caseId: string, edgeId: string): Promise<void> {
  const { error } = await deleteEdge({ path: { case_id: caseId, edge_id: edgeId } })
  if (error) throw error
}
