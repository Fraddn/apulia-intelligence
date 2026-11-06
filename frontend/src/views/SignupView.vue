<template>
  <AuthCard
    v-if="sentTo"
    :title="t('auth.signup.checkInbox')"
    :subtitle="t('auth.signup.checkInboxText', { email: sentTo })"
    icon="mail"
  >
    <p class="auth__text">{{ t('auth.signup.checkInboxHint') }}</p>
    <RouterLink :to="{ name: 'login' }" class="btn auth__submit">{{ t('auth.backToLogin') }}</RouterLink>
  </AuthCard>
  <AuthCard v-else :title="t('auth.signup.title')" :subtitle="t('auth.signup.subtitle')" icon="user">
    <AuthNotice v-if="formError" tone="error">{{ formError }}</AuthNotice>
    <form class="auth__form" novalidate @submit.prevent="onSubmit">
      <label class="auth-field">
        <span class="auth-field__label">{{ t('auth.username') }}</span>
        <input
          v-model.trim="username"
          class="input"
          type="text"
          name="username"
          autocomplete="username"
          autocapitalize="none"
          spellcheck="false"
          required
          :aria-invalid="Boolean(fieldErrors.username)"
        >
        <span v-if="fieldErrors.username" class="auth-field__error">{{ fieldErrors.username }}</span>
        <span v-else class="auth-field__hint">{{ t('auth.usernameHint') }}</span>
      </label>
      <label class="auth-field">
        <span class="auth-field__label">{{ t('auth.email') }}</span>
        <input
          v-model.trim="email"
          class="input"
          type="email"
          name="email"
          autocomplete="email"
          required
          :aria-invalid="Boolean(fieldErrors.email)"
        >
        <span v-if="fieldErrors.email" class="auth-field__error">{{ fieldErrors.email }}</span>
      </label>
      <label class="auth-field">
        <span class="auth-field__label">{{ t('auth.password') }}</span>
        <input
          v-model="password"
          class="input"
          type="password"
          name="password"
          autocomplete="new-password"
          required
          :aria-invalid="Boolean(fieldErrors.password)"
        >
        <span v-if="fieldErrors.password" class="auth-field__error">{{ fieldErrors.password }}</span>
        <span v-else class="auth-field__hint">{{ t('auth.passwordHint') }}</span>
      </label>
      <label class="auth-field">
        <span class="auth-field__label">{{ t('auth.passwordConfirm') }}</span>
        <input
          v-model="confirm"
          class="input"
          type="password"
          name="password-confirm"
          autocomplete="new-password"
          required
          :aria-invalid="mismatch"
        >
        <span v-if="mismatch" class="auth-field__error">{{ t('auth.passwordsDiffer') }}</span>
      </label>
      <button type="submit" class="btn btn--primary auth__submit" :disabled="busy || !username || !email || !password || !confirm || mismatch">
        {{ busy ? t('auth.working') : t('auth.signup.submit') }}
      </button>
    </form>
    <template #footer>
      {{ t('auth.signup.haveAccount') }}
      <RouterLink :to="{ name: 'login', query: route.query.next ? { next: route.query.next } : {} }">
        {{ t('auth.signup.logInLink') }}
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
import { auth } from '../session'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { busy, fieldErrors, formError, submit } = useAuthForm()

const username = ref('')
const email = ref('')
const password = ref('')
const confirm = ref('')
const sentTo = ref('')
const mismatch = computed(() => confirm.value.length > 0 && confirm.value !== password.value)

async function onSubmit() {
  if (mismatch.value) return
  const outcome = await submit(() => auth.signup({ username: username.value, email: email.value, password: password.value }))
  if (!outcome) return
  if (outcome.user) await router.replace(safeNext(route.query.next))
  else if (outcome.pendingFlow === 'verify_email') sentTo.value = email.value
}
</script>
