<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import type { CodeSnippet, CompletionInput, CompletionResult, ContentDetail, FollowUp, Rating } from '../../api/types'
import Icon from '../common/Icon.vue'
import CodeBlock from './CodeBlock.vue'
import PracticeTimer from './PracticeTimer.vue'
import RatingInput from './RatingInput.vue'
import RichText from './RichText'

/**
 * Rubric practice (exercises, debugging and SQL scenarios, design and architecture cases, interview and behavioral
 * questions): work it, optionally under the timer, then score yourself against the criteria and the follow-ups.
 * Hints and the reference are honest signals: using them makes it guided practice.
 */
const props = defineProps<{ content: ContentDetail; result: CompletionResult | null; busy: boolean }>()
const emit = defineEmits<{ submit: [input: CompletionInput] }>()

const body = computed(() => props.content.body)
const text = (key: string) => (typeof body.value[key] === 'string' ? (body.value[key] as string) : null)
const list = (key: string) => (Array.isArray(body.value[key]) ? (body.value[key] as unknown[]).filter((v) => typeof v === 'string') as string[] : [])
const code = (key: string) => {
  const v = body.value[key]
  return v && typeof v === 'object' && !Array.isArray(v) && 'code' in v ? (v as CodeSnippet) : null
}
const requirements = computed(() => body.value.requirements as { functional: string[]; non_functional: string[] } | undefined)
const followUps = computed(() => (body.value.follow_ups as FollowUp[] | undefined) ?? [])
const hints = computed(() => list('hints'))
const reference = computed(() => ({
  text: text('reference') ?? text('model_answer') ?? text('estimates'),
  code: code('solution') ?? code('code'),
}))
const hasReference = computed(() => !!(reference.value.text || reference.value.code))

const hintsShown = ref(0)
const referenceShown = ref(false)
const notesUsed = ref(false)
const ratings = reactive<Record<string, Rating>>({})
const followups = reactive<Record<string, Rating>>({})
const timedSeconds = ref<number | null>(null)
const answer = ref('')
const rated = computed(() => Object.keys(ratings).length)

function submit(): void {
  const input: CompletionInput = {
    ratings: { ...ratings },
    followups: { ...followups },
    hints_used: hintsShown.value,
    reference_used: referenceShown.value,
    notes_used: notesUsed.value,
  }
  if (props.content.time_limit_seconds && timedSeconds.value !== null) {
    input.timed = true
    input.time_seconds = timedSeconds.value
  }
  if (answer.value.trim()) input.notes = answer.value.trim().slice(0, 4000)
  emit('submit', input)
}
</script>

