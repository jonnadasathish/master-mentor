<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { api } from '../../api'
import { ApiError } from '../../api/client'
import type { ActiveGoal, GoalVersion, Settings } from '../../api/types'
import ContentManager from '../../components/ContentManager.vue'
import ImportPanel from '../../components/ImportPanel.vue'
import { useErrorStore } from '../../stores/errors'

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const settings = reactive<Settings>({ timezone: '', display_name: '' })
const goal = ref<ActiveGoal | null>(null)
const history = ref<GoalVersion[]>([])
const form = reactive({ targetDate: '', budgets: [90, 90, 90, 90, 90, 75, 75] })
const message = ref('')
const errors = ref<string[]>([])
const errorStore = useErrorStore()
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
  try {
    Object.assign(settings, (await api.get<Settings>('/settings')).data)
    history.value = (await api.get<GoalVersion[]>('/goals/history')).data
  } catch (caught) {
    errorStore.report(caught, 'settings')
  }
  try {
    goal.value = (await api.get<ActiveGoal>('/goals/active')).data
    form.targetDate = goal.value.target_date ?? ''
    form.budgets = [...goal.value.weekday_budgets]
  } catch (caught) {
    if (!(caught instanceof ApiError && caught.status === 404)) errorStore.report(caught, 'settings')
    goal.value = null
  }
}

async function saveSettings(): Promise<void> {
  errors.value = []
  try {
    await api.patch('/settings', { timezone: settings.timezone, display_name: settings.display_name })
    message.value = 'Settings saved.'
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
    await load()
  } catch (caught) {
    report(caught)
  }
}

onMounted(load)
</script>

<template>
  <section>
    <h1>Settings</h1>
    <form
      class="card"
      data-testid="settings-form"
      @submit.prevent="saveSettings"
    >
      <h2>Profile</h2>
      <label>Display name <input
        v-model="settings.display_name"
        maxlength="100"
      ></label>
      <label>Timezone (IANA) <input
        v-model="settings.timezone"
        maxlength="64"
        data-testid="timezone"
      ></label>
      <button type="submit">
        Save settings
      </button>
    </form>

    <form
      class="card"
      data-testid="goal-form"
      @submit.prevent="saveGoal"
    >
      <h2>Goal</h2>
      <p
        v-if="goal"
        data-testid="goal-summary"
      >
        Phase <strong>{{ goal.phase }}</strong>
        <template v-if="goal.weeks_left">
          · {{ goal.weeks_left }} weeks left
        </template>
        · {{ goal.weekly_minutes }} min/week · profile {{ goal.profile_key }}
      </p>
      <p v-else>
        No goal yet. Set a target date (optional) and your daily minutes.
      </p>
      <label>Target interview date <input
        v-model="form.targetDate"
        type="date"
        data-testid="target-date"
      ></label>
      <fieldset class="budgets">
        <legend>Minutes per day ({{ weekly }} / week)</legend>
        <label
          v-for="(d, i) in DAYS"
          :key="d"
        >{{ d }} <input
          v-model.number="form.budgets[i]"
          type="number"
          min="0"
          max="600"
          :data-testid="`budget-${i}`"
        ></label>
      </fieldset>
      <button
        type="submit"
        data-testid="save-goal"
      >
        {{ goal ? 'Save as new goal version' : 'Create goal' }}
      </button>
    </form>

    <p
      v-if="message"
      role="status"
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

    <h2>Goal history</h2>
    <table v-if="history.length">
      <thead>
        <tr><th>Valid from</th><th>Valid to</th><th>Target</th><th>Min/week</th></tr>
      </thead>
      <tbody>
        <tr
          v-for="g in history"
          :key="g.id"
        >
          <td>{{ g.valid_from }}</td><td>{{ g.valid_to ?? 'active' }}</td>
          <td>{{ g.target_date ?? '—' }}</td><td>{{ g.weekly_minutes }}</td>
        </tr>
      </tbody>
    </table>

    <h2>Content</h2>
    <ContentManager />
    <h2>Data</h2>
    <ImportPanel />
    <p>
      <a
        href="/api/v1/export/json"
        data-testid="export-json"
      >Download JSON export</a> ·
      <a href="/api/v1/export/csv">CSV (zip)</a>
    </p>
  </section>
</template>

<style scoped>
.card { border: 1px solid #d8d8de; border-radius: 8px; padding: 0.75rem 1rem; margin: 1rem 0; background: #fff; display: flex; flex-direction: column; gap: 0.5rem; max-width: 40rem; }
label { display: flex; flex-direction: column; font-size: 0.85rem; gap: 0.2rem; }
.budgets { display: flex; flex-wrap: wrap; gap: 0.5rem; border: none; padding: 0; min-width: 0; }
.budgets input { width: 4.5rem; }
.errors { color: #a11; }
table { border-collapse: collapse; font-size: 0.9rem; }
th, td { text-align: left; padding: 0.25rem 0.6rem; border-bottom: 1px solid #eee; }
</style>
