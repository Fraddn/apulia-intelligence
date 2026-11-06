import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import type { AuthOutcome } from './session'

const FIELDS = ['username', 'email', 'password']

export function useAuthForm() {
  const { t } = useI18n()
  const busy = ref(false)
  const fieldErrors = ref<Record<string, string>>({})
  const formError = ref('')

  function reset() {
    fieldErrors.value = {}
    formError.value = ''
  }

  async function submit(action: () => Promise<AuthOutcome>): Promise<AuthOutcome | null> {
    busy.value = true
    reset()
    try {
      const outcome = await action()
      if (outcome.status === 429) formError.value = t('auth.errors.tooMany')
      else if (outcome.status >= 500) formError.value = t('auth.errors.generic')
      const general: string[] = []
      for (const error of outcome.errors) {
        if (error.param && FIELDS.includes(error.param)) {
          const current = fieldErrors.value[error.param]
          fieldErrors.value = { ...fieldErrors.value, [error.param]: current ? `${current} ${error.message}` : error.message }
        } else {
          general.push(error.message)
        }
      }
      if (general.length) formError.value = general.join(' ')
      return outcome
    } catch {
      formError.value = t('auth.errors.offline')
      return null
    } finally {
      busy.value = false
    }
  }

  return { busy, fieldErrors, formError, submit, reset }
}
