<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { api } from '../../api'
import { ApiError } from '../../api/client'
import type {
  CompletionInput,
  CompletionResult,
  ContentDetail,
  FollowUp,
  Rating,
  SpeakingResult,
} from '../../api/types'
import { SPEECH_DISCLOSURE, SPEECH_UNSUPPORTED, useSpeechRecognition } from '../../composables/useSpeechRecognition'
import type { RecognitionConstructor } from '../../composables/useSpeechRecognition'
import Icon from '../common/Icon.vue'
import RatingInput from './RatingInput.vue'
import RichText from './RichText'
import SpeakingSignals from './SpeakingSignals.vue'

/**
 * Spoken practice (D-087): speak the answer with the browser's speech recognition when it exists, or practise
 * manually. Either way you review the transcript, check the signals the server measured, rate yourself against the
 * key points and submit. Manual practice is recorded as supported practice (weaker evidence) and the page says so.
 */
const props = defineProps<{
  content: ContentDetail
  result: CompletionResult | null
  busy: boolean
  recognition?: RecognitionConstructor | null
}>()
const emit = defineEmits<{ submit: [input: CompletionInput] }>()

const speech = useSpeechRecognition(props.recognition === undefined ? undefined : props.recognition)
const mode = ref<'speech' | 'manual'>(speech.supported ? 'speech' : 'manual')
const reviewed = ref(false)
const transcript = ref('')
const seconds = ref(0)
const manualSeconds = ref<number | null>(null)
const preview = ref<SpeakingResult | null>(null)
const previewError = ref('')
const checking = ref(false)

