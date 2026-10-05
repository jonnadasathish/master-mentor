<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'

/** An interview-style timer. It only measures; the time submitted is what the learner records (D-053). */
const props = defineProps<{ limitSeconds: number; now?: () => number }>()
const emit = defineEmits<{ stopped: [seconds: number]; started: [] }>()
const clock = () => (props.now ? props.now() : Date.now())
const startedAt = ref<number | null>(null)
const stoppedSeconds = ref<number | null>(null)
const tick = ref(0)
let timer: ReturnType<typeof setInterval> | undefined

const elapsed = computed(() => {
  void tick.value
  if (stoppedSeconds.value !== null) return stoppedSeconds.value
  return startedAt.value === null ? 0 : Math.max(0, Math.floor((clock() - startedAt.value) / 1000))
})
const mmss = (s: number) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
const over = computed(() => elapsed.value > props.limitSeconds)

function start(): void {
  startedAt.value = clock()
  stoppedSeconds.value = null
  timer = setInterval(() => (tick.value += 1), 1000)
  emit('started')
}
function stop(): void {
  if (timer) clearInterval(timer)
  stoppedSeconds.value = elapsed.value
  emit('stopped', stoppedSeconds.value)
}
onBeforeUnmount(() => timer && clearInterval(timer))
</script>

<template>
  <div
    class="timer"
    :class="{ over }"
    data-testid="practice-timer"
  >
    <span
      class="time tabular"
      role="timer"
      :aria-label="`Elapsed ${mmss(elapsed)} of ${mmss(limitSeconds)}`"
    >{{ mmss(elapsed) }} / {{ mmss(limitSeconds) }}</span>
    <button
      v-if="startedAt === null"
      type="button"
      class="btn btn-sm btn-primary"
      data-testid="start-timer"
      @click="start"
    >
      Start the timer
    </button>
    <button
      v-else-if="stoppedSeconds === null"
      type="button"
      class="btn btn-sm"
      data-testid="stop-timer"
      @click="stop"
    >
      Stop
    </button>
    <span
      v-else
      class="muted small"
    >{{ over ? 'Over the limit: recorded as untimed practice.' : 'Within the limit.' }}</span>
  </div>
</template>

<style scoped>
.timer { display: flex; align-items: center; gap: var(--s-3); flex-wrap: wrap; padding: var(--s-3) var(--s-4); border: 1px solid var(--border); border-radius: var(--r-md); background: var(--surface); }
.time { font-family: var(--font-mono); font-size: var(--fs-lg); font-weight: 650; color: var(--accent-text); }
.over .time { color: var(--overdue-fg); }
.small { font-size: var(--fs-sm); }
</style>
