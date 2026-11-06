<template>
  <AuthCard :title="t('auth.login.title')" :subtitle="t('auth.login.subtitle')" icon="lock">
    <AuthNotice v-if="notice === 'verified'" tone="success">{{ t('auth.login.verifiedNotice') }}</AuthNotice>
    <AuthNotice v-if="pendingVerification" tone="info">
      <strong>{{ t('auth.signup.checkInbox') }}</strong>
      {{ t('auth.login.pendingVerification') }}
    </AuthNotice>
    <AuthNotice v-if="formError" tone="error">{{ formError }}</AuthNotice>
    <form class="auth__form" novalidate @submit.prevent="onSubmit">
      <label class="auth-field">
        <span class="auth-field__label">{{ t('auth.login.identifier') }}</span>
        <input
          v-model.trim="identifier"
          class="input"
          type="text"
          name="username"
          autocomplete="username"
          autocapitalize="none"
          spellcheck="false"
          required
          :aria-invalid="Boolean(identifierError)"
        >
        <span v-if="identifierError" class="auth-field__error">{{ identifierError }}</span>
      </label>
      <label class="auth-field">
        <span class="auth-field__label">{{ t('auth.password') }}</span>
        <input
          v-model="password"
          class="input"
          type="password"
          name="password"
          autocomplete="current-password"
          required
          :aria-invalid="Boolean(fieldErrors.password)"
        >
        <span v-if="fieldErrors.password" class="auth-field__error">{{ fieldErrors.password }}</span>
      </label>
      <button type="submit" class="btn btn--primary auth__submit" :disabled="busy || !identifier || !password">
        {{ busy ? t('auth.working') : t('auth.login.submit') }}
      </button>
    </form>
    <template #footer>
      {{ t('auth.login.noAccount') }}
      <RouterLink :to="{ name: 'signup', query: route.query.next ? { next: route.query.next } : {} }">
        {{ t('auth.login.signUpLink') }}
      </RouterLink>
    </template>
  </AuthCard>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { useAuthForm } from '../authForm'
import AuthCard from '../components/AuthCard.vue'
import AuthNotice from '../components/AuthNotice.vue'
import { safeNext } from '../router'
import { auth, useSession } from '../session'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { busy, fieldErrors, formError, submit } = useAuthForm()

const identifier = ref('')
const password = ref('')
const pendingVerification = ref(false)
const notice = computed(() => route.query.notice)
const identifierError = computed(() => fieldErrors.value.email || fieldErrors.value.username)

async function onSubmit() {
  pendingVerification.value = false
  const outcome = await submit(() => auth.login(identifier.value, password.value))
  if (!outcome) return
  if (outcome.status === 409) await useSession().loadSession()
  if (outcome.user || outcome.status === 409) {
    await router.replace(safeNext(route.query.next))
  } else if (outcome.pendingFlow === 'verify_email') {
    pendingVerification.value = true
  }
}
</script>