const body = computed(() => props.content.body)
const prompt = computed(() => (typeof body.value.prompt === 'string' ? body.value.prompt : ''))
const speaking = computed(() => (body.value.speaking ?? {}) as { target_seconds?: number })
const followUps = computed(() => (body.value.follow_ups as FollowUp[] | undefined) ?? [])
const ratings = reactive<Record<string, Rating>>({})
const followups = reactive<Record<string, Rating>>({})
const reflection = ref('')
const notesUsed = ref(false)
const rated = computed(() => Object.keys(ratings).length)
const canSubmit = computed(() =>
  mode.value === 'manual' ? rated.value > 0 : reviewed.value && transcript.value.trim().length > 0 && rated.value > 0,
)
const mmss = (s: number) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`

function begin(): void {
  preview.value = null
  previewError.value = ''
  reviewed.value = false
  speech.start()
}
function finish(): void {
  speech.stop()
  transcript.value = speech.final.value
  seconds.value = speech.elapsed.value
  reviewed.value = true
}
function useManual(): void {
  if (speech.listening.value) speech.stop()
  mode.value = 'manual'
  preview.value = null
}
function useSpeech(): void {
  if (speech.supported) mode.value = 'speech'
}

async function check(): Promise<void> {
  checking.value = true
  previewError.value = ''
  try {
    const out = await api.post<{ speaking: SpeakingResult }>('/communication/preview', {
      content_key: props.content.key,
      transcript: transcript.value,
      duration_seconds: Math.max(1, seconds.value),
    })
    preview.value = out.data.speaking
  } catch (caught) {
    preview.value = null
    previewError.value = caught instanceof ApiError ? caught.message : String(caught)
  } finally {
    checking.value = false
  }
}

function submit(): void {
  const manual = mode.value === 'manual'
  const duration = manual ? Math.max(0, manualSeconds.value ?? 0) : Math.max(1, seconds.value)
  const input: CompletionInput = {
    ratings: { ...ratings },
    followups: { ...followups },
    notes_used: notesUsed.value,
    speech: {
      source: manual ? 'MANUAL' : 'BROWSER',
      duration_seconds: duration,
      ...(manual ? {} : { transcript: transcript.value.trim() }),
      ...(reflection.value.trim() ? { reflection: reflection.value.trim().slice(0, 2000) } : {}),
    },
  }
  if (!manual && props.content.time_limit_seconds) {
    input.timed = true
    input.time_seconds = duration
  }
  emit('submit', input)
}
</script>

<template>
  <form
    class="speaking"
    data-testid="speaking-runner"
    @submit.prevent="submit"
  >
    <section class="task">
      <RichText
        v-if="prompt"
        :text="prompt"
      />
      <p class="target muted">
        <Icon
          name="clock"
          :size="14"
        />
        <template v-if="speaking.target_seconds">
          Aim for about {{ speaking.target_seconds }} seconds.
        </template>
        <template v-if="content.time_limit_seconds">
          Time limit {{ mmss(content.time_limit_seconds) }}; going over records it as untimed practice.
        </template>
      </p>
    </section>

    <section
      v-if="!result"
      class="privacy"
      data-testid="speech-privacy"
    >
      <Icon
        name="lock"
        :size="14"
      />
      <p class="small">
        {{ SPEECH_DISCLOSURE }}
      </p>
    </section>

    <template v-if="!result">
      <section
        v-if="!speech.supported"
        class="notice"
        role="status"
        data-testid="speech-unsupported"
      >
        <p><strong>{{ SPEECH_UNSUPPORTED }}</strong></p>
        <p class="small">
          You can still practise: speak your answer aloud on your own, then review yourself below. It is recorded as
          manual practice, which counts as supported practice (weaker evidence than a measured one).
        </p>
      </section>

      <div
        v-if="speech.supported"
        class="modes"
        role="group"
        aria-label="How do you want to practise?"
      >
        <button
          type="button"
          class="btn btn-sm"
          :class="{ 'btn-primary': mode === 'speech' }"
          :aria-pressed="mode === 'speech'"
          data-testid="mode-speech"
          @click="useSpeech"
        >
          Speak with speech recognition
        </button>
        <button
          type="button"
          class="btn btn-sm"
          :class="{ 'btn-primary': mode === 'manual' }"
          :aria-pressed="mode === 'manual'"
          data-testid="mode-manual"
          @click="useManual"
        >
          Manual practice
        </button>
      </div>

      <section
        v-if="mode === 'speech'"
        class="stage"
      >
        <div class="controls">
          <button
            v-if="!speech.listening.value"
            type="button"
            class="btn btn-primary"
            data-testid="start-speaking"
            @click="begin"
          >
            <Icon
              name="mocks"
              :size="14"
            /> {{ reviewed ? 'Speak again' : 'Start speaking' }}
          </button>
          <button
            v-else
            type="button"
            class="btn btn-primary"
            data-testid="stop-speaking"
            @click="finish"
          >
            Stop
          </button>
          <span
            class="clock tabular"
            role="timer"
          >{{ mmss(speech.listening.value ? speech.elapsed.value : seconds) }}</span>
          <span
            v-if="speech.listening.value"
            class="listening"
            role="status"
          >Listening…</span>
        </div>
        <p
          v-if="speech.error.value"
          class="error"
          role="alert"
        >
          {{ speech.error.value }}
        </p>
        <p
          v-if="speech.listening.value"
          class="live"
          data-testid="live-transcript"
        >
          {{ speech.transcript.value || 'Start speaking; your words appear here.' }}
        </p>

        <template v-if="reviewed && !speech.listening.value">
          <label
            for="transcript"
            class="field"
          >Review your transcript <span class="muted">(fix any words the browser misheard before you submit)</span></label>
          <textarea
            id="transcript"
            v-model="transcript"
            rows="6"
            maxlength="8000"
            data-testid="transcript"
            @input="preview = null"
          />
          <button
            type="button"
            class="btn btn-sm"
            :disabled="checking || !transcript.trim()"
            data-testid="check-signals"
            @click="check"
          >
            Check my signals
          </button>
          <p
            v-if="previewError"
            class="error"
            role="alert"
          >
            {{ previewError }}
          </p>
          <SpeakingSignals
            v-if="preview"
            :speaking="preview"
          />
        </template>
      </section>

      <section
        v-else
        class="stage"
        data-testid="manual-mode"
      >
        <p>
          Speak your answer aloud now, then review yourself honestly. Nothing is recorded or measured.
        </p>
        <label
          for="manual-seconds"
          class="field"
        >About how many seconds did you speak? <span class="muted">(optional)</span></label>
        <input
          id="manual-seconds"
          v-model.number="manualSeconds"
          type="number"
          min="0"
          max="3600"
          class="seconds"
        >
      </section>

      <section
        class="score"
        aria-labelledby="speak-score-title"
      >
        <h3 id="speak-score-title">
          Review yourself against the key points
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
            /></span>
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
              class="criterion"
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
        <label
          for="speak-reflection"
          class="field"
        >One thing to improve next time <span class="muted">(optional)</span></label>
        <textarea
          id="speak-reflection"
          v-model="reflection"
          rows="2"
          maxlength="2000"
        />
        <label class="notes">
          <input
            v-model="notesUsed"
            type="checkbox"
          >
          I used notes while speaking
        </label>
        <button
          type="submit"
          class="btn btn-primary btn-lg"
          :disabled="busy || !canSubmit"
          data-testid="submit-speaking"
        >
          Record this speaking practice
        </button>
        <p
          v-if="mode === 'speech' && !reviewed"
          class="muted small"
        >
          Speak first, then review the transcript to unlock recording.
        </p>
      </section>
    </template>

    <SpeakingSignals
      v-else-if="result.speaking"
      :speaking="result.speaking"
    />
  </form>
</template>

<style scoped>
.speaking { display: grid; gap: var(--s-5); max-width: 48rem; }
.task, .stage, .score { display: grid; gap: var(--s-3); }
.target { display: flex; align-items: center; gap: var(--s-2); }
.privacy { display: flex; gap: var(--s-2); align-items: flex-start; padding: var(--s-3) var(--s-4); border: 1px solid var(--border); border-radius: var(--r-md); background: var(--surface-3); }
.notice { display: grid; gap: var(--s-2); padding: var(--s-4); border: 1px solid var(--high-bd); background: var(--high-bg); border-radius: var(--r-md); }
.modes, .controls { display: flex; gap: var(--s-3); align-items: center; flex-wrap: wrap; }
.clock { font-family: var(--font-mono); font-size: var(--fs-lg); font-weight: 650; color: var(--accent-text); }
.listening { color: var(--accent-text); font-weight: 600; }
.live { padding: var(--s-3); border: 1px dashed var(--border); border-radius: var(--r-md); min-height: 3.5rem; line-height: 1.6; }
.field { font-weight: 600; }
.seconds { width: 7rem; }
.criteria { display: grid; gap: var(--s-3); }
.criterion { display: flex; justify-content: space-between; align-items: center; gap: var(--s-3); flex-wrap: wrap; padding: var(--s-3); border: 1px solid var(--border); border-radius: var(--r-md); }
.criterion .label { flex: 1 1 16rem; display: grid; gap: var(--s-1); }
details summary { cursor: pointer; font-weight: 600; color: var(--accent-text); }
.notes { display: flex; align-items: center; gap: var(--s-2); }
.score .btn-lg { width: fit-content; }
.error { color: var(--critical-fg); }
.small { font-size: var(--fs-sm); }
h3 { font-size: var(--fs-base); }
@media (max-width: 767px) { .criterion { align-items: flex-start; } .score .btn-lg { width: 100%; } }
</style>
