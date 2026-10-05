import { createRouter, createWebHistory, type RouteRecordRaw, type RouterHistory } from 'vue-router'
import BaselineView from '../views/baseline/BaselineView.vue'
import CatalogView from '../views/CatalogView.vue'
import StatusView from '../views/StatusView.vue'
import AttemptDetailView from '../views/log/AttemptDetailView.vue'
import LogView from '../views/log/LogView.vue'
import ProblemDetailView from '../views/log/ProblemDetailView.vue'
import ProblemsView from '../views/log/ProblemsView.vue'
import MocksView from '../views/mocks/MocksView.vue'
import ProgressView from '../views/progress/ProgressView.vue'
import RevisionView from '../views/revision/RevisionView.vue'
import SettingsView from '../views/settings/SettingsView.vue'
import TodayView from '../views/today/TodayView.vue'
import SkillDetailView from '../views/skills/SkillDetailView.vue'
import SkillsView from '../views/skills/SkillsView.vue'

/** The 7 pages of docs/engineering/UI_SPEC.md §2. Content arrives in later slices. */
export const NAV_ROUTES: RouteRecordRaw[] = [
  { path: '/', name: 'today', component: TodayView, meta: { title: 'Today' } },
  { path: '/log', name: 'log', component: LogView, meta: { title: 'Log' } },
  { path: '/skills', name: 'skills', component: SkillsView, meta: { title: 'Skills' } },
  { path: '/revision', name: 'revision', component: RevisionView, meta: { title: 'Revision' } },
  { path: '/mocks', name: 'mocks', component: MocksView, meta: { title: 'Mocks' } },
  { path: '/progress', name: 'progress', component: ProgressView, meta: { title: 'Progress' } },
  { path: '/settings', name: 'settings', component: SettingsView, meta: { title: 'Settings' } },
]

export const routes: RouteRecordRaw[] = [
  ...NAV_ROUTES,
  { path: '/status', name: 'status', component: StatusView, meta: { title: 'System status' } },
  { path: '/log/problems', name: 'problems', component: ProblemsView, meta: { title: 'Problems' } },
  { path: '/log/problems/:problemKey', name: 'problem', component: ProblemDetailView, meta: { title: 'Problem' } },
  { path: '/log/attempts/:id(\\d+)', name: 'attempt', component: AttemptDetailView, meta: { title: 'Attempt' } },
  { path: '/skills/:key', name: 'skill', component: SkillDetailView, meta: { title: 'Skill' } },
  { path: '/baseline', name: 'baseline', component: BaselineView, meta: { title: 'Baseline battery' } },
  { path: '/catalog', name: 'catalog', component: CatalogView, meta: { title: 'Catalog (internal)' } },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

export function createAppRouter(history: RouterHistory = createWebHistory()) {
  return createRouter({ history, routes })
}
