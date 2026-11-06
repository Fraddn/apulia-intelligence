<template>
  <div v-if="loaded" class="user-menu">
    <template v-if="user">
      <span class="user-menu__user" :title="user.email">
        <AppIcon name="user" />
        <span class="visually-hidden">{{ t('auth.signedInAs') }}</span>
        <strong class="user-menu__name">{{ user.display }}</strong>
      </span>
      <button type="button" class="btn btn--small btn--round user-menu__logout" @click="onLogout">
        <AppIcon name="logout" :size="16" />
        {{ t('auth.logOut') }}
      </button>
    </template>
    <RouterLink
      v-else-if="route.name !== 'login'"
      :to="{ name: 'login' }"
      class="btn btn--small btn--round user-menu__login"
    >
      <AppIcon name="login" :size="16" />
      {{ t('auth.logIn') }}
    </RouterLink>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { useSession } from '../session'
import AppIcon from './AppIcon.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { user, loaded, loadSession, logout } = useSession()

async function onLogout() {
  await logout()
  await router.replace({ name: 'login' })
}

onMounted(() => {
  if (!loaded.value) loadSession()
})
</script>
