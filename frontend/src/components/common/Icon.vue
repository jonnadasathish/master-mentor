<script setup lang="ts">
import { computed } from 'vue'

/** Small inline stroke icon set (24x24). Decorative by default; pass `label` to expose it to screen readers. */
const props = withDefaults(defineProps<{ name: string; size?: number; label?: string }>(), { size: 18, label: undefined })

const PATHS: Record<string, string[]> = {
  today: ['M12 2v2', 'M12 20v2', 'M4.93 4.93l1.41 1.41', 'M17.66 17.66l1.41 1.41', 'M2 12h2', 'M20 12h2', 'M6.34 17.66l-1.41 1.41', 'M19.07 4.93l-1.41 1.41', 'M12 8a4 4 0 100 8 4 4 0 000-8z'],
  prepare: ['M2 4h6a4 4 0 014 4v13a3 3 0 00-3-3H2z', 'M22 4h-6a4 4 0 00-4 4v13a3 3 0 013-3h7z'],
  revise: ['M17 1l4 4-4 4', 'M3 11V9a4 4 0 014-4h14', 'M7 23l-4-4 4-4', 'M21 13v2a4 4 0 01-4 4H3'],
  mocks: ['M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z', 'M19 10v2a7 7 0 01-14 0v-2', 'M12 19v4', 'M8 23h8'],
  progress: ['M23 6l-9.5 9.5-5-5L1 18', 'M17 6h6v6'],
  roadmap: ['M1 6v16l7-4 8 4 7-4V2l-7 4-8-4-7 4z', 'M8 2v16', 'M16 6v16'],
  settings: ['M4 21v-7', 'M4 10V3', 'M12 21v-9', 'M12 8V3', 'M20 21v-5', 'M20 12V3', 'M1 14h6', 'M9 8h6', 'M17 16h6'],
  check: ['M20 6L9 17l-5-5'],
  'check-circle': ['M22 11.08V12a10 10 0 11-5.93-9.14', 'M22 4L12 14.01l-3-3'],
  clock: ['M12 2a10 10 0 100 20 10 10 0 000-20z', 'M12 6v6l4 2'],
  'alert-triangle': ['M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z', 'M12 9v4', 'M12 17h.01'],
  'alert-circle': ['M12 2a10 10 0 100 20 10 10 0 000-20z', 'M12 8v4', 'M12 16h.01'],
  'minus-circle': ['M12 2a10 10 0 100 20 10 10 0 000-20z', 'M8 12h8'],
  circle: ['M12 2a10 10 0 100 20 10 10 0 000-20z'],
  lock: ['M5 11h14a2 2 0 012 2v7a2 2 0 01-2 2H5a2 2 0 01-2-2v-7a2 2 0 012-2z', 'M7 11V7a5 5 0 0110 0v4'],
  play: ['M6 3l14 9-14 9z'],
  'arrow-right': ['M5 12h14', 'M12 5l7 7-7 7'],
  'arrow-left': ['M19 12H5', 'M12 19l-7-7 7-7'],
  'chevron-right': ['M9 18l6-6-6-6'],
  'chevron-down': ['M6 9l6 6 6-6'],
  plus: ['M12 5v14', 'M5 12h14'],
  x: ['M18 6L6 18', 'M6 6l12 12'],
  code: ['M16 18l6-6-6-6', 'M8 6l-6 6 6 6'],
  database: ['M12 2c4.97 0 9 1.34 9 3s-4.03 3-9 3-9-1.34-9-3 4.03-3 9-3z', 'M21 12c0 1.66-4.03 3-9 3s-9-1.34-9-3', 'M3 5v14c0 1.66 4.03 3 9 3s9-1.34 9-3V5'],
  layers: ['M12 2L2 7l10 5 10-5-10-5z', 'M2 17l10 5 10-5', 'M2 12l10 5 10-5'],
  box: ['M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z', 'M3.27 6.96L12 12.01l8.73-5.05', 'M12 22.08V12'],
  message: ['M21 11.5a8.38 8.38 0 01-.9 3.8 8.5 8.5 0 01-7.6 4.7 8.38 8.38 0 01-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 01-.9-3.8 8.5 8.5 0 014.7-7.6 8.38 8.38 0 013.8-.9h.5a8.48 8.48 0 018 8v.5z'],
  target: ['M12 2a10 10 0 100 20 10 10 0 000-20z', 'M12 6a6 6 0 100 12 6 6 0 000-12z', 'M12 10a2 2 0 100 4 2 2 0 000-4z'],
  crosshair: ['M12 2a10 10 0 100 20 10 10 0 000-20z', 'M22 12h-4', 'M6 12H2', 'M12 6V2', 'M12 22v-4'],
  flag: ['M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z', 'M4 22v-7'],
  skip: ['M5 4l10 8-10 8z', 'M19 5v14'],
  more: ['M12 11a1 1 0 100 2 1 1 0 000-2z', 'M19 11a1 1 0 100 2 1 1 0 000-2z', 'M5 11a1 1 0 100 2 1 1 0 000-2z'],
  zap: ['M13 2L3 14h9l-1 8 10-12h-9l1-8z'],
  refresh: ['M23 4v6h-6', 'M1 20v-6h6', 'M3.51 9a9 9 0 0114.85-3.36L23 10', 'M1 14l4.64 4.36A9 9 0 0020.49 15'],
  calendar: ['M5 4h14a2 2 0 012 2v14a2 2 0 01-2 2H5a2 2 0 01-2-2V6a2 2 0 012-2z', 'M16 2v4', 'M8 2v4', 'M3 10h18'],
  list: ['M8 6h13', 'M8 12h13', 'M8 18h13', 'M3 6h.01', 'M3 12h.01', 'M3 18h.01'],
  search: ['M11 3a8 8 0 100 16 8 8 0 000-16z', 'M21 21l-4.35-4.35'],
  info: ['M12 2a10 10 0 100 20 10 10 0 000-20z', 'M12 16v-4', 'M12 8h.01'],
  help: ['M12 2a10 10 0 100 20 10 10 0 000-20z', 'M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3', 'M12 17h.01'],
  pause: ['M6 4h4v16H6z', 'M14 4h4v16h-4z'],
  trending: ['M23 6l-9.5 9.5-5-5L1 18'],
  book: ['M4 19.5A2.5 2.5 0 016.5 17H20', 'M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z'],
  external: ['M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6', 'M15 3h6v6', 'M10 14L21 3'],
  sparkle: ['M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9L12 3z'],
}

const paths = computed(() => PATHS[props.name] ?? PATHS.circle!)
const filled = computed(() => props.name === 'play')
</script>

<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    :fill="filled ? 'currentColor' : 'none'"
    stroke="currentColor"
    stroke-width="1.8"
    stroke-linecap="round"
    stroke-linejoin="round"
    :aria-hidden="label ? undefined : 'true'"
    :role="label ? 'img' : undefined"
    :aria-label="label"
    focusable="false"
    class="mm-icon"
  >
    <path
      v-for="(d, i) in paths"
      :key="i"
      :d="d"
    />
  </svg>
</template>

<style scoped>
.mm-icon { flex: none; }
</style>
