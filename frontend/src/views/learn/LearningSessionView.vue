<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { api } from '../../api'
import { ApiError } from '../../api/client'
import type { CompletionInput, ContentDetail, Effects, LearningSession, StepResult } from '../../api/types'
import ErrorState from '../../components/common/ErrorState.vue'
import Icon from '../../components/common/Icon.vue'
import Skeleton from '../../components/common/Skeleton.vue'
import ContentRunner from '../../components/learning/ContentRunner.vue'
import EffectsPanel from '../../components/missions/EffectsPanel.vue'
import AttemptForm from '../../components/practice/AttemptForm.vue'
import { formatMinutes } from '../../presentation/format'
import { CONTENT_TYPE_LABEL, PRACTICE_STATE_LABEL } from '../../presentation/learning'
import { STAGE_LABEL } from '../../presentation/language'
import { openSession } from '../../learning/session'
import { refreshDerivedData } from '../../stores/data'

/**
 * A learning session: the mentor's stage for one skill, expanded into steps (learn → check → practise → reflect).
 * Each step records its own observation; the session closes when every step is done or skipped.
 */
const route = useRoute()
const router = useRouter()
const session = ref<LearningSession | null>(null)
const error = ref<unknown>(null)
const selected = ref<number | null>(null)
const content = ref<ContentDetail | null>(null)
const lastEffects = ref<Effects | undefined>()
const reflection = ref('')
const busy = ref(false)
const actionError = ref('')

const id = computed(() => Number(route.params.id))
const step = computed(() => session.value?.steps.find((s) => s.position === (selected.value ?? session.value?.next_position)) ?? null)
const finished = computed(() => session.value?.status !== 'ACTIVE')
const progress = computed(() => {
  const steps = session.value?.steps ?? []
  return { done: steps.filter((s) => s.status !== 'PENDING').length, total: steps.length }
})

async function load(): Promise<void> {
  error.value = null
  try {
    session.value = (await api.get<LearningSession>(`/learning/sessions/${id.value}`)).data
    selected.value = session.value.next_position
  } catch (caught) {
    error.value = caught
  }
}

watch(
  () => step.value?.content_key,
  async (key) => {
    content.value = null
    if (!key) return
    content.value = (await api.get<ContentDetail>(`/learning/content/${encodeURIComponent(key)}`)).data
  },
)

function advance(next: LearningSession, effects?: Effects): void {
  session.value = next
  lastEffects.value = effects ?? lastEffects.value
  selected.value = next.next_position
  reflection.value = ''
  void refreshDerivedData()
}

async function submitContent(input: CompletionInput) {
  const position = step.value!.position
  const envelope = await api.post<StepResult>(`/learning/sessions/${id.value}/steps/${position}/complete`, {
    completion: input,
  })
  return { result: envelope.data.completion!, effects: envelope.effects, session: envelope.data.session }
}

async function runContent(input: CompletionInput) {
  const out = await submitContent(input)
  pending.value = out.session
  return { result: out.result, effects: out.effects }
}
const pending = ref<LearningSession | null>(null)
function contentDone(_result: unknown, effects?: Effects): void {
  lastEffects.value = effects
  // Keep the result on screen; move on when the learner asks.
}
function next(): void {
  if (pending.value) advance(pending.value)
  pending.value = null
}

async function act(path: string, body: Record<string, unknown> = {}): Promise<void> {
  busy.value = true
  actionError.value = ''
  try {
    const envelope = await api.post<LearningSession | StepResult>(path, body)
    const data = envelope.data
    advance('session' in data ? data.session : data, envelope.effects)
  } catch (caught) {
    actionError.value = caught instanceof ApiError ? caught.message : String(caught)
  } finally {
    busy.value = false
  }
}

const skip = () => act(`/learning/sessions/${id.value}/steps/${step.value!.position}/skip`)
const saveReflection = () =>
  act(`/learning/sessions/${id.value}/steps/${step.value!.position}/complete`, { reflection: reflection.value || null })
const abandon = () => act(`/learning/sessions/${id.value}/abandon`)
async function repeat(): Promise<void> {
  if (session.value) await openSession(router, { skill: session.value.skill, stage: session.value.stage })
}
function attemptDone(result: StepResult, effects?: Effects): void {
  advance(result.session, effects)
}

onMounted(load)
watch(id, load)
</script>

