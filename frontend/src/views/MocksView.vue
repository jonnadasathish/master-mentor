<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { api } from '../api'
import type { Effects } from '../api/types'
import EmptyState from '../components/common/EmptyState.vue'
import ErrorState from '../components/common/ErrorState.vue'
import Icon from '../components/common/Icon.vue'
import PageHeader from '../components/common/PageHeader.vue'
import SectionHeading from '../components/common/SectionHeading.vue'
import Skeleton from '../components/common/Skeleton.vue'
import StatusPill from '../components/common/StatusPill.vue'
import EffectsPanel from '../components/missions/EffectsPanel.vue'
import MockKits from '../components/learning/MockKits.vue'
import MockForm from '../components/mocks/MockForm.vue'
import Sparkline from '../components/readiness/Sparkline.vue'
import { plural, shortDate } from '../presentation/format'
import { ROUND_LABEL } from '../presentation/language'
import { refreshDerivedData, useMocksStore, useSkillsStore } from '../stores/data'

/** Mock interviews: the next one to take, how recent ones went, repeated weaknesses and a mentor diagnosis. */
const route = useRoute()
const planItemId = typeof route.query.plan_item === 'string' ? Number(route.query.plan_item) : undefined
const mocks = useMocksStore()
const skills = useSkillsStore()
const catalog = ref<{ key: string; component: string }[]>([])
const logging = ref(planItemId !== undefined)
const effects = ref<Effects | null>(null)

const summary = computed(() => mocks.summary.data)
const list = computed(() => mocks.list.data ?? [])
const error = computed(() => mocks.summary.error ?? mocks.list.error)
const hasMocks = computed(() => list.value.length > 0)
const label = (type: string) => ROUND_LABEL[type] ?? type
const nextType = computed(() => summary.value?.by_type.find((t) => t.g6_failing.length > 0) ?? null)
const repeated = computed(() => summary.value?.repeated_weaknesses ?? [])

async function load(): Promise<void> {
  await Promise.all([mocks.summary.refresh(), mocks.list.refresh()])
}

async function recorded(e: Effects | null): Promise<void> {
  effects.value = e
  logging.value = false
  await refreshDerivedData()
  await load()
}

onMounted(async () => {
  await Promise.all([mocks.summary.ensure(), mocks.list.ensure(), skills.ensure()])
  try {
    catalog.value = (await api.get<{ key: string; component: string }[]>('/catalog/skills')).data
  } catch {
    catalog.value = []
  }
})
</script>

