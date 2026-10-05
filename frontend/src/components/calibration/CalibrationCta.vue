<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import type { Baseline } from '../../api/types'
import Icon from '../common/Icon.vue'

/**
 * Where calibration stands and the one thing to do next. Four states, from the server's `phase`.
 * On Today the button leads to the calibration page; on the page itself it starts the next task.
 */
const props = defineProps<{ baseline: Baseline; hub?: boolean }>()
defineEmits<{ continue: [] }>()

const copy = computed(() => {
  const b = props.baseline
  switch (b.phase) {
    case 'NOT_STARTED':
      return {
        eyebrow: 'Calibrate your skills',
        title: "Let's measure where you are.",
        body: 'A few short tasks show Master Mentor what you already know. Nothing is graded against you.',
        action: 'Start calibration',
      }
    case 'ENOUGH_MEASURED':
      return {
        eyebrow: 'Calibration',
        title: 'We have enough evidence to build your initial roadmap.',
        body: "You can look at your personal roadmap now. The remaining assessments will sharpen it, so it's worth finishing them.",
        action: 'Continue calibration',
      }
    case 'COMPLETE':
      return {
        eyebrow: 'Calibration',
        title: 'Baseline complete.',
        body: 'Every baseline assessment is done. Your plan now follows what was measured.',
        action: '',
      }
    default:
      return {
        eyebrow: 'Calibrating your skills',
        title: `We've measured ${b.assessed_required} of ${b.required} required skills.`,
        body: 'Your personalized plan will appear once the baseline has enough evidence.',
        action: 'Continue calibration',
      }
  }
})
const showRoadmap = computed(() => props.baseline.phase === 'ENOUGH_MEASURED' || props.baseline.phase === 'COMPLETE')
</script>

<template>
  <section
    class="cta"
    :class="`phase-${baseline.phase.toLowerCase()}`"
    aria-labelledby="calibration-title"
    data-testid="calibration-cta"
    :data-phase="baseline.phase"
  >
    <p class="eyebrow">
      <Icon
        name="crosshair"
        :size="14"
      /> {{ copy.eyebrow }}
    </p>
    <h2
      id="calibration-title"
      class="title"
    >
      {{ copy.title }}
    </h2>
    <p class="body">
      {{ copy.body }}
    </p>
    <div class="actions">
      <RouterLink
        v-if="showRoadmap"
        :to="{ name: 'roadmap' }"
        class="btn btn-primary btn-lg"
        data-testid="view-roadmap"
      >
        <Icon
          name="roadmap"
          :size="16"
        /> View my roadmap
      </RouterLink>
      <template v-if="copy.action">
        <button
          v-if="hub"
          type="button"
          class="btn btn-lg"
          :class="showRoadmap ? '' : 'btn-primary'"
          data-testid="continue-calibration"
          @click="$emit('continue')"
        >
          <Icon
            name="play"
            :size="14"
          /> {{ copy.action }}
        </button>
        <RouterLink
          v-else
          :to="{ name: 'calibrate', query: { start: '1' } }"
          class="btn btn-lg"
          :class="showRoadmap ? '' : 'btn-primary'"
          data-testid="continue-calibration"
        >
          <Icon
            name="play"
            :size="14"
          /> {{ copy.action }}
        </RouterLink>
      </template>
    </div>
  </section>
</template>

<style scoped>
.cta { display: grid; gap: var(--s-3); padding: var(--s-6); border-radius: var(--r-xl); background: linear-gradient(135deg, var(--calibration-bg), var(--surface) 70%); border: 1px solid var(--calibration-bd); }
.phase-complete { background: linear-gradient(135deg, var(--healthy-bg), var(--surface) 70%); border-color: var(--healthy-bd); }
.eyebrow { display: flex; align-items: center; gap: var(--s-2); margin: 0; color: var(--calibration-fg); font-size: var(--fs-xs); font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; }
.phase-complete .eyebrow { color: var(--healthy-fg); }
.title { font-size: var(--fs-2xl); letter-spacing: -0.025em; text-wrap: balance; }
.body { color: var(--text-2); max-width: 38rem; font-size: var(--fs-md); }
.actions { display: flex; gap: var(--s-3); flex-wrap: wrap; margin-top: var(--s-2); }
@media (max-width: 767px) {
  .cta { padding: var(--s-5) var(--s-4); }
  .title { font-size: var(--fs-xl); }
  .actions .btn { flex: 1 1 100%; }
}
</style>
