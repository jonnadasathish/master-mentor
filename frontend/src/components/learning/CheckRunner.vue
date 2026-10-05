<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import type { CheckQuestion, CompletionInput, CompletionResult, ContentDetail, Rating } from '../../api/types'
import Icon from '../common/Icon.vue'
import CodeBlock from './CodeBlock.vue'
import RatingInput from './RatingInput.vue'
import RichText from './RichText'

/**
 * A closed-book concept check. Choice questions are graded by the server; for a short question you write your
 * answer, compare it with the model answer and grade yourself. After submitting, every explanation is shown.
 */
const props = defineProps<{ content: ContentDetail; result: CompletionResult | null; busy: boolean }>()
const emit = defineEmits<{ submit: [input: CompletionInput] }>()

const questions = computed(() => (props.content.body.questions as CheckQuestion[]) ?? [])
const chosen = reactive<Record<string, number[]>>({})
const drafts = reactive<Record<string, string>>({})
const revealed = reactive<Record<string, boolean>>({})
const grades = reactive<Record<string, Rating>>({})
const notesUsed = ref(false)

const results = computed(() => new Map((props.result?.questions ?? []).map((q) => [q.id, q])))
const unanswered = computed(() =>
  questions.value.filter((q) => (q.kind === 'short' ? grades[q.id] === undefined : !(chosen[q.id]?.length))).length,
)

function pick(q: CheckQuestion, index: number): void {
  if (props.result) return
  if (q.kind === 'single') chosen[q.id] = [index]
  else {
    const current = chosen[q.id] ?? []
    chosen[q.id] = current.includes(index) ? current.filter((i) => i !== index) : [...current, index].sort()
  }
}

function submit(): void {
  emit('submit', { answers: { ...chosen }, self_grades: { ...grades }, notes_used: notesUsed.value })
}

function optionState(q: CheckQuestion, index: number): string {
  const r = results.value.get(q.id)
  if (!r) return (chosen[q.id] ?? []).includes(index) ? 'chosen' : ''
  if (r.answer.includes(index)) return 'correct'
  return r.chosen.includes(index) ? 'wrong' : ''
}
</script>

