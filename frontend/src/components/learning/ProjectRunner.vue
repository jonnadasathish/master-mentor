<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import type { CodeSnippet, CompletionInput, ContentDetail, Milestone, Rating } from '../../api/types'
import { formatMinutes } from '../../presentation/format'
import Icon from '../common/Icon.vue'
import CodeBlock from './CodeBlock.vue'
import RatingInput from './RatingInput.vue'
import RichText from './RichText'

/**
 * A flagship project: the brief, then milestones you build and record one by one (each is applied work with its
 * own rubric), then the interview defense of the project.
 */
const props = defineProps<{ content: ContentDetail; busy: boolean }>()
const emit = defineEmits<{ submit: [input: CompletionInput] }>()

const body = computed(() => props.content.body)
const milestones = computed(() => (body.value.milestones as Milestone[]) ?? [])
const done = computed(() => new Set(props.content.progress?.milestones_done ?? []))
const defense = computed(() => (body.value.defense_questions as string[]) ?? [])
const open = ref<string | null>(null)
const ratings = reactive<Record<string, Record<string, Rating>>>({})
const listOf = (key: string) => (Array.isArray(body.value[key]) ? (body.value[key] as string[]) : [])
const schema = computed(() => body.value.schema)
const SPEC: [string, string][] = [
  ['apis', 'APIs'], ['testing', 'Testing'], ['deployment', 'Deployment'], ['observability', 'Observability'],
  ['failure_scenarios', 'Failure scenarios to rehearse'],
]

function record(key: string): void {
  const r = ratings[key] ?? {}
  emit('submit', key === 'defense' ? { defense: true, ratings: { ...r } } : { milestone: key, ratings: { ...r } })
  open.value = null
}
function rate(key: string, criterion: string, value: Rating): void {
  ratings[key] = { ...(ratings[key] ?? {}), [criterion]: value }
}
</script>

<template>
  <article
    class="project"
    data-testid="project"
  >
    <RichText :text="String(body.summary ?? '')" />
    <p
      v-if="listOf('stack').length"
      class="stack"
    >
      <span
        v-for="t in listOf('stack')"
        :key="t"
        class="chip"
      >{{ t }}</span>
    </p>
    <details
      class="spec"
      open
    >
      <summary>Requirements and architecture</summary>
      <div class="spec-body">
        <div
          v-if="body.requirements"
          class="reqs"
        >
          <div>
            <h2 class="sub">
              Functional
            </h2>
            <ul class="items">
              <li
                v-for="r in (body.requirements as { functional: string[] }).functional"
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
            <h2 class="sub">
              Non-functional
            </h2>
            <ul class="items">
              <li
                v-for="r in (body.requirements as { non_functional: string[] }).non_functional"
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
        <h2 class="sub">
          Architecture
        </h2>
        <RichText :text="String(body.architecture ?? '')" />
        <h2 class="sub">
          Schema
        </h2>
        <CodeBlock
          v-if="schema && typeof schema === 'object'"
          :code="(schema as CodeSnippet).code"
          :language="(schema as CodeSnippet).language"
        />
        <RichText
          v-else
          :text="String(schema ?? '')"
        />
        <template
          v-for="[key, title] in SPEC"
          :key="key"
        >
          <h2 class="sub">
            {{ title }}
          </h2>
          <ul class="items">
            <li
              v-for="s in listOf(key)"
              :key="s"
            >
              <RichText
                :text="s"
                inline
              />
            </li>
          </ul>
        </template>
      </div>
    </details>

    <section>
      <h2>Milestones</h2>
      <ol class="milestones">
        <li
          v-for="(m, i) in milestones"
          :key="m.key"
          class="milestone card-quiet"
          :class="{ done: done.has(m.key) }"
          :data-testid="`milestone-${m.key}`"
        >
          <div class="m-head">
            <span
              class="n"
              aria-hidden="true"
            >
              <Icon
                v-if="done.has(m.key)"
                name="check"
                :size="13"
              />
              <template v-else>{{ i + 1 }}</template>
            </span>
            <div class="m-title">
              <h3>{{ m.title }}</h3>
              <p class="muted small">
                {{ formatMinutes(m.minutes) }}<template v-if="done.has(m.key)">
                  · done
                </template>
              </p>
            </div>
            <button
              type="button"
              class="btn btn-sm"
              :aria-expanded="open === m.key"
              @click="open = open === m.key ? null : m.key"
            >
              {{ open === m.key ? 'Close' : done.has(m.key) ? 'Record again' : 'Record' }}
            </button>
          </div>
          <RichText :text="m.goal" />
          <ul class="items">
            <li
              v-for="d in m.deliverables"
              :key="d"
            >
              <RichText
                :text="d"
                inline
              />
            </li>
          </ul>
          <div
            v-if="open === m.key"
            class="rate"
          >
            <div
              v-for="r in m.rubric"
              :key="r.key"
              class="criterion"
            >
              <span>{{ r.label }}</span>
              <RatingInput
                :model-value="ratings[m.key]?.[r.key]"
                :name="`${m.key}-${r.key}`"
                :label="r.label"
                @update:model-value="(v) => rate(m.key, r.key, v)"
              />
            </div>
            <button
              type="button"
              class="btn btn-primary"
              :disabled="busy"
              :data-testid="`record-${m.key}`"
              @click="record(m.key)"
            >
              Save milestone
            </button>
          </div>
        </li>
      </ol>
    </section>

    <section
      class="defense card-quiet"
      data-testid="project-defense"
    >
      <h2>Defend it in an interview</h2>
      <p class="muted small">
        Answer each question aloud, then rate how well you answered.
      </p>
      <ol class="items numbered">
        <li
          v-for="(q, i) in defense"
          :key="q"
          class="criterion"
        >
          <RichText
            :text="q"
            inline
          />
          <RatingInput
            :model-value="ratings.defense?.[`q${i}`]"
            :name="`defense-${i}`"
            :label="`Defense question ${i + 1}`"
            @update:model-value="(v) => rate('defense', `q${i}`, v)"
          />
        </li>
      </ol>
      <button
        type="button"
        class="btn btn-primary"
        :disabled="busy || !ratings.defense"
        data-testid="record-defense"
        @click="record('defense')"
      >
        Save the defense
      </button>
    </section>
  </article>