<template>
  <form
    class="practice"
    data-testid="practice-runner"
    @submit.prevent="submit"
  >
    <section class="task">
      <p
        v-if="text('competency')"
        class="eyebrow"
      >
        Competency: {{ text('competency') }}
      </p>
      <RichText
        v-if="text('prompt')"
        :text="text('prompt')!"
      />
      <RichText
        v-if="text('scenario')"
        :text="text('scenario')!"
      />
      <div
        v-if="list('symptoms').length"
        class="block"
      >
        <h3>Symptoms</h3>
        <ul class="items">
          <li
            v-for="s in list('symptoms')"
            :key="s"
          >
            <RichText
              :text="s"
              inline
            />
          </li>
        </ul>
      </div>
      <div
        v-if="text('artifacts') || code('artifacts')"
        class="block"
      >
        <h3>What you have</h3>
        <CodeBlock
          v-if="code('artifacts')"
          :code="code('artifacts')!.code"
          :language="code('artifacts')!.language"
        />
        <RichText
          v-else
          :text="text('artifacts')!"
        />
      </div>
      <div
        v-if="requirements"
        class="block reqs"
      >
        <div>
          <h3>Functional requirements</h3>
          <ul class="items">
            <li
              v-for="r in requirements.functional"
              :key="r"
            >
              <RichText
                :text="r"
                inline
              />
            </li>
          </ul>
        </div>
        <div>
          <h3>Non-functional requirements</h3>
          <ul class="items">
            <li
              v-for="r in requirements.non_functional"
              :key="r"
            >
              <RichText
                :text="r"
                inline
              />
            </li>
          </ul>
        </div>
      </div>
      <CodeBlock
        v-if="code('schema')"
        :code="code('schema')!.code"
        :language="code('schema')!.language"
      />
      <div
        v-for="key in ['examples', 'constraints', 'tasks']"
        v-show="list(key).length"
        :key="key"
        class="block"
      >
        <h3>{{ key === 'examples' ? 'Examples' : key === 'constraints' ? 'Constraints' : 'Your tasks' }}</h3>
        <ul class="items">
          <li
            v-for="s in list(key)"
            :key="s"
          >
            <RichText
              :text="s"
              inline
            />
          </li>
        </ul>
      </div>
      <CodeBlock
        v-if="code('starter')"
        :code="code('starter')!.code"
        :language="code('starter')!.language"
      />
      <details
        v-if="list('approach').length"
        class="block"
      >
        <summary>A way to structure your answer</summary>
        <ol class="items numbered">
          <li
            v-for="s in list('approach')"
            :key="s"
          >
            <RichText
              :text="s"
              inline
            />
          </li>
        </ol>
      </details>
    </section>

    <PracticeTimer
      v-if="content.time_limit_seconds && !result"
      :limit-seconds="content.time_limit_seconds"
      @stopped="(s) => (timedSeconds = s)"
    />

    <section
      v-if="!result"
      class="work"
    >
      <label
        class="answer"
        for="practice-answer"
      >Your answer or notes <span class="muted">(optional, saved with the record)</span></label>
      <textarea
        id="practice-answer"
        v-model="answer"
        rows="6"
        maxlength="4000"
      />
      <div
        v-if="hints.length"
        class="hints"
      >
        <ol
          v-if="hintsShown"
          class="items numbered"
          data-testid="hints"
        >
          <li
            v-for="h in hints.slice(0, hintsShown)"
            :key="h"
          >
            <RichText
              :text="h"
              inline
            />
          </li>
        </ol>
        <button
          v-if="hintsShown < hints.length"
          type="button"
          class="btn btn-sm"
          data-testid="show-hint"
          @click="hintsShown += 1"
        >
          <Icon
            name="help"
            :size="14"
          /> Show a hint ({{ hints.length - hintsShown }} left)
        </button>
      </div>
    </section>

    <section
      v-if="hasReference"
      class="reference"
    >
      <button
        v-if="!referenceShown"
        type="button"
        class="link-btn"
        data-testid="show-reference"
        @click="referenceShown = true"
      >
        Show the reference answer
      </button>
      <template v-else>
        <h3>Reference</h3>
        <p
          v-if="!result"
          class="muted small"
        >
          Seen before scoring, so this counts as guided practice.
        </p>
        <RichText
          v-if="reference.text"
          :text="reference.text"
        />
        <CodeBlock
          v-if="reference.code"
          :code="reference.code.code"
          :language="reference.code.language"
          :explanation="reference.code.explanation"
        />
      </template>
    </section>

    <section
      v-if="!result"
      class="score"
      aria-labelledby="score-title"
    >
      <h3 id="score-title">
        Score yourself honestly
      </h3>
      <ul class="criteria">
        <li
          v-for="r in content.rubric"
          :key="r.key"
          class="criterion"
        >
          <span class="label"><RichText
            :text="r.label"
            inline
          /> <span class="muted small">· {{ r.points }} pt</span></span>
          <RatingInput
            v-model="ratings[r.key]"
            :name="`criterion-${r.key}`"
            :label="r.label"
          />
        </li>
      </ul>
      <template v-if="followUps.length">
        <h3>Follow-up questions</h3>
        <ul class="criteria">
          <li
            v-for="(f, i) in followUps"
            :key="i"
            class="criterion followup"
          >
            <span class="label">
              <RichText
                :text="f.prompt"
                inline
              />
              <details>
                <summary class="small">What a strong answer covers</summary>
                <RichText :text="f.look_for" />
              </details>
            </span>
            <RatingInput
              v-model="followups[String(i)]"
              :name="`followup-${i}`"
              :label="`Follow-up ${i + 1}`"
            />
          </li>
        </ul>
      </template>
      <label class="notes">
        <input
          v-model="notesUsed"
          type="checkbox"
        >
        I used notes or documentation
      </label>
      <button
        type="submit"
        class="btn btn-primary btn-lg"
        :disabled="busy || rated === 0"
        data-testid="submit-practice"
      >
        Record this practice
      </button>
    </section>
  </form>
</template>

<style scoped>
.practice { display: grid; gap: var(--s-5); max-width: 48rem; }
.task, .work, .score, .reference { display: grid; gap: var(--s-3); }
.block { display: grid; gap: var(--s-2); }
.reqs { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--s-4); }
h3 { font-size: var(--fs-base); }
.items { list-style: disc; padding-left: var(--s-5); display: grid; gap: var(--s-1); line-height: 1.6; }
.numbered { list-style: decimal; }
details summary { cursor: pointer; font-weight: 600; color: var(--accent-text); }
.answer { font-weight: 600; }
.hints { display: grid; gap: var(--s-2); }
.hints .btn { width: fit-content; }
.criteria { display: grid; gap: var(--s-3); }
.criterion { display: flex; justify-content: space-between; align-items: center; gap: var(--s-3); flex-wrap: wrap; padding: var(--s-3); border: 1px solid var(--border); border-radius: var(--r-md); }
.criterion .label { flex: 1 1 16rem; display: grid; gap: var(--s-1); }
.notes { display: flex; align-items: center; gap: var(--s-2); }
.score .btn { width: fit-content; }
.small { font-size: var(--fs-sm); }
@media (max-width: 767px) { .reqs { grid-template-columns: minmax(0, 1fr); } }
</style>
