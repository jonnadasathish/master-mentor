<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ApiError } from '../../api/client'
import type { PlanItem, PlanLearning } from '../../api/types'
import { openSession } from '../../learning/session'
import { formatMinutes } from '../../presentation/format'
import type { MissionText } from '../../presentation/mission'
import Icon from '../common/Icon.vue'

/**
 * Today's learning mission on a hybrid day (enough measured, calibration still open): the mentor's top gap and the
 * existing learning session that fills it. Wording and numbers are the server's; this only renders and opens the session.
 */
const props = defineProps<{ item: PlanItem; learning: PlanLearning; text: MissionText; why: string[] }>()
const router = useRouter()
const opening = ref(false)
const error = ref('')
const resuming = computed(() => props.learning.session_id !== null)

async function start(): Promise<void> {
  if (!props.item.skill) return
  opening.value = true
  error.value = ''
  try {
    if (props.learning.session_id !== null) await router.push({ name: 'session', params: { id: props.learning.session_id } })
    else await openSession(router, { skill: props.item.skill, stage: props.learning.stage, plan_item_id: props.item.id })
  } catch (caught) {
    error.value = caught instanceof ApiError ? caught.message : String(caught)
  } finally {
    opening.value = false
  }
}
</script>

<template>
  <section
    class="learning card"
    aria-labelledby="learning-title"
    data-testid="learning-mission"
  >
    <p class="eyebrow">
      <Icon
        name="play"
        :size="14"
      /> Today's learning
    </p>
    <p class="label">
      Today's focus
    </p>
    <h2
      id="learning-title"
      class="focus"
      data-testid="learning-focus"
    >
      {{ text.skillLabel ?? text.title }}
    </h2>
    <div
      v-if="why.length"
      data-testid="learning-why"
    >
      <p class="label">
        Why this is today's focus
      </p>
      <ul class="why">
        <li
          v-for="w in why"
          :key="w"
        >
          {{ w }}
        </li>
      </ul>
    </div>
    <p
      class="estimate tabular"
      data-testid="learning-minutes"
    >
      Estimated time: <strong>{{ formatMinutes(learning.minutes) }}</strong>
    </p>
    <div>
      <p class="label">
        Learning path
      </p>
      <ol
        class="path"
        data-testid="learning-path"
      >
        <li
          v-for="s in learning.steps"
          :key="s.position"
        >
          <span>{{ s.title }}</span>
          <span class="muted tabular">{{ formatMinutes(s.minutes) }}</span>
        </li>
      </ol>
    </div>
    <div class="actions">
      <button
        type="button"
        class="btn btn-primary btn-lg"
        data-testid="start-learning"
        :disabled="opening"
        @click="start"
      >
        <Icon
          name="play"
          :size="14"
        /> {{ resuming ? "Continue today's learning" : "Start today's learning" }}
      </button>
    </div>
    <p
      v-if="error"
      role="alert"
      class="error"
    >
      {{ error }}
    </p>
  </section>
</template>

<style scoped>
.learning { display: grid; gap: var(--s-3); padding: var(--s-5); min-width: 0; border-color: var(--accent, var(--border-strong)); }
.eyebrow { display: flex; align-items: center; gap: var(--s-2); font-weight: 700; color: var(--accent-fg, var(--text-2)); }
.label { font-size: var(--fs-sm); color: var(--text-2); }
.focus { overflow-wrap: anywhere; }
.why { display: grid; gap: var(--s-1); padding-left: var(--s-4); list-style: disc; }
.path { display: grid; gap: var(--s-1); padding-left: var(--s-5); list-style: decimal; }
.path li { padding-left: var(--s-1); }
.path li > span:first-child { margin-right: var(--s-2); overflow-wrap: anywhere; }
.actions { display: flex; flex-wrap: wrap; gap: var(--s-2); }
.error { color: var(--critical-fg, inherit); }
</style>
