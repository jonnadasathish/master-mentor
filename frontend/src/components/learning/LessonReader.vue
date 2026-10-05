<script setup lang="ts">
import { computed } from 'vue'
import type { CodeSnippet, ContentBody } from '../../api/types'
import { LESSON_SECTIONS } from '../../presentation/learning'
import CodeBlock from './CodeBlock.vue'
import RichText from './RichText'

/** A lesson (or a short concept) in reading order: what, why, when, how, the mental model … how to explain it. */
const props = defineProps<{ body: ContentBody; type: 'lesson' | 'concept' }>()

const sections = computed(() => {
  const b = props.body
  const order: [string, string][] =
    props.type === 'concept'
      ? [['explanation', 'Explanation'], ['points', 'Key points'], ['example', 'Example'], ['misconceptions', 'Misconceptions']]
      : LESSON_SECTIONS
  return order
    .filter(([key]) => b[key] !== undefined && b[key] !== null)
    .map(([key, title]) => {
      const value = b[key]
      if (Array.isArray(value)) return { key, title, kind: 'list' as const, items: value as string[] }
      if (typeof value === 'object') return { key, title, kind: 'code' as const, code: value as CodeSnippet }
      return { key, title, kind: 'text' as const, text: String(value) }
    })
})
</script>

<template>
  <article
    class="lesson"
    data-testid="lesson"
  >
    <p
      v-if="body.summary"
      class="summary"
    >
      <RichText
        :text="String(body.summary)"
        inline
      />
    </p>
    <section
      v-for="s in sections"
      :key="s.key"
      class="section"
      :data-section="s.key"
    >
      <h2>{{ s.title }}</h2>
      <RichText
        v-if="s.kind === 'text'"
        :text="s.text"
      />
      <ul
        v-else-if="s.kind === 'list'"
        class="items"
      >
        <li
          v-for="item in s.items"
          :key="item"
        >
          <RichText
            :text="item"
            inline
          />
        </li>
      </ul>
      <CodeBlock
        v-else
        :code="s.code.code"
        :language="s.code.language"
        :explanation="s.code.explanation"
      />
    </section>
  </article>
</template>

<style scoped>
.lesson { display: grid; gap: var(--s-5); max-width: 46rem; }
.summary { font-size: var(--fs-lg); line-height: 1.5; color: var(--text); font-weight: 520; }
.section { display: grid; gap: var(--s-3); }
.section h2 { font-size: var(--fs-md); letter-spacing: 0; }
.section[data-section='mistakes'] h2::before { content: '⚠ '; color: var(--high-fg); }
.items { list-style: disc; padding-left: var(--s-5); display: grid; gap: var(--s-2); line-height: 1.6; }
.items li::marker { color: var(--text-3); }
</style>
