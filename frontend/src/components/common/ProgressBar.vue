<script setup lang="ts">
import { computed } from 'vue'
import { barPercent } from '../../presentation/format'

/** A restrained progress bar. The numbers come from the server; this only converts them to a width. */
const props = withDefaults(
  defineProps<{
    value: number | null
    max: number | null
    label: string
    tone?: 'accent' | 'critical' | 'high' | 'medium' | 'healthy' | 'calibration' | 'neutral'
    size?: 'sm' | 'md' | 'lg'
    marker?: number | null
  }>(),
  { tone: 'accent', size: 'md', marker: null },
)
const width = computed(() => barPercent(props.value, props.max))
const markerLeft = computed(() => (props.marker == null ? null : barPercent(props.marker, props.max)))
</script>

<template>
  <div
    class="bar"
    :class="[`bar-${tone}`, `bar-${size}`]"
    role="progressbar"
    :aria-label="label"
    :aria-valuemin="0"
    :aria-valuemax="max ?? 0"
    :aria-valuenow="value ?? 0"
  >
    <div
      class="fill"
      :style="{ width: `${width}%` }"
    />
    <div
      v-if="markerLeft !== null"
      class="marker"
      :style="{ left: `${markerLeft}%` }"
      aria-hidden="true"
    />
  </div>
</template>

<style scoped>
.bar { position: relative; width: 100%; background: var(--surface-3); border-radius: 999px; overflow: hidden; }
.bar-sm { height: 0.3rem; }
.bar-md { height: 0.5rem; }
.bar-lg { height: 0.7rem; }
.fill { height: 100%; border-radius: 999px; background: var(--accent); transition: width 600ms var(--ease); }
.bar-critical .fill { background: var(--critical-fg); }
.bar-high .fill { background: #d9650f; }
.bar-medium .fill { background: #b9860c; }
.bar-healthy .fill { background: #1a9250; }
.bar-calibration .fill { background: #1a8ba3; }
.bar-neutral .fill { background: var(--text-3); }
.marker { position: absolute; top: 0; bottom: 0; width: 2px; background: var(--text); opacity: 0.45; }
</style>
