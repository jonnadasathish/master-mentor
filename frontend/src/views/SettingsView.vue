<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../api'
import { ApiError } from '../api/client'
import type { ActiveGoal, GoalVersion, Settings } from '../api/types'
import ErrorState from '../components/common/ErrorState.vue'
import Icon from '../components/common/Icon.vue'
import PageHeader from '../components/common/PageHeader.vue'
import SectionHeading from '../components/common/SectionHeading.vue'
import ContentManager from '../components/settings/ContentManager.vue'
import ImportPanel from '../components/settings/ImportPanel.vue'
import { formatMinutes, shortDate } from '../presentation/format'
import { PHASE_LABEL } from '../presentation/language'
import { refreshDerivedData, useProfileStore } from '../stores/data'

/** Your profile and goal, the content you bring (stories, projects), and your data. Technical tools live one click away. */
const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const profile = useProfileStore()
const settings = reactive<Settings>({ timezone: '', display_name: '' })
const goal = ref<ActiveGoal | null>(null)
const history = ref<GoalVersion[]>([])
const form = reactive({ targetDate: '', budgets: [90, 90, 90, 90, 90, 75, 75] })
const message = ref('')
const errors = ref<string[]>([])
const loadError = ref<unknown>(null)
const backup = ref<{ available: boolean; message: string; warning: boolean } | null>(null)
const weekly = computed(() => form.budgets.reduce((a, b) => a + (Number(b) || 0), 0))

function report(caught: unknown): void {
  if (caught instanceof ApiError) {
    const details = caught.details.errors as { loc: string[]; msg: string }[] | undefined
    errors.value = details?.map((d) => `${d.loc.at(-1)}: ${d.msg}`) ?? [caught.message]
  } else {
    errors.value = [String(caught)]
  }
}

async function load(): Promise<void> {
  loadError.value = null
  try {
    Object.assign(settings, (await api.get<Settings>('/settings')).data)
    history.value = (await api.get<GoalVersion[]>('/goals/history')).data
  } catch (caught) {
    loadError.value = caught
    return
  }
  try {
    goal.value = (await api.get<ActiveGoal>('/goals/active')).data
    form.targetDate = goal.value.target_date ?? ''
    form.budgets = [...goal.value.weekday_budgets]
  } catch (caught) {
    if (!(caught instanceof ApiError && caught.status === 404)) loadError.value = caught
    goal.value = null
  }
  try {
    backup.value = (await api.get<{ available: boolean; message: string; warning: boolean }>('/system/backup-status')).data
  } catch {
    backup.value = null // advisory only
  }
}

async function saveSettings(): Promise<void> {
  errors.value = []
  try {
    await api.patch('/settings', { timezone: settings.timezone, display_name: settings.display_name })
    message.value = 'Saved.'
    profile.settings.reset()
    await refreshDerivedData()
  } catch (caught) {
    report(caught)
  }
}

async function saveGoal(): Promise<void> {
  errors.value = []
  const budgets = form.budgets.map((b) => Number(b) || 0)
  try {
    if (goal.value) {
      const body: Record<string, unknown> = { weekday_budgets: budgets }
      if (form.targetDate && form.targetDate !== goal.value.target_date) body.target_date = form.targetDate
      if (!form.targetDate && goal.value.target_date) body.clear_target_date = true
      await api.patch('/goals/active', body)
    } else {
      await api.post('/goals', { target_date: form.targetDate || null, weekday_budgets: budgets })
    }
    message.value = 'Goal saved as a new version (history below).'
    profile.goal.reset()
    await refreshDerivedData()
    await load()
  } catch (caught) {
    report(caught)
  }
}

onMounted(load)
</script>

