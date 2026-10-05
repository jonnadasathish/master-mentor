<script setup lang="ts">
/** Loading placeholder block (shimmer). Compose several to mirror the shape of the content that is coming. */
withDefaults(defineProps<{ height?: string; width?: string; radius?: string }>(), {
  height: '1rem', width: '100%', radius: 'var(--r-sm)',
})
</script>

<template>
  <div
    class="skeleton"
    aria-hidden="true"
    :style="{ height, width, borderRadius: radius }"
  />
</template>

<style scoped>
.skeleton {
  background: linear-gradient(90deg, var(--surface-3) 25%, var(--surface-2) 50%, var(--surface-3) 75%);
  background-size: 200% 100%; animation: shimmer 1.4s linear infinite;
}
@keyframes shimmer { to { background-position: -200% 0; } }
</style>
