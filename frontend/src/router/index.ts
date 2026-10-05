import { createRouter, createWebHistory, type RouteRecordRaw, type RouterHistory } from 'vue-router'
import { useStartingProfileStore } from '../stores/data'
import { NAV_ITEMS } from './nav'

/** Views are loaded lazily so the first paint only pays for the page being opened. */
export const routes: RouteRecordRaw[] = [
  { path: '/', name: 'today', component: () => import('../views/TodayView.vue'), meta: { title: 'Today' } },
  { path: '/prepare', name: 'prepare', component: () => import('../views/PrepareView.vue'), meta: { title: 'Prepare' } },
  { path: '/prepare/dsa', name: 'dsa', component: () => import('../views/DsaView.vue'), meta: { title: 'DSA' } },
  {
    path: '/prepare/dsa/problems',
    name: 'problems',
    component: () => import('../views/dsa/ProblemsView.vue'),
    meta: { title: 'DSA problems' },
  },
  {
    path: '/prepare/dsa/problems/:problemKey',
    name: 'problem',
    component: () => import('../views/dsa/ProblemDetailView.vue'),
    meta: { title: 'Problem' },
  },
  {
    path: '/prepare/dsa/attempts/:id(\\d+)',
    name: 'attempt',
    component: () => import('../views/dsa/AttemptDetailView.vue'),
    meta: { title: 'Attempt' },
  },
  {
    path: '/prepare/:slug(cs|system-design|lld|behavioral)',
    name: 'track',
    component: () => import('../views/TrackView.vue'),
    meta: { title: 'Prepare' },
  },
  {
    path: '/prepare/:slug(python|engineering|projects)',
    name: 'curriculum',
    component: () => import('../views/CurriculumView.vue'),
    meta: { title: 'Prepare' },
  },
  { path: '/log', name: 'log', component: () => import('../views/LogView.vue'), meta: { title: 'Log practice' } },
  {
    path: '/onboarding',
    name: 'onboarding',
    component: () => import('../views/OnboardingView.vue'),
    meta: { title: 'Starting profile', bare: true },
  },
  {
    path: '/calibrate',
    name: 'calibrate',
    component: () => import('../views/CalibrateView.vue'),
    meta: { title: 'Calibrate your skills' },
  },
  { path: '/baseline', name: 'baseline', component: () => import('../views/BaselineView.vue'), meta: { title: 'Baseline' } },
  { path: '/skills/:key', name: 'skill', component: () => import('../views/SkillDetailView.vue'), meta: { title: 'Skill' } },
  {
    path: '/learn/session/:id(\\d+)',
    name: 'session',
    component: () => import('../views/learn/LearningSessionView.vue'),
    meta: { title: 'Learning session' },
  },
  { path: '/learn/:key', name: 'learn', component: () => import('../views/learn/LearnContentView.vue'), meta: { title: 'Learn' } },
  { path: '/revise', name: 'revision', component: () => import('../views/RevisionView.vue'), meta: { title: 'Revise' } },
  { path: '/mocks', name: 'mocks', component: () => import('../views/MocksView.vue'), meta: { title: 'Mocks' } },
  { path: '/progress', name: 'progress', component: () => import('../views/ProgressView.vue'), meta: { title: 'Progress' } },
  { path: '/review', name: 'review', component: () => import('../views/WeeklyReviewView.vue'), meta: { title: 'Weekly review' } },
  { path: '/roadmap', name: 'roadmap', component: () => import('../views/RoadmapView.vue'), meta: { title: 'Roadmap' } },
  { path: '/settings', name: 'settings', component: () => import('../views/SettingsView.vue'), meta: { title: 'Settings' } },
  {
    path: '/settings/developer',
    name: 'developer',
    component: () => import('../views/settings/DeveloperView.vue'),
    meta: { title: 'Developer / System' },
  },
  {
    path: '/settings/developer/catalog',
    name: 'catalog',
    component: () => import('../views/settings/CatalogView.vue'),
    meta: { title: 'Catalog verification' },
  },
  // Old locations keep working.
  { path: '/skills', redirect: '/prepare' },
  { path: '/revision', redirect: '/revise' },
  { path: '/log/problems', redirect: '/prepare/dsa/problems' },
  { path: '/status', redirect: '/settings/developer' },
  { path: '/catalog', redirect: '/settings/developer/catalog' },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

export { NAV_ITEMS }

export function createAppRouter(history: RouterHistory = createWebHistory()) {
  const router = createRouter({
    history,
    routes,
    scrollBehavior: (_to, _from, saved) => saved ?? { top: 0 },
  })
  /**
   * First run: until the starting profile is completed, every page leads to the onboarding. Developer tools stay
   * reachable. If the profile cannot be read (engine down) navigation is never blocked.
   */
  router.beforeEach(async (to) => {
    if (to.name === 'onboarding' || to.path.startsWith('/settings/developer')) return true
    try {
      const profile = useStartingProfileStore()
      await profile.ensure()
      if (profile.data && !profile.data.onboarding.completed) return { name: 'onboarding' }
    } catch {
      // fail open
    }
    return true
  })
  router.afterEach((to) => {
    document.title = to.meta.title ? `${String(to.meta.title)} · Master Mentor` : 'Master Mentor'
  })
  return router
}
