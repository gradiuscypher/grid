import { queryOptions } from '@tanstack/react-query'
import type { LoginRequest, RegisterRequest, UserOut } from './generated'
import { getMe, login, logout, register } from './generated'

export const meQueryOptions = queryOptions({
  queryKey: ['auth', 'me'] as const,
  queryFn: async (): Promise<UserOut | null> => {
    const { data, error, response } = await getMe()
    if (response?.status === 401) return null
    if (error) throw error
    return data ?? null
  },
  retry: false,
})

export async function loginRequest(body: LoginRequest): Promise<UserOut> {
  const { data, error } = await login({ body })
  if (error) throw error
  return data
}

export async function registerRequest(body: RegisterRequest): Promise<UserOut> {
  const { data, error } = await register({ body })
  if (error) throw error
  return data
}

export async function logoutRequest(): Promise<void> {
  const { error } = await logout()
  if (error) throw error
}
