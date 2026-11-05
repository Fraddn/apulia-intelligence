<template>
  <div v-if="loaded" class="user-menu">
    <template v-if="user">
      <span class="user-menu__label">{{ t('auth.signedInAs') }}</span>
      <strong class="user-menu__name" :title="user.email">{{ user.display }}</strong>
      <button type="button" class="btn btn--small user-menu__logout" @click="logout">{{ t('auth.logOut') }}</button>
    </template>
    <a v-else href="/accounts/login/" class="btn btn--small user-menu__login">{{ t('auth.logIn') }}</a>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSession } from '../session'

const { t } = useI18n()
const { user, loaded, loadSession, logout } = useSession()

onMounted(loadSession)
</script>
