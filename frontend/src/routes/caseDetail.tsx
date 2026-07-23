import { useQuery } from '@tanstack/react-query'
import { createRoute, Link } from '@tanstack/react-router'
import { caseQueryOptions } from '../api/cases'
import { apiErrorMessage } from '../api/errors'
import { authedLayoutRoute } from './authed'
import styles from './CaseDetailPage.module.css'

export const caseDetailRoute = createRoute({
  getParentRoute: () => authedLayoutRoute,
  path: '/cases/$caseId',
  loader: ({ context, params }) =>
    context.queryClient.ensureQueryData(caseQueryOptions(params.caseId)),
  component: CaseDetailPage,
})

function CaseDetailPage() {
  const { caseId } = caseDetailRoute.useParams()
  const caseQuery = useQuery(caseQueryOptions(caseId))

  return (
    <div className={styles.wrap}>
      <Link to="/" className={styles.back}>
        ← Cases
      </Link>
      {caseQuery.isLoading && <p>Loading case…</p>}
      {caseQuery.isError && (
        <p role="alert">{apiErrorMessage(caseQuery.error, 'Failed to load case')}</p>
      )}
      {caseQuery.data && (
        <>
          <h1 className={styles.title}>{caseQuery.data.name}</h1>
          {caseQuery.data.description && (
            <p className={styles.description}>{caseQuery.data.description}</p>
          )}
          <div className={styles.placeholder}>Canvas arrives in Phase 2b.</div>
        </>
      )}
    </div>
  )
}
