function isValidationDetail(detail: unknown): detail is Array<{ msg?: unknown }> {
  return Array.isArray(detail)
}

/** Normalizes a FastAPI error body (`{"detail": ...}`) into a display string. */
export function apiErrorMessage(error: unknown, fallback = 'Something went wrong'): string {
  if (error && typeof error === 'object' && 'detail' in error) {
    const detail = (error as { detail: unknown }).detail

    if (typeof detail === 'string') return detail

    if (isValidationDetail(detail)) {
      const messages = detail
        .map((item) => (typeof item.msg === 'string' ? item.msg : null))
        .filter((msg): msg is string => msg !== null)
      if (messages.length > 0) return messages.join('; ')
    }
  }

  if (error instanceof Error) return error.message

  return fallback
}
