<template>
  <div v-if="loaded" class="user-menu">
    <template v-if="user">
      <span class="user-menu__user" :title="user.email">
        <AppIcon name="user" />
        <span class="visually-hidden">{{ t('auth.signedInAs') }}</span>
        <strong class="user-menu__name">{{ user.display }}</strong>
      </span>
      <button type="button" class="btn btn--small btn--round user-menu__logout" @click="logout">
        <AppIcon name="logout" :size="16" />
        {{ t('auth.logOut') }}
      </button>
    </template>
    <a v-else href="/accounts/login/" class="btn btn--small btn--round user-menu__login">
      <AppIcon name="login" :size="16" />
      {{ t('auth.logIn') }}
    </a>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSession } from '../session'
import AppIcon from './AppIcon.vue'

const { t } = useI18n()
const { user, loaded, loadSession, logout } = useSession()

onMounted(loadSession)
</script>
