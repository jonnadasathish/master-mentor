<script setup lang="ts">
import Icon from './Icon.vue'

/** Friendly empty state: what is missing, why it matters, and the one thing to do about it. */
defineProps<{ icon?: string; title: string; body?: string }>()
</script>

<template>
  <div
    class="empty"
    data-testid="empty-state"
  >
    <span
      class="badge"
      aria-hidden="true"
    ><Icon
      :name="icon ?? 'sparkle'"
      :size="20"
    /></span>
    <p class="title">
      {{ title }}
    </p>
    <p
      v-if="body"
      class="muted"
    >
      {{ body }}
    </p>
    <div
      v-if="$slots.default"
      class="actions"
    >
      <slot />
    </div>
  </div>
</template>

<style scoped>
.empty {
  display: grid; justify-items: center; gap: var(--s-2); text-align: center; padding: var(--s-6) var(--s-4);
  background: var(--surface); border: 1px dashed var(--border-strong); border-radius: var(--r-lg);
}
.badge { display: grid; place-items: center; width: 2.6rem; height: 2.6rem; border-radius: 50%; background: var(--accent-soft); color: var(--accent-text); }
.title { font-size: var(--fs-md); font-weight: 700; letter-spacing: -0.01em; }
.empty p { max-width: 32rem; }
.actions { margin-top: var(--s-2); display: flex; gap: var(--s-2); flex-wrap: wrap; justify-content: center; }
</style>
