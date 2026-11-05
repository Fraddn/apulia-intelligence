import { ref } from 'vue'

export interface SessionUser {
  id: number
  display: string
  email: string
}

const SESSION_URL = '/_allauth/browser/v1/auth/session'

const user = ref<SessionUser | null>(null)
const loaded = ref(false)

function csrfToken(): string {
  return document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/)?.[1] ?? ''
}

async function loadSession() {
  try {
    const response = await fetch(SESSION_URL, { credentials: 'same-origin', headers: { Accept: 'application/json' } })
    const body = await response.json()
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

export function useSession() {
  return { user, loaded, loadSession, logout }
}
