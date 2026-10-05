<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import type { LearningTrackDetail } from '../../api/types'
import { COVERAGE_LABEL, COVERAGE_TONE } from '../../presentation/learning'
import { stateFromGapStatus } from '../../presentation/language'
import { useLearningStore } from '../../stores/data'
import Icon from '../common/Icon.vue'
import SectionHeading from '../common/SectionHeading.vue'
import Skeleton from '../common/Skeleton.vue'
import StatusPill from '../common/StatusPill.vue'
import ContentList from './ContentList.vue'

/**
 * A learning track in teaching order: topics, their skills (with your score and the target) and the content that
 * teaches them. The order is the curriculum's; what to do first is still the mentor's decision (Today).
 */
const props = defineProps<{ track: string; title?: string }>()
const store = useLearningStore()
const detail = ref<LearningTrackDetail | null>(null)
const failed = ref(false)
const open = ref<string | null>(null)

async function load(): Promise<void> {
  failed.value = false
  try {
    detail.value = await store.track(props.track)
  } catch {
    failed.value = true
  }
}
onMounted(load)
watch(() => store.tracks.get(props.track), (fresh) => fresh && (detail.value = fresh))
const total = computed(() => detail.value?.content_count ?? 0)
</script>

<template>
  <section
    v-if="!failed"
    class="curriculum"
    :data-testid="`curriculum-${track}`"
    aria-labelledby="curriculum-title"
  >
    <SectionHeading
      id="curriculum-title"
      :title="title ?? 'Learning path'"
    >
      <span
        v-if="detail"
        class="muted tabular small"
      >{{ detail.done_count }} of {{ total }} items done</span>
    </SectionHeading>
    <Skeleton
      v-if="!detail"
      height="10rem"
      radius="var(--r-lg)"
    />
    <ol
      v-else
      class="topics"
    >
      <li
        v-for="(topic, i) in detail.topics"
        :key="topic.key"
        class="topic card-quiet"
        :data-testid="`topic-${topic.key}`"
      >
        <div class="topic-head">
          <span
            class="n"
            aria-hidden="true"
          >{{ i + 1 }}</span>
          <div class="topic-text">
            <h3>{{ topic.title }}</h3>
            <p class="muted small">
              {{ topic.summary }}
            </p>
          </div>
        </div>
        <ul class="skills">
          <li
            v-for="s in topic.skills"
            :key="s.key"
          >
            <RouterLink
              :to="{ name: 'skill', params: { key: s.key } }"
              class="name"
            >
              {{ s.name }}
            </RouterLink>
            <span class="muted small tabular">{{ s.score ?? '—' }} / {{ s.target_score ?? '—' }}</span>
            <StatusPill
              :state="s.status ? stateFromGapStatus(s.status) : 'calibration'"
              quiet
            />
            <StatusPill
              v-if="s.coverage_state !== 'FULL'"
              :state="COVERAGE_TONE[s.coverage_state]"
              :label="COVERAGE_LABEL[s.coverage_state]"
              quiet
            />
          </li>
        </ul>
        <button
          v-if="(detail.content[topic.key] ?? []).length"
          type="button"
          class="link-btn small"
          :aria-expanded="open === topic.key"
          :data-testid="`topic-toggle-${topic.key}`"
          @click="open = open === topic.key ? null : topic.key"
        >
          <Icon
            :name="open === topic.key ? 'chevron-down' : 'chevron-right'"
            :size="14"
          />
          {{ (detail.content[topic.key] ?? []).length }} learning items
        </button>
        <ContentList
          v-if="open === topic.key"
          :items="detail.content[topic.key] ?? []"
          :testid="`topic-content-${topic.key}`"
        />
      </li>
    </ol>
  </section>
</template>

<style scoped>
.curriculum { display: grid; gap: var(--s-3); }
.topics { display: grid; gap: var(--s-3); }
.topic { display: grid; gap: var(--s-3); }
.topic-head { display: flex; gap: var(--s-3); align-items: flex-start; }
.n { display: grid; place-items: center; width: 1.8rem; height: 1.8rem; border-radius: 50%; background: var(--accent-soft); color: var(--accent-text); font-weight: 700; font-size: var(--fs-sm); flex: none; }
.topic-text { display: grid; gap: var(--s-1); min-width: 0; }
h3 { font-size: var(--fs-md); }
.skills { display: grid; gap: var(--s-2); }
.skills li { display: flex; align-items: center; gap: var(--s-2) var(--s-3); flex-wrap: wrap; }
.name { font-weight: 600; flex: 1 1 14rem; min-width: 0; }
.link-btn { display: inline-flex; align-items: center; gap: var(--s-1); width: fit-content; text-decoration: none; }
.small { font-size: var(--fs-sm); }
</style>
