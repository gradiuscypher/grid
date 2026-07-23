import type { ErrorComponentProps } from '@tanstack/react-router'
import { apiErrorMessage } from '../api/errors'
import { Button } from './Button'
import { Panel } from './Panel'
import styles from './RouteError.module.css'

export function RouteError({ error, reset }: ErrorComponentProps) {
  return (
    <div className={styles.wrap}>
      <Panel>
        <p className={styles.message} role="alert">
          {apiErrorMessage(error, 'Something went wrong loading this page.')}
        </p>
        <Button onClick={reset}>Retry</Button>
      </Panel>
    </div>
  )
}
