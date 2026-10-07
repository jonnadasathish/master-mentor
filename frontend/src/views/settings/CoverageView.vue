<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../../api'
import type { CoverageReport, CoverageState } from '../../api/types'
import ErrorState from '../../components/common/ErrorState.vue'
import Icon from '../../components/common/Icon.vue'
import PageHeader from '../../components/common/PageHeader.vue'
import Skeleton from '../../components/common/Skeleton.vue'
import StatusPill from '../../components/common/StatusPill.vue'
import { COVERAGE_LABEL, COVERAGE_TONE, CONTENT_TYPE_LABEL } from '../../presentation/learning'

/**
 * Developer / System: the deterministic content coverage report (MASTER_SPEC_V3 §26). Every canonical skill with
 * what the library offers for it; a required skill must never be a silent content gap.
 */
const report = ref<CoverageReport | null>(null)
const error = ref<unknown>(null)
const state = ref<CoverageState | ''>('')
const requiredOnly = ref(true)
const STATES: CoverageState[] = ['CONTENT_GAP', 'UNMEASURED', 'PARTIAL', 'FULL']

const rows = computed(() =>
  (report.value?.rows ?? []).filter((r) => (!requiredOnly.value || r.required) && (!state.value || r.coverage_state === state.value)),
)
const counts = computed(() => Object.entries(report.value?.content_counts ?? {}).filter(([, n]) => n > 0))

async function load(): Promise<void> {
  error.value = null
  try {
    report.value = (await api.get<CoverageReport>('/learning/coverage')).data
  } catch (caught) {
    error.value = caught
  }
}
onMounted(load)
</script>

<template>
  <div class="page">
    <PageHeader
      eyebrow="Developer / System"
      title="Content coverage"
      description="What the learning library offers per skill. FULL = lesson, concept check, practice, timed practice and recall cards."
    >
      <RouterLink
        :to="{ name: 'developer' }"
        class="btn btn-ghost"
      >
        <Icon
          name="arrow-left"
          :size="16"
        /> Developer
      </RouterLink>
    </PageHeader>
    <Skeleton
      v-if="!report && !error"
      height="16rem"
    />
    <ErrorState
      v-else-if="!report"
      :error="error"
      @retry="load"
    />
    <template v-else>
      <section
        class="summary"
        data-testid="coverage-summary"
      >
        <div
          v-for="s in STATES"
          :key="s"
          class="tile card-quiet"
        >
          <StatusPill
            :state="COVERAGE_TONE[s]"
            :label="COVERAGE_LABEL[s]"
          />
          <p class="big tabular">
            {{ report.summary.required[s] }}
          </p>
          <p class="muted small">
            required skills ({{ report.summary.all[s] }} in all)
          </p>
        </div>
      </section>
      <p class="muted small">
        Library: <template
          v-for="([type, n], i) in counts"
          :key="type"
        >
          {{ i ? ' · ' : '' }}{{ n }} {{ CONTENT_TYPE_LABEL[type as keyof typeof CONTENT_TYPE_LABEL] ?? type }}
        </template>
      </p>
      <div class="filters">
        <label>State
          <select
            v-model="state"
            data-testid="coverage-filter"
          >
            <option value="">All</option>
            <option
              v-for="s in STATES"
              :key="s"
              :value="s"
            >{{ COVERAGE_LABEL[s] }}</option>
          </select>
        </label>
        <label class="check">
          <input
            v-model="requiredOnly"
            type="checkbox"
          > Required skills only
        </label>
      </div>
      <div class="table-wrap">
        <table data-testid="coverage-table">
          <thead>
            <tr>
              <th scope="col">
                Skill
              </th>
              <th scope="col">
                Tier
              </th>
              <th scope="col">
                Learn
              </th>
              <th scope="col">
                Checks
              </th>
              <th scope="col">
                Practice
              </th>
              <th scope="col">
                Timed
              </th>
              <th scope="col">
                Recall
              </th>
              <th scope="col">
                Mock rounds
              </th>
              <th scope="col">
                State
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="r in rows"
              :key="r.skill_key"
            >
              <td>
                <RouterLink :to="{ name: 'skill', params: { key: r.skill_key } }">
                  {{ r.skill_name }}
                </RouterLink>
                <span class="muted mono">{{ r.skill_key }}</span>
              </td>
              <td>{{ r.tier ?? '—' }}</td>
              <td class="tabular">
                {{ r.direct_learning_content }}
              </td>
              <td class="tabular">
                {{ r.concept_checks }}
              </td>
              <td class="tabular">
                {{ r.practice_count }}
              </td>
              <td class="tabular">
                {{ r.timed_practice }}
              </td>
              <td class="tabular">
                {{ r.revision_content }}
              </td>
              <td>{{ r.mock_coverage.join(', ') || '—' }}</td>
              <td>
                <StatusPill
                  :state="COVERAGE_TONE[r.coverage_state]"
                  :label="COVERAGE_LABEL[r.coverage_state]"
                  quiet
                />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<style scoped>
.summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr)); gap: var(--s-3); }
.tile { display: grid; gap: var(--s-1); }
.big { font-size: var(--fs-2xl); font-weight: 700; }
.filters { display: flex; gap: var(--s-4); align-items: end; flex-wrap: wrap; }
.filters label { display: grid; gap: var(--s-1); }
.filters .check { display: flex; align-items: center; gap: var(--s-2); }
.table-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: var(--r-lg); background: var(--surface); }
table { width: 100%; font-size: var(--fs-sm); }
th, td { padding: var(--s-2) var(--s-3); border-bottom: 1px solid var(--border); vertical-align: top; }
th { font-size: var(--fs-xs); text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-3); white-space: nowrap; }
td:first-child { display: grid; min-width: 14rem; }
.mono { font-family: var(--font-mono); font-size: var(--fs-xs); }
.small { font-size: var(--fs-sm); }
</style>
