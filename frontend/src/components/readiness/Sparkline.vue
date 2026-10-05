<script setup lang="ts">
import { computed } from 'vue'

/** A minimal trend line. Scales the server's values into the box; shows nothing it was not given. */
const props = withDefaults(defineProps<{ points: number[]; label: string; width?: number; height?: number }>(), {
  width: 160, height: 36,
})
const path = computed(() => {
  const values = props.points
  if (values.length < 2) return ''
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = max - min || 1
  const pad = 3
  return values
    .map((v, i) => {
      const x = pad + (i / (values.length - 1)) * (props.width - pad * 2)
      const y = props.height - pad - ((v - min) / span) * (props.height - pad * 2)
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)} ${y.toFixed(1)}`
    })
    .join(' ')
})
</script>

<template>
  <svg
    :width="width"
    :height="height"
    :viewBox="`0 0 ${width} ${height}`"
    role="img"
    :aria-label="label"
  >
    <path
      :d="path"
      fill="none"
      stroke="var(--accent)"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
  </svg>
</template>
