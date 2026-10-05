<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import Icon from '../components/common/Icon.vue'
import PageHeader from '../components/common/PageHeader.vue'
import CurriculumSection from '../components/learning/CurriculumSection.vue'
import { CURRICULUM_PAGES } from '../presentation/language'

/** A curriculum-only area (Python, practical engineering, projects): the learning path and how it is scored. */
const route = useRoute()
const page = computed(() => CURRICULUM_PAGES.find((p) => p.slug === route.params.slug) ?? CURRICULUM_PAGES[0])
const SCORED_IN: Record<string, string> = {
  python: 'Python skills are part of your DSA and coding readiness.',
  engineering: 'Practical engineering is part of your project and deep-dive readiness.',
  projects: 'Project milestones produce applied evidence; the defense is scored as a project walkthrough.',
}
</script>

<template>
  <div class="page">
    <PageHeader
      eyebrow="Prepare"
      :title="page.label"
      :description="SCORED_IN[page.slug]"
    >
      <RouterLink
        :to="{ name: 'log' }"
        class="btn"
      >
        <Icon
          name="plus"
          :size="16"
        /> Log practice
      </RouterLink>
    </PageHeader>
    <CurriculumSection
      :key="page.track"
      :track="page.track"
    />
  </div>
</template>
