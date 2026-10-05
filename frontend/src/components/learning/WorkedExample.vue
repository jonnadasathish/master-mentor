<script setup lang="ts">
import { computed } from 'vue'
import type { CodeSnippet, ContentBody } from '../../api/types'
import CodeBlock from './CodeBlock.vue'
import RichText from './RichText'

/** A problem solved step by step, the way you would say it aloud. */
const props = defineProps<{ body: ContentBody }>()
const steps = computed(() => (props.body.steps as { title: string; text: string; code?: CodeSnippet }[]) ?? [])
const takeaways = computed(() => (props.body.takeaways as string[]) ?? [])
const code = computed(() => props.body.code as CodeSnippet | undefined)
</script>

<template>
  <article
    class="example"
    data-testid="worked-example"
  >
    <section class="problem">
      <h2>The problem</h2>
      <RichText :text="String(body.problem ?? '')" />
    </section>
    <ol class="steps">
      <li
        v-for="(step, i) in steps"
        :key="i"
        class="step"
      >
        <span
          class="n"
          aria-hidden="true"
        >{{ i + 1 }}</span>
        <div class="step-body">
          <h3>{{ step.title }}</h3>
          <RichText :text="step.text" />
          <CodeBlock
            v-if="step.code"
            :code="step.code.code"
            :language="step.code.language"
          />
        </div>
      </li>
    </ol>
    <CodeBlock
      v-if="code"
      :code="code.code"
      :language="code.language"
      :explanation="code.explanation"
    />
    <p
      v-if="body.complexity"
      class="complexity"
    >
      <strong>Complexity:</strong> <RichText
        :text="String(body.complexity)"
        inline
      />
    </p>
    <section v-if="takeaways.length">
      <h2>Takeaways</h2>
      <ul class="takeaways">
        <li
          v-for="t in takeaways"
          :key="t"
        >
          <RichText
            :text="t"
            inline
          />
        </li>
      </ul>
    </section>
  </article>
</template>

<style scoped>
.example { display: grid; gap: var(--s-5); max-width: 46rem; }
h2 { font-size: var(--fs-md); margin-bottom: var(--s-2); }
h3 { font-size: var(--fs-base); margin-bottom: var(--s-1); }
.steps { display: grid; gap: var(--s-4); }
.step { display: grid; grid-template-columns: 2rem minmax(0, 1fr); gap: var(--s-3); }
.n { display: grid; place-items: center; width: 1.8rem; height: 1.8rem; border-radius: 50%; background: var(--accent-soft); color: var(--accent-text); font-weight: 700; font-size: var(--fs-sm); }
.step-body { display: grid; gap: var(--s-2); min-width: 0; }
.complexity { color: var(--text-2); }
.takeaways { list-style: disc; padding-left: var(--s-5); display: grid; gap: var(--s-1); }
</style>
