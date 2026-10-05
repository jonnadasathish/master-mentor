<script setup lang="ts">
import { computed } from 'vue'

/** Gap/readiness status with an icon AND a text label (never color alone, UI_SPEC §1). */
const props = defineProps<{ status: string; priority?: number | null }>()
const ICONS: Record<string, string> = {
  CRITICAL: '⛔', HIGH: '▲', MEDIUM: '●', LOW: '○', NONE: '✓', BLOCKED: '🔒', PARKED: '⏸', UNASSESSED: '?',
}
const icon = computed(() => ICONS[props.status] ?? '•')
</script>

<template>
  <span
    class="badge"
    :class="`s-${status.toLowerCase()}`"
  ><span aria-hidden="true">{{ icon }}</span> {{ status.toLowerCase() + (priority != null ? ` ${priority}` : '') }}</span>
</template>

<style scoped>
.badge { display: inline-block; border-radius: 999px; padding: 0 0.5rem; font-size: 0.8rem; border: 1px solid #ccc; white-space: nowrap; }
.s-critical { background: #fde8e8; border-color: #d33; }
.s-high { background: #fff1d6; border-color: #c77700; }
.s-medium { background: #fffbe0; }
.s-blocked, .s-parked { background: #eee; }
.s-none { background: #eaf6ea; }
</style>
