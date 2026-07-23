import { describe, expect, it } from 'vitest'
import { apiErrorMessage } from './errors'

describe('apiErrorMessage', () => {
  it('extracts a string detail', () => {
    expect(apiErrorMessage({ detail: 'not authenticated' })).toBe('not authenticated')
  })

  it('joins pydantic validation error messages', () => {
    const error = {
      detail: [
        { loc: ['body', 'email'], msg: 'field required', type: 'missing' },
        { loc: ['body', 'password'], msg: 'too short', type: 'value_error' },
      ],
    }
    expect(apiErrorMessage(error)).toBe('field required; too short')
  })

  it('falls back for an Error instance', () => {
    expect(apiErrorMessage(new Error('network down'))).toBe('network down')
  })

  it('falls back to the default message for unrecognized shapes', () => {
    expect(apiErrorMessage('boom', 'default message')).toBe('default message')
    expect(apiErrorMessage(null, 'default message')).toBe('default message')
  })
})
