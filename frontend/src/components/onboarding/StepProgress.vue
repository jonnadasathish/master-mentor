<script setup lang="ts">
import type { Step } from '../../practice/onboarding'

/** "Step 2 of 6" with a labelled list of steps (the current one is marked for assistive technology). */
defineProps<{ steps: readonly Step[]; current: Step }>()
const LABEL: Record<Step, string> = {
  welcome: 'Welcome', profile: 'You', target: 'Your target', stack: 'Your stack', context: 'Your view',
  calibration: 'Calibration', ready: 'Ready',
}
</script>

<template>
  <nav
    class="progress"
    aria-label="Starting profile steps"
  >
    <p class="count tabular">
      Step {{ steps.indexOf(current) + 1 }} of {{ steps.length }}
    </p>
    <ol>
      <li
        v-for="(s, i) in steps"
        :key="s"
        :aria-current="s === current ? 'step' : undefined"
        :class="{ done: i < steps.indexOf(current), current: s === current }"
      >
        <span
          class="dot"
          aria-hidden="true"
        />
        <span class="label">{{ LABEL[s] }}</span>
      </li>
    </ol>
  </nav>
</template>

<style scoped>
.progress { display: grid; gap: var(--s-2); }
.count { font-size: var(--fs-xs); font-weight: 650; letter-spacing: 0.06em; text-transform: uppercase; color: var(--text-3); }
ol { display: flex; gap: var(--s-2); }
li { flex: 1; display: grid; gap: var(--s-1); }
.dot { height: 0.3rem; border-radius: 999px; background: var(--surface-3); transition: background var(--t-base) var(--ease); }
li.done .dot, li.current .dot { background: var(--accent); }
li.current .dot { box-shadow: 0 0 0 3px var(--accent-soft); }
.label { font-size: var(--fs-xs); color: var(--text-3); }
li.current .label { color: var(--accent-text); font-weight: 650; }
@media (max-width: 767px) { .label { display: none; } }
</style>
