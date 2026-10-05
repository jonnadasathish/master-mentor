<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../../api'
import type { Effects, Today } from '../../api/types'
import EffectsPanel from '../../components/EffectsPanel.vue'
import PlanItemCard from '../../components/PlanItemCard.vue'
import StatusBadge from '../../components/StatusBadge.vue'
import { useErrorStore } from '../../stores/errors'

const today = ref<Today | null>(null)
const lastEffects = ref<Effects | null>(null)
const showWhy = ref(false)
const errorStore = useErrorStore()

/** UI_SPEC §3 header. Every number comes from the read model. */
const header = computed(() => {
  const t = today.value
  if (!t) return ''
  const weeks = t.weeks_left ? ` · ${t.weeks_left} weeks left` : ''
  if (t.calibration.active) {
    return `Calibration · ${t.calibration.assessed}/${t.calibration.required} skills measured · battery ${t.calibration.battery_done}/${t.calibration.battery_total}${weeks} · ${t.phase}`
  }
  const limiting = t.readiness.limiting_component ? ` · limiting: ${t.readiness.limiting_component}` : ''
  return `${t.readiness.state.replace('_', ' ')}${limiting}${weeks} · ${t.phase}`
})

async function load(): Promise<void> {
  try {
    today.value = (await api.get<Today>('/today')).data
  } catch (caught) {
    errorStore.report(caught, 'today')
  }
}

async function completed(effects?: Effects): Promise<void> {
  lastEffects.value = effects ?? null
  await load()
}

async function regenerate(): Promise<void> {
  try {
    today.value = (await api.post<Today>('/plan/today/regenerate', {})).data
  } catch (caught) {
    errorStore.report(caught, 'today')
  }
}

onMounted(load)
</script>

<template>
  <section v-if="today">
    <h1 class="sr-only">
      Today · {{ today.plan_date }}
    </h1>
    <header
      class="state"
      data-testid="today-header"
    >
      <strong>{{ header }}</strong>
      <span class="date">{{ today.plan_date }}</span>
    </header>
    <p
      class="blockers"
      data-testid="today-readiness"
    >
      Readiness: <RouterLink :to="{ name: 'progress' }">
        {{ today.readiness.state.replace('_', ' ') }}
      </RouterLink>
      <template v-if="today.readiness.blockers.length">
        · Blockers: {{ today.readiness.blockers.map((b) => `${b.gate} ${b.message}`).join(' · ') }}
      </template>
      · <RouterLink :to="{ name: 'progress' }">
        all gates ▸
      </RouterLink>
      <template v-if="!today.goal_exists">
        · <RouterLink :to="{ name: 'settings' }">
          set a goal
        </RouterLink>
      </template>
    </p>

    <section
      class="mentor"
      aria-label="Mentor"
    >
      <p data-testid="mentor-message">
        {{ today.plan.message.text }}
      </p>
      <button
        type="button"
        class="link"
        :aria-expanded="showWhy"
        data-testid="message-why"
        @click="showWhy = !showWhy"
      >
        why {{ showWhy ? '▾' : '▸' }}
      </button>
      <dl
        v-if="showWhy"
        class="metrics"
        data-testid="message-payload"
      >
        <div><dt>rule</dt><dd>{{ today.plan.message.rule }}</dd></div>
        <div
          v-for="(value, key) in today.plan.message.payload"
          :key="key"
        >
          <dt>{{ key }}</dt><dd>{{ Array.isArray(value) ? value.join(', ') : value }}</dd>
        </div>
      </dl>
    </section>

    <EffectsPanel
      v-if="lastEffects"
      :effects="lastEffects"
    />

    <h2>Today's plan · {{ today.plan.allocated_minutes }} / {{ today.plan.budget_minutes }} min</h2>
    <ol
      class="plan"
      data-testid="plan-items"
    >
      <PlanItemCard
        v-for="item in today.plan.items"
        :key="item.id"
        :item="item"
        :client="api"
        @changed="load"
        @completed="completed"
      />
    </ol>
    <p v-if="!today.plan.items.length">
      Nothing planned: no gaps above threshold and nothing due.
    </p>
    <p class="meta">
      {{ today.plan.unallocated_minutes }} min unallocated (the mentor does not invent work).
      <button
        type="button"
        class="link"
        data-testid="regenerate"
        @click="regenerate"
      >
        Regenerate remaining plan
      </button>
    </p>

    <template v-if="today.top_gaps.length">
      <h2>Top gaps</h2>
      <ul class="gaps">
        <li
          v-for="g in today.top_gaps"
          :key="g.skill_key"
        >
          <RouterLink :to="{ name: 'skill', params: { key: g.skill_key } }">
            {{ g.skill_key }}
          </RouterLink>
          <StatusBadge
            :status="g.status"
            :priority="g.priority"
          />
          {{ g.primary_gap_type?.toLowerCase().replace('_', ' ') }} → {{ g.focus_stage?.toLowerCase() }}
        </li>
      </ul>
    </template>

    <footer
      class="footer"
      data-testid="today-footer"
    >
      <div>
        <h2>Stop list</h2>
        <ul
          v-if="today.plan.stop_list.length"
          data-testid="stop-list"
        >
          <li
            v-for="s in today.plan.stop_list"
            :key="s.skill"
          >
            {{ s.instruction }}
          </li>
        </ul>
        <p v-else>
          Nothing to stop.
        </p>
      </div>
      <p>
        <RouterLink :to="{ name: 'revision' }">
          Revision
        </RouterLink>: {{ today.revisions.overdue }} overdue · {{ today.revisions.due }} due · backlog
        {{ today.revisions.backlog_minutes }} min (cap {{ today.revisions.cap_minutes }})
      </p>
    </footer>
  </section>
</template>

<style scoped>
.state { display: flex; justify-content: space-between; gap: 1rem; flex-wrap: wrap; font-size: 1.1rem; border-bottom: 2px solid #3366cc; padding-bottom: 0.4rem; }
.date { color: #555; }
.blockers { font-size: 0.9rem; color: #333; }
.mentor { background: #eef3ff; border-left: 4px solid #3366cc; padding: 0.4rem 0.8rem; margin: 0.8rem 0; }
.mentor p { font-size: 1.1rem; margin: 0.3rem 0; }
.metrics { display: flex; flex-wrap: wrap; gap: 0.3rem 1.2rem; font-size: 0.8rem; }
.metrics dt { color: #666; }
.metrics dd { margin: 0; }
.meta { color: #555; font-size: 0.85rem; }
.plan { padding: 0; }
.gaps li { margin: 0.3rem 0; display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center; }
.footer { display: flex; justify-content: space-between; gap: 1rem; flex-wrap: wrap; border-top: 1px solid #ddd; margin-top: 1rem; }
.link { background: none; border: none; color: #2a55b0; text-decoration: underline; cursor: pointer; padding: 0; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
</style>