<template>
  <form
    class="check"
    data-testid="check-runner"
    @submit.prevent="submit"
  >
    <p
      v-if="content.body.intro"
      class="intro"
    >
      {{ content.body.intro }}
    </p>
    <ol class="questions">
      <li
        v-for="(q, i) in questions"
        :key="q.id"
        class="question card-quiet"
        :data-testid="`question-${q.id}`"
      >
        <p class="prompt">
          <span class="qn">{{ i + 1 }}.</span>
          <RichText
            :text="q.prompt"
            inline
          />
          <span
            v-if="q.kind === 'multi'"
            class="muted small"
          > (choose all that apply)</span>
        </p>
        <CodeBlock
          v-if="q.code"
          :code="q.code.code"
          :language="q.code.language"
        />
        <div
          v-if="q.kind !== 'short'"
          class="options"
          :role="q.kind === 'single' ? 'radiogroup' : 'group'"
          :aria-label="`Options for question ${i + 1}`"
        >
          <label
            v-for="(option, index) in q.options ?? []"
            :key="index"
            class="option"
            :class="optionState(q, index)"
          >
            <input
              :type="q.kind === 'single' ? 'radio' : 'checkbox'"
              :name="q.id"
              :checked="(chosen[q.id] ?? []).includes(index)"
              :disabled="!!result"
              @change="pick(q, index)"
            >
            <RichText
              :text="option"
              inline
            />
            <Icon
              v-if="optionState(q, index) === 'correct'"
              name="check"
              :size="14"
              label="Correct answer"
            />
            <Icon
              v-else-if="optionState(q, index) === 'wrong'"
              name="x"
              :size="14"
              label="Your answer, incorrect"
            />
          </label>
        </div>
        <div
          v-else
          class="short"
        >
          <label
            class="sr-only"
            :for="`draft-${q.id}`"
          >Your answer</label>
          <textarea
            :id="`draft-${q.id}`"
            v-model="drafts[q.id]"
            rows="3"
            placeholder="Write your answer before you compare."
            :disabled="!!result"
          />
          <button
            v-if="!revealed[q.id]"
            type="button"
            class="btn btn-sm"
            :data-testid="`reveal-${q.id}`"
            @click="revealed[q.id] = true"
          >
            Compare with the model answer
          </button>
          <template v-else>
            <div class="model">
              <p class="eyebrow">
                Model answer
              </p>
              <RichText :text="q.model_answer ?? ''" />
            </div>
            <p class="small">
              How close was yours?
            </p>
            <RatingInput
              v-model="grades[q.id]"
              :name="`grade-${q.id}`"
              label="Grade your answer"
            />
          </template>
        </div>
        <div
          v-if="results.get(q.id)"
          class="explanation"
          :class="results.get(q.id)!.earned === 2 ? 'ok' : 'miss'"
          data-testid="explanation"
        >
          <p class="verdict">
            <Icon
              :name="results.get(q.id)!.earned === 2 ? 'check-circle' : results.get(q.id)!.earned === 1 ? 'minus-circle' : 'alert-circle'"
              :size="15"
            />
            {{ results.get(q.id)!.earned === 2 ? 'Right' : results.get(q.id)!.earned === 1 ? 'Partly right' : 'Not right' }}
          </p>
          <RichText :text="results.get(q.id)!.explanation" />
        </div>
      </li>
    </ol>
    <div
      v-if="!result"
      class="submit"
    >
      <label class="notes">
        <input
          v-model="notesUsed"
          type="checkbox"
          data-testid="notes-used"
        >
        I looked at notes (then it does not count as recall)
      </label>
      <button
        type="submit"
        class="btn btn-primary btn-lg"
        :disabled="busy"
        data-testid="submit-check"
      >
        Check my answers
      </button>
      <p
        v-if="unanswered"
        class="muted small"
      >
        {{ unanswered }} {{ unanswered === 1 ? 'question has' : 'questions have' }} no answer yet; unanswered questions score 0.
      </p>
    </div>
  </form>
</template>

<style scoped>
.check { display: grid; gap: var(--s-4); max-width: 46rem; }
.intro { color: var(--text-2); }
.questions { display: grid; gap: var(--s-4); }
.question { display: grid; gap: var(--s-3); }
.prompt { font-weight: 600; display: flex; gap: var(--s-2); flex-wrap: wrap; }
.qn { color: var(--text-3); }
.options { display: grid; gap: var(--s-2); }
.option {
  display: flex; align-items: center; gap: var(--s-2); padding: var(--s-2) var(--s-3); border: 1px solid var(--border);
  border-radius: var(--r-md); cursor: pointer; color: var(--text); font-size: var(--fs-base); background: var(--surface);
}
.option:hover { border-color: var(--border-strong); }
.option.chosen { border-color: var(--accent); background: var(--accent-soft); }
.option.correct { border-color: var(--healthy-bd); background: var(--healthy-bg); }
.option.wrong { border-color: var(--critical-bd); background: var(--critical-bg); }
.short { display: grid; gap: var(--s-2); }
.short .btn { width: fit-content; }
.model { padding: var(--s-3); border-left: 3px solid var(--accent); background: var(--accent-soft); border-radius: var(--r-sm); display: grid; gap: var(--s-1); }
.explanation { padding: var(--s-3); border-radius: var(--r-md); display: grid; gap: var(--s-1); }
.explanation.ok { background: var(--healthy-bg); }
.explanation.miss { background: var(--high-bg); }
.verdict { display: flex; align-items: center; gap: var(--s-1); font-weight: 650; }
.submit { display: grid; gap: var(--s-2); justify-items: start; }
.notes { display: flex; align-items: center; gap: var(--s-2); }
.small { font-size: var(--fs-sm); }
</style>