<template>
  <div class="page">
    <PageHeader
      eyebrow="Mocks"
      title="Practise the real thing"
      description="Mocks show how your skills hold up under interview pressure."
    >
      <button
        v-if="!logging"
        type="button"
        class="btn btn-primary"
        data-testid="log-mock"
        @click="logging = true"
      >
        <Icon
          name="plus"
          :size="16"
        /> Log a mock
      </button>
    </PageHeader>

    <section
      v-if="logging"
      class="card"
      aria-label="Log a mock"
    >
      <p
        v-if="planItemId"
        class="for-plan"
      >
        <Icon
          name="today"
          :size="14"
        /> Logging the mock from today's plan.
      </p>
      <MockForm
        :plan-item-id="planItemId"
        :catalog="catalog"
        @recorded="recorded"
      />
    </section>
    <EffectsPanel
      v-if="effects"
      :effects="effects"
    />

    <Skeleton
      v-if="!summary && !error"
      height="14rem"
      radius="var(--r-lg)"
    />
    <ErrorState
      v-else-if="error"
      :error="error"
      @retry="load"
    />

    <template v-else-if="summary">
      <EmptyState
        v-if="!hasMocks && !logging"
        icon="mocks"
        title="You haven't completed a mock interview yet."
        body="Master Mentor will use your mock results to identify interview-execution gaps."
      >
        <button
          type="button"
          class="btn btn-primary"
          data-testid="first-mock"
          @click="logging = true"
        >
          Start your first mock
        </button>
      </EmptyState>

      <template v-if="hasMocks || summary.simulation_eligible || nextType">
        <section
          class="next card"
          data-testid="next-mock"
        >
          <p class="eyebrow">
            Next recommended mock
          </p>
          <template v-if="summary.simulation_eligible">
            <h2>A full interview simulation</h2>
            <p class="muted">
              Your skills are ready for a complete run-through.
            </p>
          </template>
          <template v-else-if="nextType">
            <h2>{{ label(nextType.round_type) }} round</h2>
            <p class="muted">
              {{ nextType.rounds_60d }} of {{ nextType.required_60d }} done in the last 60 days.
            </p>
          </template>
          <template v-else>
            <h2>You're up to date.</h2>
            <p class="muted">
              Your mock coverage looks good.
            </p>
          </template>
        </section>

        <section aria-labelledby="mock-types">
          <SectionHeading
            id="mock-types"
            title="How you're scoring"
          />
          <ul
            class="types"
            data-testid="mock-types"
          >
            <li
              v-for="t in summary.by_type"
              :key="t.round_type"
              class="type"
            >
              <p class="tname">
                {{ label(t.round_type) }}
              </p>
              <p
                v-if="t.latest"
                class="tscore tabular"
              >
                {{ t.latest.score }}
              </p>
              <p
                v-else
                class="tscore muted"
              >
                —
              </p>
              <Sparkline
                v-if="t.trend.length > 1"
                :points="t.trend.map((p) => p.score)"
                :label="`${label(t.round_type)} scores over time`"
                :width="120"
                :height="28"
              />
              <p class="muted small">
                {{ t.latest ? `Latest, ${shortDate(t.latest.date)}` : 'No rounds yet' }}
              </p>
            </li>
          </ul>
        </section>

        <MockKits />

        <section
          class="diagnosis card"
          aria-labelledby="mock-diagnosis"
        >
          <h2
            id="mock-diagnosis"
            class="eyebrow"
          >
            Mentor diagnosis
          </h2>
          <template v-if="repeated.length">
            <p class="big">
              Your repeated weakness: <RouterLink :to="{ name: 'skill', params: { key: repeated[0]![0] } }">
                {{ skills.nameOf(repeated[0]![0]) }}
              </RouterLink>
            </p>
            <p class="muted">
              It came up in {{ plural(repeated[0]![1], 'mock round') }}. Practise it before your next mock.
            </p>
            <ul
              v-if="repeated.length > 1"
              class="more"
            >
              <li
                v-for="[skill, n] in repeated.slice(1)"
                :key="skill"
              >
                <RouterLink :to="{ name: 'skill', params: { key: skill } }">
                  {{ skills.nameOf(skill) }}
                </RouterLink>
                <span class="muted"> · {{ plural(n, 'round') }}</span>
              </li>
            </ul>
          </template>
          <p
            v-else-if="hasMocks"
            class="muted"
          >
            No weakness has repeated across mocks yet.
          </p>
          <p
            v-else
            class="muted"
          >
            Log a mock and the diagnosis appears here.
          </p>
        </section>

        <section
          v-if="summary.final_simulations.length"
          aria-labelledby="mock-finals"
        >
          <SectionHeading
            id="mock-finals"
            title="Full simulations"
          />
          <ul
            class="finals card-quiet divided"
            data-testid="finals"
          >
            <li
              v-for="f in summary.final_simulations"
              :key="f.mock_id"
            >
              <span class="fdate">{{ shortDate(f.date) }}</span>
              <StatusPill
                :state="!f.valid ? 'blocked' : f.passed ? 'healthy' : 'medium'"
                :label="!f.valid ? 'Not a full simulation' : f.passed ? 'Passed' : 'Not yet'"
              />
              <span
                v-if="f.failure"
                class="muted small"
              >{{ f.failure }}</span>
            </li>
          </ul>
        </section>

        <section
          v-if="hasMocks"
          aria-labelledby="mock-recent"
        >
          <SectionHeading
            id="mock-recent"
            title="Recent mocks"
          />
          <ul class="recent">
            <li
              v-for="m in list"
              :key="m.id"
              class="mock card-quiet"
            >
              <p class="mtop">
                <strong>{{ shortDate(m.occurred_on) }}</strong>
                <span class="muted small">{{ m.source === 'SELF' ? 'Self-run' : m.source === 'PEER' ? 'With a peer' : 'On a platform' }}<template v-if="m.is_final_simulation"> · full simulation</template></span>
              </p>
              <ul class="rounds">
                <li
                  v-for="r in m.rounds"
                  :key="r.id"
                >
                  <span>{{ label(r.round_type) }}</span>
                  <strong class="tabular">{{ r.round_score }}</strong>
                </li>
              </ul>
            </li>
          </ul>
        </section>
      </template>
    </template>
  </div>
</template>

<style scoped>
.for-plan { display: flex; align-items: center; gap: var(--s-2); margin-bottom: var(--s-4); padding: var(--s-2) var(--s-3); background: var(--accent-soft); color: var(--accent-text); border-radius: var(--r-md); font-size: var(--fs-sm); }
.next { display: grid; gap: var(--s-2); border-left: 4px solid var(--accent); }
.types { display: grid; grid-template-columns: repeat(auto-fill, minmax(11rem, 1fr)); gap: var(--s-3); }
.type { display: grid; gap: var(--s-1); padding: var(--s-4); background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-lg); align-content: start; }
.tname { font-weight: 650; }
.tscore { font-size: var(--fs-2xl); font-weight: 700; letter-spacing: -0.03em; line-height: 1.1; }
.small { font-size: var(--fs-sm); }
.diagnosis { display: grid; gap: var(--s-2); }
.big { font-size: var(--fs-lg); font-weight: 650; letter-spacing: -0.01em; }
.more { display: grid; gap: var(--s-1); font-size: var(--fs-sm); margin-top: var(--s-1); }
.finals li { display: flex; align-items: center; gap: var(--s-3); padding: var(--s-3) var(--s-4); flex-wrap: wrap; }
.fdate { font-weight: 600; min-width: 4.5rem; }
.recent { display: grid; gap: var(--s-3); }
.mtop { display: flex; gap: var(--s-3); align-items: baseline; flex-wrap: wrap; margin-bottom: var(--s-2); }
.rounds { display: flex; flex-wrap: wrap; gap: var(--s-2) var(--s-5); font-size: var(--fs-sm); }
.rounds li { display: flex; gap: var(--s-2); }
</style>
