<script setup lang="ts">
import { computed, ref } from 'vue'
import Icon from '../common/Icon.vue'

/**
 * The mentor's voice. The text is the backend's message, shown unchanged; this component only presents it.
 * "Why am I seeing this?" lists the message's own inputs in plain words.
 */
const props = defineProps<{ text: string; payload?: Record<string, unknown> }>()
const showWhy = ref(false)

function words(key: string): string {
  const text = key.replace(/_/g, ' ')
  return text.charAt(0).toUpperCase() + text.slice(1)
}
const details = computed(() =>
  Object.entries(props.payload ?? {})
    .map(([key, value]) => ({
      key,
      label: words(key),
      value: Array.isArray(value) ? value.join(', ') : String(value ?? ''),
    }))
    .filter((d) => d.value !== ''),
)
</script>

<template>
  <section
    class="mentor"
    aria-labelledby="mentor-title"
  >
    <div class="head">
      <span
        class="spark"
        aria-hidden="true"
      ><Icon
        name="zap"
        :size="16"
      /></span>
      <h2
        id="mentor-title"
        class="eyebrow"
      >
        Your mentor
      </h2>
    </div>
    <p
      class="text"
      data-testid="mentor-message"
    >
      {{ text }}
    </p>
    <template v-if="details.length">
      <button
        type="button"
        class="why"
        :aria-expanded="showWhy"
        data-testid="message-why"
        @click="showWhy = !showWhy"
      >
        Why am I seeing this?
        <Icon
          :name="showWhy ? 'chevron-down' : 'chevron-right'"
          :size="14"
        />
      </button>
      <dl
        v-if="showWhy"
        class="details"
        data-testid="message-payload"
      >
        <div
          v-for="d in details"
          :key="d.key"
        >
          <dt>{{ d.label }}</dt>
          <dd>{{ d.value }}</dd>
        </div>
      </dl>
    </template>
  </section>
</template>

<style scoped>
.mentor {
  display: grid; gap: var(--s-3); padding: var(--s-5); background: var(--surface); border: 1px solid var(--accent-border);
  border-left: 4px solid var(--accent); border-radius: var(--r-lg); box-shadow: var(--shadow-sm);
}
.head { display: flex; align-items: center; gap: var(--s-2); }
.spark { display: grid; place-items: center; width: 1.6rem; height: 1.6rem; border-radius: 50%; background: var(--accent-soft); color: var(--accent-text); }
.eyebrow { margin: 0; color: var(--accent-text); }
.text { font-size: var(--fs-lg); line-height: 1.5; font-weight: 520; letter-spacing: -0.01em; max-width: 46rem; }
.why { display: inline-flex; align-items: center; gap: var(--s-1); width: fit-content; background: none; border: 0; padding: 0; font: inherit; font-size: var(--fs-sm); color: var(--text-3); cursor: pointer; }
.why:hover { color: var(--text); }
.details { display: flex; flex-wrap: wrap; gap: var(--s-2) var(--s-5); font-size: var(--fs-sm); padding-top: var(--s-2); border-top: 1px solid var(--border); }
dt { color: var(--text-3); }
dd { color: var(--text); font-weight: 560; }
@media (max-width: 767px) {
  .mentor { padding: var(--s-4); gap: var(--s-2); }
  .text { font-size: var(--fs-md); }
}
</style>
