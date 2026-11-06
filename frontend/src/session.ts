import { ref } from 'vue'
import { csrfToken } from './api'
import { i18n } from './i18n'

export interface SessionUser {
  id: number
  display: string
  email: string
}

export interface AuthError {
  message: string
  code: string
  param?: string
}

export interface AuthOutcome {
  status: number
  user: SessionUser | null
  pendingFlow: string | null
  errors: AuthError[]
}

interface AllauthBody {
  data?: { user?: SessionUser; flows?: { id: string; is_pending?: boolean }[] }
  meta?: { is_authenticated?: boolean }
  errors?: AuthError[]
}

const BASE_URL = '/_allauth/browser/v1'
const SESSION_URL = `${BASE_URL}/auth/session`

const user = ref<SessionUser | null>(null)
const loaded = ref(false)

async function call(path: string, method: string, body?: unknown): Promise<AuthOutcome> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    credentials: 'same-origin',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      'Accept-Language': i18n.global.locale.value,
      'X-CSRFToken': csrfToken(),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  let parsed: AllauthBody = {}
  try {
    parsed = (await response.json()) as AllauthBody
  } catch {
    parsed = {}
  }
  const authenticated = Boolean(parsed.meta?.is_authenticated && parsed.data?.user)
  if (authenticated) user.value = parsed.data?.user ?? null
  else if (response.status === 401) user.value = null
  return {
    status: response.status,
    user: authenticated ? (parsed.data?.user ?? null) : null,
    pendingFlow: parsed.data?.flows?.find((flow) => flow.is_pending)?.id ?? null,
    errors: parsed.errors ?? [],
  }
}

async function loadSession() {
  try {
    const response = await fetch(SESSION_URL, { credentials: 'same-origin', headers: { Accept: 'application/json' } })
    const body = (await response.json()) as AllauthBody
    user.value = response.ok ? (body?.data?.user ?? null) : null
    loaded.value = true
  } catch {
    user.value = null
    loaded.value = false
  }
}

async function logout() {
  await fetch(SESSION_URL, {
    method: 'DELETE',
    credentials: 'same-origin',
    headers: { Accept: 'application/json', 'X-CSRFToken': csrfToken() },
  })
  user.value = null
}

function clearUser() {
  user.value = null
}

export const auth = {
  login: (identifier: string, password: string) =>
    call('/auth/login', 'POST', identifier.includes('@') ? { email: identifier, password } : { username: identifier, password }),
  signup: (data: { username: string; email: string; password: string }) =>
    call('/auth/signup', 'POST', { username: data.username, email: data.email, password: data.password }),
  verifyEmail: (key: string) => call('/auth/email/verify', 'POST', { key }),
}

export function useSession() {
  return { user, loaded, loadSession, logout, clearUser }
}
