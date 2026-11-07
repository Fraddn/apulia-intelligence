import { createRouter, createWebHistory, type RouteLocationNormalized } from 'vue-router'
import { useSession } from './session'

declare module 'vue-router' {
  interface RouteMeta {
    public?: boolean
    guestOnly?: boolean
  }
}

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'dashboard', component: () => import('./views/DashboardView.vue') },
    { path: '/companies', name: 'companies', component: () => import('./views/CompaniesView.vue') },
    { path: '/info', name: 'glossary', component: () => import('./views/GlossaryView.vue') },
    { path: '/library', name: 'library', component: () => import('./views/LibraryView.vue') },
    { path: '/compare', name: 'compare', component: () => import('./views/CompareView.vue') },
    { path: '/companies/:vat', name: 'company', component: () => import('./views/CompanyView.vue'), props: true },
    { path: '/login', name: 'login', component: () => import('./views/LoginView.vue'), meta: { public: true, guestOnly: true } },
    { path: '/signup', name: 'signup', component: () => import('./views/SignupView.vue'), meta: { public: true, guestOnly: true } },
    {
      path: '/account/verify-email/:token',
      name: 'verify-email',
      component: () => import('./views/VerifyEmailView.vue'),
      props: true,
      meta: { public: true },
    },
    { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('./views/NotFoundView.vue') },
  ],
  scrollBehavior: (to, from, saved) =>
    saved ?? (to.hash ? { el: decodeURIComponent(to.hash), top: 88 } : to.path === from.path ? false : { top: 0 }),
})

export function safeNext(value: unknown): string {
  return typeof value === 'string' && value.startsWith('/') && !value.startsWith('//') ? value : '/'
}

export function loginRoute(to: Pick<RouteLocationNormalized, 'fullPath'>) {
  return { name: 'login', query: to.fullPath === '/' ? {} : { next: to.fullPath } }
}

router.beforeEach(async (to) => {
  const { user, loaded, loadSession } = useSession()
  if (!loaded.value) await loadSession()
  if (to.meta.public) return to.meta.guestOnly && user.value ? { path: safeNext(to.query.next) } : true
  return user.value ? true : loginRoute(to)
})
