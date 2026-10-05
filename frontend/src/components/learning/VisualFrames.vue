<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ContentBody } from '../../api/types'

/** A walkthrough as frames of monospace diagrams, one step at a time (keyboard: the two buttons). */
const props = defineProps<{ body: ContentBody }>()
const frames = computed(() => (props.body.frames as { caption: string; diagram: string }[]) ?? [])
const index = ref(0)
const frame = computed(() => frames.value[index.value])
</script>

<template>
  <article
    class="visual"
    data-testid="visual"
  >
    <p class="summary">
      {{ body.summary }}
    </p>
    <figure
      v-if="frame"
      class="frame"
    >
      <figcaption>
        <span class="count">Step {{ index + 1 }} of {{ frames.length }}</span>
        {{ frame.caption }}
      </figcaption>
      <pre
        tabindex="0"
        :aria-label="`Diagram for step ${index + 1}`"
      >{{ frame.diagram }}</pre>
    </figure>
    <div class="nav">
      <button
        type="button"
        class="btn"
        :disabled="index === 0"
        @click="index -= 1"
      >
        Previous
      </button>
      <button
        type="button"
        class="btn"
        :disabled="index >= frames.length - 1"
        data-testid="next-frame"
        @click="index += 1"
      >
        Next step
      </button>
    </div>
  </article>
</template>

<style scoped>
.visual { display: grid; gap: var(--s-4); max-width: 46rem; }
.summary { font-size: var(--fs-md); color: var(--text-2); }
.frame { margin: 0; display: grid; gap: var(--s-3); }
figcaption { font-weight: 600; display: grid; gap: var(--s-1); }
.count { font-size: var(--fs-xs); font-weight: 650; letter-spacing: 0.06em; text-transform: uppercase; color: var(--text-3); }
pre {
  margin: 0; padding: var(--s-4); background: var(--surface-2); border: 1px solid var(--border); border-radius: var(--r-md);
  font-family: var(--font-mono); font-size: var(--fs-sm); line-height: 1.5; overflow-x: auto; white-space: pre; overflow-wrap: normal;
}
.nav { display: flex; gap: var(--s-2); }
</style>
