import { queryOptions } from '@tanstack/react-query'
import type { CaseCreateRequest, CaseOut } from './generated'
import { createCase, getCase, listCases } from './generated'

export const casesQueryOptions = queryOptions({
  queryKey: ['cases'] as const,
  queryFn: async (): Promise<CaseOut[]> => {
    const { data, error } = await listCases()
    if (error) throw error
    return data
  },
})

export function caseQueryOptions(caseId: string) {
  return queryOptions({
    queryKey: ['cases', caseId] as const,
    queryFn: async (): Promise<CaseOut> => {
      const { data, error } = await getCase({ path: { case_id: caseId } })
      if (error) throw error
      return data
    },
  })
}

export async function createCaseRequest(body: CaseCreateRequest): Promise<CaseOut> {
  const { data, error } = await createCase({ body })
  if (error) throw error
  return data
}
