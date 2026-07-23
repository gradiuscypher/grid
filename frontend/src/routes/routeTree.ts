import { authedLayoutRoute } from './authed'
import { caseDetailRoute } from './caseDetail'
import { casesIndexRoute } from './casesIndex'
import { loginRoute } from './login'
import { registerRoute } from './register'
import { rootRoute } from './root'

export const routeTree = rootRoute.addChildren([
  loginRoute,
  registerRoute,
  authedLayoutRoute.addChildren([casesIndexRoute, caseDetailRoute]),
])
