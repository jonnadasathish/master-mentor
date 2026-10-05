<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { api } from '../../api'
import type { Meta, SkillStateDetail } from '../../api/types'
import { useErrorStore } from '../../stores/errors'

const route = useRoute()
const skill = ref<SkillStateDetail | null>(null)
const meta = ref<Meta>({})
const errorStore = useErrorStore()

async function load(): Promise<void> {
  try {
    const envelope = await api.get<SkillStateDetail>(`/skills/${encodeURIComponent(String(route.params.key))}`)
    skill.value = envelope.data
    meta.value = envelope.meta
  } catch (caught) {
    errorStore.report(caught, 'skill')
  }
}

function sourceLink(row: SkillStateDetail['evidence'][number]): string | null {
  return row.source_type === 'ATTEMPT' ? `/log/attempts/${row.source_id}` : null
}

onMounted(load)
watch(() => route.params.key, load)
</script>

<template>
  <section v-if="skill">
    <p>
      <RouterLink :to="{ name: 'skills' }">
        ← Skills
      </RouterLink>
    </p>
    <h1 data-testid="skill-name">
      {{ skill.name }}
    </h1>
    <p class="meta">
      {{ skill.key }} · {{ skill.component }} · {{ skill.tier ?? 'no tier' }} · target {{ skill.target_score ?? '—' }}
      · as of {{ meta.as_of_date }} (run {{ meta.run_id }}, ruleset {{ meta.ruleset_version }})
    </p>
    <dl
      class="state"
      data-testid="skill-state"
    >
      <div><dt>Score</dt><dd>{{ skill.state.score ?? 'unassessed' }}</dd></div>
      <div><dt>Effective</dt><dd>{{ skill.state.effective_score ?? '—' }}</dd></div>
      <div><dt>Level</dt><dd>{{ skill.state.level === null ? '—' : `L${skill.state.level}` }}</dd></div>
      <div><dt>Confidence</dt><dd>{{ skill.state.confidence }}</dd></div>
      <div><dt>Peak</dt><dd>{{ skill.state.peak_score ?? '—' }}</dd></div>
      <div><dt>Evidence (120 d)</dt><dd>{{ skill.state.evidence_count }} rows / {{ skill.state.distinct_sources }} sources</dd></div>
    </dl>
    <p
      v-if="skill.state.declared_unknown"
      class="note"
    >
      You declared this skill unknown in the familiarity sweep: it counts as measured at 0 until real evidence exists.
    </p>
    <p
      v-if="skill.state.reality_capped"
      class="note"
    >
      Capped by a recent mock interview result below 70.
    </p>

    <section
      v-if="skill.gap"
      class="gap"
      data-testid="skill-gap"
    >
      <h2>Gap: {{ skill.gap.status.toLowerCase() }} (priority {{ skill.gap.priority }}, rank {{ skill.gap.rank }})</h2>
      <p v-if="skill.gap.primary_gap_type">
        {{ skill.gap.primary_gap_type.toLowerCase().replace('_', ' ') }} → next stage
        <strong>{{ skill.gap.focus_stage?.toLowerCase() }}</strong>
        <template v-if="skill.gap.focus_skill && skill.gap.focus_skill !== skill.key">
          on <RouterLink :to="{ name: 'skill', params: { key: skill.gap.focus_skill } }">
            {{ skill.gap.focus_skill }}
          </RouterLink>
        </template>
      </p>
      <p v-if="skill.gap.parked_reason">
        Parked ({{ skill.gap.parked_reason.toLowerCase().replace('_', ' ') }}): no missions until the deadline passes; it still counts in readiness.
      </p>
      <p class="reasons">
        <span
          v-for="r in skill.gap.reason_codes"
          :key="r"
          class="chip"
        >{{ r.toLowerCase() }}</span>
      </p>
    </section>

    <h2>Prerequisites</h2>
    <ul v-if="skill.prerequisites.length">
      <li
        v-for="p in skill.prerequisites"
        :key="p.skill"
      >
        <RouterLink :to="{ name: 'skill', params: { key: p.skill } }">
          {{ p.skill }}
        </RouterLink>
        needs {{ p.min_score }}, effective {{ p.effective_score ?? 'unassessed' }}
        {{ p.satisfied ? '✓' : '✗' }}
      </li>
    </ul>
    <p v-else>
      None.
    </p>

    <section
      v-if="skill.focus"
      data-testid="skill-focus"
    >
      <h2>Recommended focus</h2>
      <p>
        Stage <strong>{{ skill.focus.stage.toLowerCase() }}</strong>
        <template v-if="skill.focus.template_key">
          · mission {{ skill.focus.template_key }} ({{ skill.focus.minutes ?? '—' }} min, record
          {{ skill.focus.observation_kind?.toLowerCase().replace('_', ' ') }}) · done when: {{ skill.focus.pass_rule }}
        </template>
      </p>
    </section>

    <h2>Downstream skills</h2>
    <p v-if="!skill.dependents.length">
      None.
    </p>
    <p v-else>
      <RouterLink
        v-for="d in skill.dependents"
        :key="d"
        :to="{ name: 'skill', params: { key: d } }"
        class="dep"
      >
        {{ d }}
      </RouterLink>
    </p>
    <p v-if="skill.milestone">
      Milestone: {{ skill.milestone.key }} {{ skill.milestone.name }} ({{ skill.milestone.track.replace('_', ' ') }})
    </p>

    <h2>Revision items</h2>
    <ul
      v-if="skill.revision_items.length"
      data-testid="skill-revisions"
    >
      <li
        v-for="r in skill.revision_items"
        :key="r.item_key"
      >
        {{ r.item_key }} · {{ r.state.toLowerCase() }} · index {{ r.interval_index }}<template v-if="r.due_date">
          · due {{ r.due_date }}
        </template><template v-if="r.lapses">
          · lapses {{ r.lapses }}
        </template>
      </li>
    </ul>
    <p v-else>
      None yet.
    </p>

    <h2>Evidence (newest first)</h2>
    <table
      v-if="skill.evidence.length"
      data-testid="evidence-table"
    >
      <thead>
        <tr>
          <th>Date</th><th>Source</th><th>Rule</th><th>Level</th><th>Points</th><th>Used for</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="e in skill.evidence"
          :key="`${e.source_type}-${e.source_id}`"
        >
          <td>{{ e.observed_on }}</td>
          <td>
            <RouterLink
              v-if="sourceLink(e)"
              :to="sourceLink(e)!"
            >
              {{ e.source_type.toLowerCase() }} #{{ e.source_id }}
            </RouterLink>
            <span v-else>{{ (e.kind ?? e.source_type).toLowerCase() }} #{{ e.source_id }}</span>
            <small>{{ e.source_key }}</small>
          </td>
          <td>{{ e.rule.toLowerCase() }}</td>
          <td>L{{ e.level }}</td>
          <td>{{ e.outcome_points ?? '—' }}</td>
          <td>{{ [e.qualifying ? 'level' : '', e.considered ? 'score' : '', e.is_scoring ? '' : 'not scoring'].filter(Boolean).join(', ') || '—' }}</td>
        </tr>
      </tbody>
    </table>
    <p v-else>
      No evidence yet.
    </p>
  </section>
</template>

<style scoped>
.meta { color: #555; font-size: 0.85rem; }
.state { display: flex; flex-wrap: wrap; gap: 1.5rem; }
.state dt { font-size: 0.75rem; color: #666; }
.state dd { margin: 0; font-size: 1.2rem; }
.gap { border-left: 4px solid #b35c00; padding-left: 0.75rem; }
.dep { margin-right: 0.6rem; }
.chip { display: inline-block; margin: 0.1rem; border-radius: 999px; border: 1px solid #bbb; background: #f6f6f8; padding: 0.05rem 0.5rem; font-size: 0.8rem; }
.note { background: #fff7e0; padding: 0.4rem 0.6rem; border-radius: 6px; }
table { border-collapse: collapse; width: 100%; font-size: 0.9rem; }
th, td { text-align: left; padding: 0.3rem 0.5rem; border-bottom: 1px solid #eee; }
td small { display: block; color: #777; }
</style>
