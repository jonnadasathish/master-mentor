<script setup lang="ts">
import { computed } from 'vue'
import { STATE_LABEL, type SemanticState } from '../../presentation/language'
import Icon from './Icon.vue'

/**
 * A semantic state shown with an icon AND a text label (never colour alone).
 * `state` is one of the semantic states; `label` overrides the default wording.
 */
const props = defineProps<{ state: SemanticState; label?: string; quiet?: boolean }>()

const ICON: Record<SemanticState, string> = {
  critical: 'alert-circle', high: 'alert-triangle', medium: 'minus-circle', low: 'circle', healthy: 'check-circle',
  ready: 'check-circle', due: 'revise', overdue: 'clock', blocked: 'lock', calibration: 'crosshair',
  completed: 'check', parked: 'pause',
}
const text = computed(() => props.label ?? STATE_LABEL[props.state])
</script>

<template>
  <span
    class="pill"
    :class="[`pill-${state}`, { quiet }]"
    :data-state="state"
  >
    <Icon
      :name="ICON[state]"
      :size="13"
    />
    <span>{{ text }}</span>
  </span>
</template>

<style scoped>
.pill {
  display: inline-flex; align-items: center; gap: 0.3rem; padding: 0.15rem 0.55rem 0.15rem 0.45rem;
  border-radius: 999px; border: 1px solid transparent; font-size: var(--fs-xs); font-weight: 650; white-space: nowrap; line-height: 1.3;
}
.pill-critical { background: var(--critical-bg); color: var(--critical-fg); border-color: var(--critical-bd); }
.pill-high { background: var(--high-bg); color: var(--high-fg); border-color: var(--high-bd); }
.pill-medium, .pill-low { background: var(--medium-bg); color: var(--medium-fg); border-color: var(--medium-bd); }
.pill-low { background: var(--surface-2); color: var(--text-2); border-color: var(--border); }
.pill-healthy, .pill-ready, .pill-completed { background: var(--healthy-bg); color: var(--healthy-fg); border-color: var(--healthy-bd); }
.pill-due { background: var(--due-bg); color: var(--due-fg); border-color: var(--due-bd); }
.pill-overdue { background: var(--overdue-bg); color: var(--overdue-fg); border-color: var(--overdue-bd); }
.pill-blocked, .pill-parked { background: var(--blocked-bg); color: var(--blocked-fg); border-color: var(--blocked-bd); }
.pill-calibration { background: var(--calibration-bg); color: var(--calibration-fg); border-color: var(--calibration-bd); }
.quiet { background: transparent; border-color: transparent; padding-left: 0; }
</style>
