import type { ButtonHTMLAttributes } from 'react'
import styles from './Button.module.css'

type Variant = 'default' | 'primary' | 'danger' | 'ghost'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
}

const variantClass: Record<Variant, string> = {
  default: '',
  primary: styles.primary,
  danger: styles.danger,
  ghost: styles.ghost,
}

export function Button({ variant = 'default', className, ...props }: ButtonProps) {
  const classes = [styles.button, variantClass[variant], className].filter(Boolean).join(' ')
  return <button type="button" className={classes} {...props} />
}
