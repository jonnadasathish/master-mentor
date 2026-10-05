<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import EmptyState from '../components/common/EmptyState.vue'
import ErrorState from '../components/common/ErrorState.vue'
import Icon from '../components/common/Icon.vue'
import PageHeader from '../components/common/PageHeader.vue'
import Skeleton from '../components/common/Skeleton.vue'
import CategoryCard from '../components/skills/CategoryCard.vue'
import { PREPARE_CATEGORIES } from '../presentation/language'
import { summarizeCategory } from '../presentation/prepare'
import { useReadinessStore, useSkillsStore, useTodayStore } from '../stores/data'

const skills = useSkillsStore()
const readiness = useReadinessStore()
const today = useTodayStore()

const loaded = computed(() => skills.data !== null && readiness.data !== null)
const error = computed(() => skills.error ?? readiness.error)
const cards = computed(() =>
  PREPARE_CATEGORIES.map((category) => ({
    category,
    summary: summarizeCategory(category, skills.list, readiness.data),
    to: category.slug === 'dsa' ? { name: 'dsa' } : { name: 'track', params: { slug: category.slug } },
  })),
)
const calibration = computed(() => today.baseline.data)

async function load(): Promise<void> {
  await Promise.all([skills.refresh(), readiness.refresh()])
}
onMounted(() => Promise.all([skills.ensure(), readiness.ensure(), today.baseline.ensure()]))
</script>

<template>
  <div class="page">
    <PageHeader
      eyebrow="Prepare"
      title="What would you like to work on?"
      description="Each area shows where you are, what is holding it back and the next best step."
    />

    <RouterLink
      v-if="calibration?.calibration_mode"
      :to="{ name: 'calibrate' }"
      class="calibrate"
      data-testid="finish-baseline"
    >
      <Icon
        name="crosshair"
        :size="18"
      />
      <span>
        <strong>Finish your baseline first.</strong>
        {{ calibration.battery_done }} of {{ calibration.battery_total }} assessments done. It makes everything below accurate.
      </span>
      <Icon
        name="arrow-right"
        :size="16"
      />
    </RouterLink>

    <div
      v-if="!loaded && !error"
      class="grid"
      aria-busy="true"
    >
      <Skeleton
        v-for="n in 5"
        :key="n"
        height="11rem"
        radius="var(--r-lg)"
      />
    </div>
    <ErrorState
      v-else-if="error"
      :error="error"
      @retry="load"
    />
    <EmptyState
      v-else-if="!skills.list.length"
      icon="book"
      title="The skill catalog isn't loaded yet."
      body="Load it from Settings → Developer, then come back."
    />
    <div
      v-else
      class="grid"
    >
      <CategoryCard
        v-for="c in cards"
        :key="c.category.slug"
        :category="c.category"
        :summary="c.summary"
        :to="c.to"
      />
    </div>
  </div>
</template>

<style scoped>
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(18rem, 1fr)); gap: var(--s-4); }
.calibrate {
  display: flex; align-items: center; gap: var(--s-3); padding: var(--s-4) var(--s-5); background: var(--calibration-bg); color: var(--calibration-fg);
  border: 1px solid var(--calibration-bd); border-radius: var(--r-lg); text-decoration: none;
}
.calibrate span { flex: 1; color: var(--text); }
.calibrate:hover { text-decoration: none; border-color: var(--calibration-fg); }
</style>
