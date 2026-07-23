import { queryOptions } from '@tanstack/react-query'
import type { EntityTypeOut } from './generated'
import { listEntityTypes } from './generated'

export const entityTypesQueryOptions = queryOptions({
  queryKey: ['entity-types'] as const,
  queryFn: async (): Promise<EntityTypeOut[]> => {
    const { data, error } = await listEntityTypes()
    if (error) throw error
    return data
  },
  staleTime: Number.POSITIVE_INFINITY,
})