</template>

<style scoped>
.project { display: grid; gap: var(--s-5); max-width: 48rem; }
h2 { font-size: var(--fs-lg); margin-bottom: var(--s-3); }
h3 { font-size: var(--fs-base); }
.sub { font-size: var(--fs-md); margin: 0; }
.stack { display: flex; flex-wrap: wrap; gap: var(--s-2); }
.chip { padding: 0.15rem 0.6rem; border-radius: 999px; background: var(--surface-2); border: 1px solid var(--border); font-size: var(--fs-sm); }
.spec summary { cursor: pointer; font-weight: 650; }
.spec-body { display: grid; gap: var(--s-3); margin-top: var(--s-3); }
.reqs { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--s-4); }
.items { list-style: disc; padding-left: var(--s-5); display: grid; gap: var(--s-1); }
.numbered { list-style: decimal; }
.milestones { display: grid; gap: var(--s-3); }
.milestone { display: grid; gap: var(--s-2); }
.milestone.done { border-color: var(--healthy-bd); }
.m-head { display: flex; align-items: center; gap: var(--s-3); }
.m-title { flex: 1; min-width: 0; }
.n { display: grid; place-items: center; width: 1.7rem; height: 1.7rem; border-radius: 50%; background: var(--accent-soft); color: var(--accent-text); font-weight: 700; font-size: var(--fs-sm); flex: none; }
.done .n { background: var(--healthy-fg); color: #fff; }
.rate { display: grid; gap: var(--s-2); padding-top: var(--s-2); border-top: 1px solid var(--border); }
.rate .btn, .defense .btn { width: fit-content; }
.criterion { display: flex; justify-content: space-between; align-items: center; gap: var(--s-3); flex-wrap: wrap; }
.defense { display: grid; gap: var(--s-3); }
.small { font-size: var(--fs-sm); }
@media (max-width: 767px) { .reqs { grid-template-columns: minmax(0, 1fr); } }
</style>