<template>
  <div class="page">
    <Skeleton
      v-if="!session && !error"
      height="20rem"
      radius="var(--r-lg)"
    />
    <ErrorState
      v-else-if="!session"
      :error="error"
      @retry="load"
    />
    <template v-else>
      <RouterLink
        :to="{ name: 'skill', params: { key: session.skill } }"
        class="back"
      >
        <Icon
          name="arrow-left"
          :size="14"
        /> {{ session.skill_name }}
      </RouterLink>
      <header class="head">
        <p class="eyebrow">
          Learning session · {{ STAGE_LABEL[session.stage] ?? session.stage }}
        </p>
        <h1 data-testid="session-title">
          {{ session.skill_name }}
        </h1>
        <p class="meta">
          {{ formatMinutes(session.minutes) }} · {{ progress.done }} of {{ progress.total }} steps
        </p>
      </header>

      <div class="layout">
        <ol
          class="steps card-quiet"
          aria-label="Session steps"
          data-testid="session-steps"
        >
          <li
            v-for="s in session.steps"
            :key="s.position"
          >
            <button
              type="button"
              class="step"
              :class="[`is-${s.status.toLowerCase()}`, { current: s.position === step?.position }]"
              :aria-current="s.position === step?.position ? 'step' : undefined"
              :data-testid="`step-${s.position}`"
              :disabled="finished"
              @click="selected = s.position"
            >
              <span
                class="mark"
                aria-hidden="true"
              >
                <Icon
                  v-if="s.status === 'DONE'"
                  name="check"
                  :size="12"
                />
                <Icon
                  v-else-if="s.status === 'SKIPPED'"
                  name="skip"
                  :size="12"
                />
                <template v-else>{{ s.position }}</template>
              </span>
              <span class="label">
                <span class="title">{{ s.title }}</span>
                <span class="muted small">
                  {{ s.kind === 'REFLECTION' ? 'Reflection' : s.kind === 'PROBLEM' ? 'Problem' : CONTENT_TYPE_LABEL[s.content_type ?? 'lesson'] }}
                  · {{ formatMinutes(s.minutes) }}<template v-if="s.optional"> · optional</template><template v-if="s.points !== null"> · {{ s.points }}/100</template>
                  <span class="sr-only"> · {{ s.status.toLowerCase() }}</span>
                </span>
              </span>
            </button>
          </li>
        </ol>

        <section class="main">
          <section
            v-if="finished"
            class="summary card"
            data-testid="session-summary"
          >
            <p class="eyebrow">
              {{ session.status === 'ABANDONED' ? 'Session stopped' : 'Session complete' }}
            </p>
            <h2>
              <template v-if="session.outcome === 'PASSED'">
                Every scored step passed.
              </template>
              <template v-else-if="session.outcome === 'NEEDS_REPEAT'">
                Some steps need another go. That is useful evidence, not a failure.
              </template>
              <template v-else>
                Recorded.
              </template>
            </h2>
            <p
              class="before-after tabular"
              data-testid="before-after"
            >
              Score {{ session.before.score ?? 'not measured' }} → {{ session.after.score ?? 'not measured' }}
            </p>
            <div class="actions">
              <RouterLink
                :to="{ name: 'today' }"
                class="btn btn-primary"
              >
                Back to Today
              </RouterLink>
              <RouterLink
                :to="{ name: 'skill', params: { key: session.skill } }"
                class="btn"
              >
                See the skill
              </RouterLink>
              <button
                type="button"
                class="btn"
                data-testid="repeat-session"
                @click="repeat"
              >
                Repeat this session
              </button>
            </div>
            <EffectsPanel
              v-if="lastEffects"
              :effects="lastEffects"
            />
          </section>

          <template v-else-if="step">
            <h2 class="step-title">
              {{ step.title }}
            </h2>
            <template v-if="step.kind === 'CONTENT'">
              <Skeleton
                v-if="!content"
                height="12rem"
              />
              <template v-else>
                <ContentRunner
                  :key="`${session.id}-${step.position}`"
                  :content="content"
                  :submit="runContent"
                  @completed="contentDone"
                />
                <button
                  v-if="pending"
                  type="button"
                  class="btn btn-primary btn-lg next"
                  data-testid="next-step"
                  @click="next"
                >
                  {{ pending.status === 'ACTIVE' ? 'Next step' : 'Finish the session' }} <Icon
                    name="arrow-right"
                    :size="14"
                  />
                </button>
              </template>
            </template>
            <template v-else-if="step.kind === 'PROBLEM' && step.problem">
              <p class="muted">
                Solve <a
                  v-if="step.problem.url"
                  :href="step.problem.url"
                  target="_blank"
                  rel="noopener noreferrer"
                >{{ step.problem.title }} <Icon
                  name="external"
                  :size="12"
                  label="opens in a new tab"
                /></a><template v-else>
                  {{ step.problem.title }}
                </template>
                ({{ step.problem.difficulty.toLowerCase() }}, currently {{ PRACTICE_STATE_LABEL[step.problem.practice_state].toLowerCase() }}),
                then record how it went.
              </p>
              <AttemptForm
                :key="`${session.id}-${step.position}`"
                :problem-id="step.problem.id"
                :client="api"
                :session-step="{ sessionId: session.id, position: step.position }"
                @step="attemptDone"
              />
            </template>
            <form
              v-else
              class="reflection"
              @submit.prevent="saveReflection"
            >
              <label for="reflection">What did you learn, and what still feels shaky? <span class="muted">(kept with the session, not scored)</span></label>
              <textarea
                id="reflection"
                v-model="reflection"
                rows="4"
                maxlength="4000"
              />
              <button
                type="submit"
                class="btn btn-primary"
                :disabled="busy"
                data-testid="save-reflection"
              >
                Save and finish
              </button>
            </form>
            <div class="step-actions">
              <button
                v-if="!pending"
                type="button"
                class="link-btn"
                :disabled="busy"
                data-testid="skip-step"
                @click="skip"
              >
                Skip this step
              </button>
              <button
                type="button"
                class="link-btn"
                :disabled="busy"
                @click="abandon"
              >
                Stop the session
              </button>
            </div>
            <p
              v-if="actionError"
              class="error"
              role="alert"
            >
              {{ actionError }}
            </p>
          </template>
        </section>
      </div>
    </template>
  </div>
