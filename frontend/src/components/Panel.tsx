import type { HTMLAttributes } from 'react'
import styles from './Panel.module.css'

export function Panel({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  const classes = [styles.panel, className].filter(Boolean).join(' ')
  return <div className={classes} {...props} />
}
