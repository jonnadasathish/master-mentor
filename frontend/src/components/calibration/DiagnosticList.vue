<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import type { BatteryItem, PlanItem } from '../../api/types'
import { formatMinutes } from '../../presentation/format'
import { missionText } from '../../presentation/mission'
import { useSkillsStore } from '../../stores/data'
import StatusPill from '../common/StatusPill.vue'

/** Today's diagnostic items as a compact list (the full cards live on the calibration page). */
const props = defineProps<{ items: PlanItem[]; battery: readonly BatteryItem[] }>()
const skills = useSkillsStore()
type RowState = 'completed' | 'due' | 'calibration'
const rows = computed(() =>
  props.items.map((item) => ({
    id: item.id,
    title: missionText(item, { nameOf: skills.nameOf, componentOf: skills.componentOf, battery: props.battery }).title,
    minutes: item.minutes,
    state: (item.status === 'DONE' ? 'completed' : item.started_at && item.status === 'PENDING' ? 'due' : 'calibration') as RowState,
    label:
      item.status === 'DONE' ? 'Done' : item.status === 'SKIPPED' ? 'Skipped' : item.status === 'DEFERRED' ? 'Tomorrow'
        : item.started_at ? 'In progress' : 'To do',
  })),
)
</script>

<template>
  <ul
    class="list card-quiet divided"
    data-testid="diagnostic-list"
  >
    <li
      v-for="(r, n) in rows"
      :key="r.id"
    >
      <span class="num tabular">{{ String(n + 1).padStart(2, '0') }}</span>
      <span class="title">{{ r.title }}</span>
      <span class="muted tabular">{{ formatMinutes(r.minutes) }}</span>
      <StatusPill
        :state="r.state"
        :label="r.label"
      />
    </li>
    <li class="more">
      <RouterLink :to="{ name: 'calibrate' }">
        Open calibration
      </RouterLink>
    </li>
  </ul>
</template>

<style scoped>
.list li { display: flex; align-items: center; gap: var(--s-3); padding: var(--s-3) var(--s-4); }
.num { color: var(--calibration-fg); font-weight: 700; }
.title { flex: 1; font-weight: 600; min-width: 0; }
.more { justify-content: flex-end; font-size: var(--fs-sm); }
</style>