</template>

<style scoped>
.back { display: inline-flex; align-items: center; gap: var(--s-1); font-size: var(--fs-sm); color: var(--text-3); width: fit-content; }
.head { display: grid; gap: var(--s-1); }
h1 { font-size: var(--fs-2xl); }
.meta { color: var(--text-2); font-size: var(--fs-sm); }
.layout { display: grid; grid-template-columns: 18rem minmax(0, 1fr); gap: var(--s-5); align-items: start; }
.steps { display: grid; gap: var(--s-1); padding: var(--s-2); position: sticky; top: var(--s-4); }
.step {
  display: flex; gap: var(--s-3); align-items: flex-start; width: 100%; text-align: left; padding: var(--s-2) var(--s-3);
  border: 0; border-radius: var(--r-md); background: transparent; font: inherit; color: var(--text); cursor: pointer;
}
.step:hover:not(:disabled) { background: var(--surface-2); }
.step.current { background: var(--accent-soft); }
.step:disabled { cursor: default; }
.mark { display: grid; place-items: center; width: 1.5rem; height: 1.5rem; border-radius: 50%; background: var(--surface-3); font-size: var(--fs-xs); font-weight: 700; flex: none; }
.is-done .mark { background: var(--healthy-fg); color: #fff; }
.is-skipped .mark { background: var(--blocked-bg); color: var(--blocked-fg); }
.label { display: grid; min-width: 0; }
.title { font-weight: 600; font-size: var(--fs-sm); }
.main { display: grid; gap: var(--s-4); min-width: 0; }
.step-title { font-size: var(--fs-xl); }
.next { width: fit-content; }
.summary { display: grid; gap: var(--s-3); }
.before-after { font-size: var(--fs-lg); font-weight: 650; }
.actions { display: flex; gap: var(--s-2); flex-wrap: wrap; }
.reflection { display: grid; gap: var(--s-2); max-width: 40rem; }
.reflection .btn { width: fit-content; }
.step-actions { display: flex; gap: var(--s-4); flex-wrap: wrap; }
.error { color: var(--critical-fg); }
.small { font-size: var(--fs-xs); }
@media (max-width: 1023px) {
  .layout { grid-template-columns: minmax(0, 1fr); }
  .steps { position: static; }
}
</style>
