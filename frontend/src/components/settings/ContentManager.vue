<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { api } from '../../api'
import { ApiError } from '../../api/client'
import type { ProjectRecord, PromptRecord, Story } from '../../api/types'
import { useErrorStore } from '../../stores/errors'

/** Stories (with competencies), projects and assessment prompts: content, never evidence by itself. */
const stories = ref<Story[]>([])
const projects = ref<ProjectRecord[]>([])
const prompts = ref<PromptRecord[]>([])
const skills = ref<{ key: string; component: string }[]>([])
const story = reactive({
  title: '', situation: '', task: '', action: '', result: '', metric: '', tradeoffs: '', learning: '', competency: '',
})
const project = reactive({ project_key: '', name: '', summary: '' })
const prompt = reactive({ prompt_key: '', skill: '', kind: 'CONCEPT_EXPLAIN', prompt_text: '' })
const message = ref('')
const errors = ref<string[]>([])
const errorStore = useErrorStore()

async function load(): Promise<void> {
  try {
    stories.value = (await api.get<Story[]>('/stories')).data
    projects.value = (await api.get<ProjectRecord[]>('/projects')).data
    prompts.value = (await api.get<PromptRecord[]>('/prompts')).data
  } catch (caught) {
    errorStore.report(caught, 'content')
  }
}

async function submit(path: string, body: unknown, done: string): Promise<void> {
  errors.value = []
  message.value = ''
  try {
    await api.post(path, body)
    message.value = done
    await load()
  } catch (caught) {
    if (caught instanceof ApiError) {
      const details = caught.details.errors as { loc: string[]; msg: string }[] | undefined
      errors.value = details?.map((d) => `${d.loc.at(-1)}: ${d.msg}`) ?? [caught.message]
    } else {
      errors.value = [String(caught)]
    }
  }
}

onMounted(async () => {
  await load()
  try {
    skills.value = (await api.get<{ key: string; component: string }[]>('/catalog/skills')).data
  } catch (caught) {
    errorStore.report(caught, 'content')
  }
})
</script>

<template>
  <section
    class="content"
    data-testid="content-manager"
  >
    <h2>Stories ({{ stories.length }})</h2>
    <ul>
      <li
        v-for="s in stories"
        :key="s.id"
      >
        {{ s.title }} — {{ (s.competencies ?? []).join(', ') }}{{ s.archived ? ' (archived)' : '' }}
      </li>
    </ul>
    <form
      class="card"
      data-testid="story-form"
      @submit.prevent="submit('/stories', { title: story.title, situation: story.situation, task: story.task,
                                            action: story.action, result: story.result, metric: story.metric || null,
                                            tradeoffs: story.tradeoffs || null, learning: story.learning || null,
                                            competencies: [story.competency] },
                              'Story saved: its revision item starts tomorrow.')"
    >
      <label>Title <input
        v-model="story.title"
        maxlength="160"
        data-testid="story-title"
      ></label>
      <label>Situation <textarea
        v-model="story.situation"
        rows="2"
      /></label>
      <label>Task <textarea
        v-model="story.task"
        rows="1"
      /></label>
      <label>Action <textarea
        v-model="story.action"
        rows="2"
      /></label>
      <label>Result <textarea
        v-model="story.result"
        rows="1"
      /></label>
      <label>Metrics <input
        v-model="story.metric"
        maxlength="255"
        placeholder="e.g. p95 latency 2 s → 300 ms"
      ></label>
      <label>Trade-offs <textarea
        v-model="story.tradeoffs"
        rows="1"
        placeholder="What you weighed and gave up"
      /></label>
      <label>Reflection <textarea
        v-model="story.learning"
        rows="1"
        placeholder="What you learned or would do differently"
      /></label>
      <label>Main competency
        <select
          v-model="story.competency"
          data-testid="story-competency"
        >
          <option value="">Choose…</option>
          <option
            v-for="s in skills.filter((x) => x.component === 'behavioral')"
            :key="s.key"
            :value="s.key"
          >{{ s.key }}</option>
        </select>
      </label>
      <button type="submit">
        Add story
      </button>
    </form>

    <h2>Projects ({{ projects.length }})</h2>
    <ul>
      <li
        v-for="p in projects"
        :key="p.id"
      >
        {{ p.project_key }} — {{ p.name }}
      </li>
    </ul>
    <form
      class="card"
      @submit.prevent="submit('/projects', { ...project }, 'Project saved.')"
    >
      <label>Key <input
        v-model="project.project_key"
        placeholder="payments-api"
      ></label>
      <label>Name <input v-model="project.name"></label>
      <label>Summary <textarea
        v-model="project.summary"
        rows="2"
      /></label>
      <button type="submit">
        Add project
      </button>
    </form>

    <h2>Assessment prompts ({{ prompts.length }})</h2>
    <ul>
      <li
        v-for="p in prompts"
        :key="p.id"
      >
        {{ p.source_key }} · {{ p.skill }} · {{ p.kind.toLowerCase().replace('_', ' ') }}
      </li>
    </ul>
    <form
      class="card"
      @submit.prevent="submit('/prompts', { ...prompt }, 'Prompt saved.')"
    >
      <label>Key <input
        v-model="prompt.prompt_key"
        placeholder="db-mvcc-1"
      ></label>
      <label>Skill
        <select v-model="prompt.skill">
          <option value="">Choose…</option>
          <option
            v-for="s in skills"
            :key="s.key"
            :value="s.key"
          >{{ s.key }}</option>
        </select>
      </label>
      <label>Kind
        <select v-model="prompt.kind">
          <option value="CONCEPT_EXPLAIN">concept explain</option>
          <option value="RECALL_QUIZ">recall quiz</option>
          <option value="SD_DESIGN">sd design</option>
          <option value="LLD_DESIGN">lld design</option>
        </select>
      </label>
      <label>Prompt <textarea
        v-model="prompt.prompt_text"
        rows="2"
      /></label>
      <button type="submit">
        Add prompt
      </button>
    </form>
    <p
      v-if="message"
      role="status"
    >
      {{ message }}
    </p>
    <ul
      v-if="errors.length"
      role="alert"
      class="errors"
    >
      <li
        v-for="e in errors"
        :key="e"
      >
        {{ e }}
      </li>
    </ul>
  </section>
</template>

<style scoped>
.card { display: grid; gap: var(--s-3); padding: var(--s-4) var(--s-5); background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-lg); max-width: 40rem; }
.content { display: grid; gap: var(--s-4); }
label { display: grid; gap: var(--s-1); }
.errors { color: var(--critical-fg); font-size: var(--fs-sm); }
</style>