<template>
  <div class="page page-narrow">
    <PageHeader
      eyebrow="Settings"
      title="Make it yours"
    />
    <ErrorState
      v-if="loadError"
      :error="loadError"
      @retry="load"
    />

    <RouterLink
      :to="{ name: 'onboarding' }"
      class="profile-link"
      data-testid="edit-starting-profile"
    >
      <Icon
        name="message"
        :size="16"
      />
      <span><strong>Starting profile</strong> Your experience, stack, target and what you believe about your skills</span>
      <Icon
        name="chevron-right"
        :size="16"
      />
    </RouterLink>

    <form
      class="card"
      data-testid="settings-form"
      @submit.prevent="saveSettings"
    >
      <h2>About you</h2>
      <label>Your name
        <input
          v-model="settings.display_name"
          maxlength="100"
        >
      </label>
      <label>Timezone <span class="muted">(for example Asia/Kolkata)</span>
        <input
          v-model="settings.timezone"
          maxlength="64"
          data-testid="timezone"
        >
      </label>
      <button
        type="submit"
        class="btn"
      >
        Save
      </button>
    </form>

    <form
      class="card"
      data-testid="goal-form"
      @submit.prevent="saveGoal"
    >
      <h2>Your goal</h2>
      <p
        v-if="goal"
        class="muted"
        data-testid="goal-summary"
      >
        {{ PHASE_LABEL[goal.phase] ?? goal.phase }}<template v-if="goal.weeks_left">
          · {{ goal.weeks_left.replace(/\.0$/, '') }} weeks to go
        </template>
        · {{ formatMinutes(goal.weekly_minutes) }} a week
      </p>
      <p
        v-else
        class="muted"
      >
        Set a target date (optional) and how much time you have each day. Master Mentor plans your days from this.
      </p>
      <label>Target interview date
        <input
          v-model="form.targetDate"
          type="date"
          data-testid="target-date"
        >
      </label>
      <fieldset class="budgets">
        <legend>Minutes you can give each day <span class="muted">({{ formatMinutes(weekly) }} a week)</span></legend>
        <div class="days">
          <label
            v-for="(d, i) in DAYS"
            :key="d"
          >{{ d }}
            <input
              v-model.number="form.budgets[i]"
              type="number"
              min="0"
              max="600"
              :data-testid="`budget-${i}`"
            >
          </label>
        </div>
      </fieldset>
      <button
        type="submit"
        class="btn btn-primary"
        data-testid="save-goal"
      >
        {{ goal ? 'Save changes' : 'Create goal' }}
      </button>
    </form>

    <p
      v-if="message"
      role="status"
      class="ok"
      data-testid="settings-message"
    >
      {{ message }}
    </p>
    <ul
      v-if="errors.length"
      role="alert"
      class="errors"
    >
      <li
        v-for="e in errors"
        :key="e"
      >
        {{ e }}
      </li>
    </ul>

    <details
      v-if="history.length"
      class="history"
    >
      <summary>Goal history ({{ history.length }})</summary>
      <ul>
        <li
          v-for="g in history"
          :key="g.id"
        >
          From {{ shortDate(g.valid_from) }}<template v-if="g.valid_to">
            to {{ shortDate(g.valid_to) }}
          </template><template v-else>
            (now)
          </template>
          · {{ g.target_date ? `target ${shortDate(g.target_date)}` : 'no target date' }} · {{ formatMinutes(g.weekly_minutes) }} a week
        </li>
      </ul>
    </details>

    <section>
      <SectionHeading title="Your stories, projects and prompts" />
      <ContentManager />
    </section>

    <section class="stack">
      <SectionHeading title="Your data" />
      <div
        v-if="backup"
        class="backup"
        :class="{ warn: backup.warning }"
        data-testid="backup-summary"
      >
        <Icon
          :name="backup.warning ? 'alert-triangle' : 'check-circle'"
          :size="16"
        />
        <span>{{ backup.message }}</span>
      </div>
      <p class="downloads">
        <a
          href="/api/v1/export/json"
          class="btn"
          data-testid="export-json"
        >Download everything (JSON)</a>
        <a
          href="/api/v1/export/csv"
          class="btn"
        >Download as spreadsheets (CSV)</a>
      </p>
      <ImportPanel />
    </section>

    <RouterLink
      :to="{ name: 'developer' }"
      class="dev-link"
      data-testid="developer-link"
    >
      <Icon
        name="settings"
        :size="16"
      />
      <span><strong>Developer / System</strong> Health, versions and technical tools</span>
      <Icon
        name="chevron-right"
        :size="16"
      />
    </RouterLink>
  </div>
</template>

<style scoped>
.card { display: grid; gap: var(--s-4); }
label { display: grid; gap: var(--s-1); font-weight: 560; }
.days { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: var(--s-2); }
.days input { width: 100%; }
legend { font-weight: 560; margin-bottom: var(--s-2); }
.ok { color: var(--healthy-fg); font-weight: 560; }
.errors { color: var(--critical-fg); }
.history { font-size: var(--fs-sm); color: var(--text-2); }
.history summary { cursor: pointer; }
.history ul { display: grid; gap: var(--s-1); margin-top: var(--s-2); }
.backup { display: flex; align-items: center; gap: var(--s-2); padding: var(--s-3) var(--s-4); background: var(--healthy-bg); color: var(--healthy-fg); border-radius: var(--r-md); font-size: var(--fs-sm); }
.backup.warn { background: var(--medium-bg); color: var(--medium-fg); }
.downloads { display: flex; gap: var(--s-3); flex-wrap: wrap; }
.profile-link, .dev-link { display: flex; align-items: center; gap: var(--s-3); padding: var(--s-4) var(--s-5); background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-lg); color: var(--text-2); }
.profile-link span, .dev-link span { flex: 1; font-size: var(--fs-sm); }
.profile-link strong, .dev-link strong { display: block; color: var(--text); font-size: var(--fs-base); }
.profile-link:hover, .dev-link:hover { text-decoration: none; border-color: var(--border-strong); }
@media (max-width: 767px) { .days { grid-template-columns: repeat(4, minmax(0, 1fr)); } }
</style>
