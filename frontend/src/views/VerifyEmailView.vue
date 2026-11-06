<template>
  <AuthCard v-if="state === 'working'" :title="t('auth.verify.title')" icon="mail">
    <LoadState :loading="true" :error="false" />
  </AuthCard>
  <AuthCard
    v-else-if="state === 'confirmed'"
    :title="t('auth.verify.confirmed')"
    :subtitle="t('auth.verify.confirmedText')"
    icon="check"
  >
    <RouterLink :to="{ name: 'login', query: { notice: 'verified' } }" class="btn btn--primary auth__submit">
      {{ t('auth.logIn') }}
    </RouterLink>
  </AuthCard>
  <AuthCard v-else :title="t('auth.verify.invalid')" :subtitle="message || t('auth.verify.invalidText')" icon="alert">
    <RouterLink :to="{ name: 'login' }" class="btn auth__submit">{{ t('auth.backToLogin') }}</RouterLink>
  </AuthCard>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import AuthCard from '../components/AuthCard.vue'
import LoadState from '../components/LoadState.vue'
import { auth } from '../session'

const props = defineProps<{ token: string }>()

const { t } = useI18n()
const router = useRouter()
const state = ref<'working' | 'confirmed' | 'invalid'>('working')
const message = ref('')

onMounted(async () => {
  try {
    const outcome = await auth.verifyEmail(props.token)
    if (outcome.user) {
      await router.replace('/')
      return
    }
    if (outcome.status === 401) {
      state.value = 'confirmed'
      return
    }
    message.value = outcome.status === 429 ? t('auth.errors.tooMany') : ''
    state.value = 'invalid'
  } catch {
    message.value = t('auth.errors.offline')
    state.value = 'invalid'
  }
})
</script>
