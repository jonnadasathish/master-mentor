<script setup lang="ts">
import { computed, ref } from 'vue'
import { ApiError } from '../../api/client'
import type { CompletionInput, CompletionResult, ContentDetail, Effects } from '../../api/types'
import { newRequestId } from '../../practice/payload'
import { RECORDS_LABEL } from '../../presentation/learning'
import Icon from '../common/Icon.vue'
import EffectsPanel from '../missions/EffectsPanel.vue'
import CardsRunner from './CardsRunner.vue'
import CheckRunner from './CheckRunner.vue'
import LessonReader from './LessonReader.vue'
import PracticeRunner from './PracticeRunner.vue'
import SpeakingRunner from './SpeakingRunner.vue'
import ProblemSet from './ProblemSet.vue'
import ProjectRunner from './ProjectRunner.vue'
import type { Submitter } from './submitter'
import VisualFrames from './VisualFrames.vue'
import WorkedExample from './WorkedExample.vue'

/**
 * Shows one content item and records its completion through ``submit`` (the content endpoint, or a session step).
 * Scores and what changed come from the server; this component only collects what the learner did.
 */
const props = defineProps<{ content: ContentDetail; submit: Submitter }>()
const emit = defineEmits<{ completed: [result: CompletionResult, effects?: Effects] }>()

const result = ref<CompletionResult | null>(null)
const effects = ref<Effects | undefined>()
const busy = ref(false)
const error = ref('')
const minutes = ref(props.content.minutes)
const requestId = ref(newRequestId())
const reading = computed(() => ['lesson', 'concept', 'worked_example', 'visual_explanation'].includes(props.content.type))

async function record(input: CompletionInput): Promise<void> {
  busy.value = true
  error.value = ''
  try {
    const out = await props.submit({ ...input, client_request_id: requestId.value })
    requestId.value = newRequestId()
    effects.value = out.effects
    if (props.content.type !== 'project') result.value = out.result
    emit('completed', out.result, out.effects)
  } catch (caught) {
    error.value = caught instanceof ApiError ? caught.message : String(caught)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="runner">
    <LessonReader
      v-if="content.type === 'lesson' || content.type === 'concept'"
      :body="content.body"
      :type="content.type"
    />
    <WorkedExample
      v-else-if="content.type === 'worked_example'"
      :body="content.body"
    />
    <VisualFrames
      v-else-if="content.type === 'visual_explanation'"
      :body="content.body"
    />
    <CheckRunner
      v-else-if="content.type === 'concept_check' || content.type === 'quiz'"
      :content="content"
      :result="result"
      :busy="busy"
      @submit="record"
    />
    <CardsRunner
      v-else-if="content.type === 'revision_card'"
      :content="content"
      :result="result"
      :busy="busy"
      @submit="record"
    />
    <ProblemSet
      v-else-if="content.type === 'guided_problem' || content.type === 'timed_problem'"
      :content="content"
    />
    <ProjectRunner
      v-else-if="content.type === 'project'"
      :content="content"
      :busy="busy"
      @submit="record"
    />
    <SpeakingRunner
      v-else-if="content.type === 'interview_question' && content.body.speaking"
      :content="content"
      :result="result"
      :busy="busy"
      @submit="record"
    />
    <PracticeRunner
      v-else
      :content="content"
      :result="result"
      :busy="busy"
      @submit="record"
    />

    <div
      v-if="reading && !result"
      class="studied"
    >
      <label for="studied-minutes">Minutes spent</label>
      <input
        id="studied-minutes"
        v-model.number="minutes"
        type="number"
        min="1"
        max="600"
        class="minutes"
      >
      <button
        type="button"
        class="btn btn-primary"
        :disabled="busy"
        data-testid="mark-studied"
        @click="record({ minutes })"
      >
        <Icon
          name="check"
          :size="14"
        /> I've studied this
      </button>
      <span class="muted small">This {{ RECORDS_LABEL.STUDY_SESSION }}.</span>
    </div>

    <p
      v-if="error"
      class="error"
      role="alert"
    >
      {{ error }}
    </p>

    <section
      v-if="result"
      class="result"
      :class="result.passed === false ? 'miss' : 'ok'"
      data-testid="completion-result"
      aria-live="polite"
    >
      <p class="headline">
        <Icon
          :name="result.passed === false ? 'refresh' : 'check-circle'"
          :size="18"
        />
        <template v-if="result.speaking">
          Speaking practice completed.
          <span class="muted small">{{ result.passed ? 'It met the practice bar.' : 'Not yet at the practice bar: the mentor will bring this back.' }}</span>
        </template>
        <template v-else-if="result.points === null">
          Recorded as study time.
        </template>
        <template v-else>
          <strong class="tabular">{{ result.points }} / 100</strong>
          {{ result.passed ? '— passed.' : '— not yet: the mentor will bring this back.' }}
        </template>
      </p>
      <p
        v-if="result.followup_points !== null && !result.speaking"
        class="small"
      >
        Follow-ups: <strong class="tabular">{{ result.followup_points }} / 100</strong>
      </p>
      <p class="muted small">
        This {{ RECORDS_LABEL[result.observation.kind] ?? 'is recorded' }}.
      </p>
    </section>
    <EffectsPanel
      v-if="effects && (result || content.type === 'project')"
      :effects="effects"
    />
  </div>
</template>

<style scoped>
.runner { display: grid; gap: var(--s-5); }
.studied { display: flex; align-items: center; gap: var(--s-3); flex-wrap: wrap; padding: var(--s-4); background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-lg); }
.minutes { width: 5.5rem; }
.result { display: grid; gap: var(--s-1); padding: var(--s-4); border-radius: var(--r-lg); border: 1px solid; }
.result.ok { background: var(--healthy-bg); border-color: var(--healthy-bd); }
.result.miss { background: var(--high-bg); border-color: var(--high-bd); }
.headline { display: flex; align-items: center; gap: var(--s-2); font-size: var(--fs-md); }
.error { color: var(--critical-fg); }
.small { font-size: var(--fs-sm); }
</style>
