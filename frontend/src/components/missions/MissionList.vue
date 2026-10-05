<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import type { HttpClient } from '../../api/client'
import type { BatteryItem, Effects, PlanItem } from '../../api/types'
import { missionText } from '../../presentation/mission'
import { useSkillsStore } from '../../stores/data'
import MissionCard from './MissionCard.vue'

/** Today's missions (at most six at once). Completed missions keep their place so the day reads as a story. */
const props = defineProps<{
  items: PlanItem[]
  client: HttpClient
  battery: readonly BatteryItem[]
  results: Record<number, Effects>
}>()
const emit = defineEmits<{ changed: []; completed: [itemId: number, effects?: Effects] }>()

const MAX_SHOWN = 6
const skills = useSkillsStore()
const showAll = ref(false)
const cards = ref<{ start: () => Promise<void>; phase: string; $el: HTMLElement }[]>([])

const shown = computed(() => (showAll.value ? props.items : props.items.slice(0, MAX_SHOWN)))
const hiddenCount = computed(() => Math.max(0, props.items.length - MAX_SHOWN))
const ctx = computed(() => ({
  nameOf: skills.nameOf,
  componentOf: skills.componentOf,
  battery: props.battery,
}))

/**
 * "Continue": resumes the mission already in progress, otherwise starts the first one not yet started. Finished,
 * skipped and deferred missions are never restarted. Returns what happened so the caller can explain "nothing left".
 */
async function startNext(): Promise<'resumed' | 'started' | 'none'> {
  const running = cards.value.find((c) => c?.phase === 'in-progress')
  const next = running ?? cards.value.find((c) => c?.phase === 'not-started')
  if (!next) return 'none'
  if (!running) await next.start()
  await nextTick()
  if (typeof next.$el?.scrollIntoView === 'function') next.$el.scrollIntoView({ block: 'center', behavior: 'smooth' })
  return running ? 'resumed' : 'started'
}
defineExpose({ startNext })
</script>

<template>
  <div>
    <ol
      class="missions"
      data-testid="plan-items"
    >
      <MissionCard
        v-for="(item, n) in shown"
        :key="item.id"
        :ref="(el) => { const i = shown.indexOf(item); if (el) cards[i] = el as never }"
        :number="n + 1"
        :item="item"
        :client="client"
        :text="missionText(item, ctx)"
        :result="results[item.id] ?? null"
        @changed="emit('changed')"
        @completed="(effects) => emit('completed', item.id, effects)"
      />
    </ol>
    <button
      v-if="hiddenCount && !showAll"
      type="button"
      class="btn btn-ghost show-more"
      @click="showAll = true"
    >
      Show {{ hiddenCount }} more
    </button>
  </div>
</template>

<style scoped>
.missions { display: grid; gap: var(--s-3); }
.show-more { margin-top: var(--s-3); }
</style>
