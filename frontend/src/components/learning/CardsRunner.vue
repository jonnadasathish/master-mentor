<script setup lang="ts">
import { computed, reactive } from 'vue'
import type { CompletionInput, CompletionResult, ContentDetail, Rating } from '../../api/types'
import RatingInput from './RatingInput.vue'
import RichText from './RichText'

/** Recall cards: try to answer from memory, flip, then say how well you recalled it. */
const props = defineProps<{ content: ContentDetail; result: CompletionResult | null; busy: boolean }>()
const emit = defineEmits<{ submit: [input: CompletionInput] }>()
const cards = computed(() => (props.content.body.cards as { front: string; back: string }[]) ?? [])
const flipped = reactive<Record<number, boolean>>({})
const grades = reactive<Record<string, Rating>>({})
const graded = computed(() => Object.keys(grades).length)
</script>

<template>
  <form
    class="cards"
    data-testid="cards-runner"
    @submit.prevent="emit('submit', { self_grades: { ...grades } })"
  >
    <ol class="list">
      <li
        v-for="(card, i) in cards"
        :key="i"
        class="card-quiet card"
      >
        <p class="front">
          <RichText
            :text="card.front"
            inline
          />
        </p>
        <button
          v-if="!flipped[i]"
          type="button"
          class="btn btn-sm"
          :data-testid="`flip-${i}`"
          @click="flipped[i] = true"
        >
          Show answer
        </button>
        <template v-else>
          <p class="back">
            <RichText
              :text="card.back"
              inline
            />
          </p>
          <RatingInput
            v-model="grades[String(i)]"
            :name="`card-${i}`"
            :label="`How well did you recall card ${i + 1}?`"
          />
        </template>
      </li>
    </ol>
    <div
      v-if="!result"
      class="submit"
    >
      <button
        type="submit"
        class="btn btn-primary btn-lg"
        :disabled="busy || graded === 0"
        data-testid="submit-cards"
      >
        Save my recall
      </button>
      <span class="muted small">{{ graded }} of {{ cards.length }} rated</span>
    </div>
  </form>
</template>

<style scoped>
.cards { display: grid; gap: var(--s-4); max-width: 46rem; }
.list { display: grid; gap: var(--s-3); }
.card { display: grid; gap: var(--s-3); }
.front { font-weight: 650; font-size: var(--fs-md); }
.back { padding: var(--s-3); border-left: 3px solid var(--accent); background: var(--accent-soft); border-radius: var(--r-sm); }
.card .btn { width: fit-content; }
.submit { display: flex; gap: var(--s-3); align-items: center; flex-wrap: wrap; }
.small { font-size: var(--fs-sm); }
</style>
