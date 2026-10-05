<script setup lang="ts">
import { computed } from 'vue'
import { shortDate } from '../../presentation/format'

/** A calm line chart for a 0-100 score over dates. It plots the server's values; the axis is fixed 0-100. */
const props = defineProps<{ points: { date: string; value: number }[]; label: string }>()
const W = 600
const H = 150
const PAD = { l: 8, r: 8, t: 10, b: 22 }

const coords = computed(() => {
  const n = props.points.length
  return props.points.map((p, i) => ({
    x: PAD.l + (n === 1 ? (W - PAD.l - PAD.r) / 2 : (i / (n - 1)) * (W - PAD.l - PAD.r)),
    y: PAD.t + (1 - Math.max(0, Math.min(100, p.value)) / 100) * (H - PAD.t - PAD.b),
    ...p,
  }))
})
const line = computed(() => coords.value.map((c, i) => `${i === 0 ? 'M' : 'L'}${c.x.toFixed(1)} ${c.y.toFixed(1)}`).join(' '))
const area = computed(() => {
  if (coords.value.length < 2) return ''
  const first = coords.value[0]!
  const last = coords.value[coords.value.length - 1]!
  return `${line.value} L${last.x.toFixed(1)} ${H - PAD.b} L${first.x.toFixed(1)} ${H - PAD.b} Z`
})
const last = computed(() => coords.value[coords.value.length - 1] ?? null)
</script>

<template>
  <figure class="chart">
    <svg
      :viewBox="`0 0 ${W} ${H}`"
      role="img"
      :aria-label="label"
      preserveAspectRatio="none"
    >
      <line
        v-for="g in [0, 50, 100]"
        :key="g"
        :x1="PAD.l"
        :x2="W - PAD.r"
        :y1="PAD.t + (1 - g / 100) * (H - PAD.t - PAD.b)"
        :y2="PAD.t + (1 - g / 100) * (H - PAD.t - PAD.b)"
        stroke="var(--border)"
        stroke-dasharray="3 4"
        vector-effect="non-scaling-stroke"
      />
      <path
        v-if="area"
        :d="area"
        fill="var(--accent-soft)"
      />
      <path
        :d="line"
        fill="none"
        stroke="var(--accent)"
        stroke-width="2.5"
        stroke-linecap="round"
        stroke-linejoin="round"
        vector-effect="non-scaling-stroke"
      />
    </svg>
    <figcaption>
      <span>{{ shortDate(points[0]?.date) }}</span>
      <strong
        v-if="last"
        class="tabular"
      >{{ last.value }}</strong>
      <span>{{ shortDate(points[points.length - 1]?.date) }}</span>
    </figcaption>
  </figure>
</template>

<style scoped>
.chart { margin: 0; display: grid; gap: var(--s-1); }
svg { width: 100%; height: 9rem; display: block; }
figcaption { display: flex; justify-content: space-between; align-items: baseline; font-size: var(--fs-xs); color: var(--text-3); }
figcaption strong { color: var(--text); font-size: var(--fs-md); }
</style>
