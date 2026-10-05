<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import CalibrationStep from '../components/onboarding/CalibrationStep.vue'
import ContextStep from '../components/onboarding/ContextStep.vue'
import ProfileStep from '../components/onboarding/ProfileStep.vue'
import ReadyStep from '../components/onboarding/ReadyStep.vue'
import StackStep from '../components/onboarding/StackStep.vue'
import StepProgress from '../components/onboarding/StepProgress.vue'
import TargetStep from '../components/onboarding/TargetStep.vue'
import WelcomeStep from '../components/onboarding/WelcomeStep.vue'
import ErrorState from '../components/common/ErrorState.vue'
import Skeleton from '../components/common/Skeleton.vue'
import Logo from '../components/shell/Logo.vue'
import type { Step } from '../practice/onboarding'
import { useStartingProfileStore, useTodayStore } from '../stores/data'
import { useOnboardingStore } from '../stores/onboarding'

/** First run: a short, calm starting-profile flow. Opened again later it edits the profile instead. */
const TITLE: Record<Step, string> = {
  welcome: "Let's build your starting point.",
  profile: 'A little about you',
  target: 'Your target',
  stack: 'Your current stack',
  context: 'How do you see your skills?',
  calibration: 'How calibration works',
  ready: 'Your starting point is ready.',
}
const router = useRouter()
const profile = useStartingProfileStore()
const today = useTodayStore()
const store = useOnboardingStore()
const heading = ref<HTMLElement | null>(null)

const title = computed(() => (store.editing && store.step === 'profile' ? 'Edit your starting profile' : TITLE[store.step]))
const last = computed(() => store.index === store.steps.length - 1)
const loaded = computed(() => profile.data !== null)

async function load(): Promise<void> {
  await profile.refresh()
  if (profile.data) {
    store.start(profile.data)
    await today.baseline.ensure()
  }
}

async function primary(): Promise<void> {
  if (last.value) {
    const ok = await store.save()
    if (ok && store.editing) await router.push({ name: 'progress' })
    return
  }
  store.next()
}

onMounted(load)
watch(
  () => store.step,
  async () => {
    await nextTick()
    heading.value?.focus()
  },
)
</script>

<template>
  <div
    class="onboarding"
    data-testid="onboarding"
  >
    <header class="top">
      <span class="brand"><Logo /> <strong>Master Mentor</strong></span>
      <RouterLink
        v-if="store.editing"
        :to="{ name: 'settings' }"
        class="btn btn-ghost btn-sm"
      >
        Cancel
      </RouterLink>
    </header>

    <Skeleton
      v-if="!loaded && !profile.error"
      height="22rem"
      radius="var(--r-xl)"
    />
    <ErrorState
      v-else-if="!loaded"
      :error="profile.error"
      @retry="load"
    />

    <main
      v-else
      class="card"
    >
      <StepProgress
        v-if="store.step !== 'ready'"
        :steps="store.steps"
        :current="store.step"
      />
      <h1
        ref="heading"
        tabindex="-1"
        data-testid="ob-title"
      >
        {{ title }}
      </h1>

      <WelcomeStep v-if="store.step === 'welcome'" />
      <ProfileStep v-else-if="store.step === 'profile'" />
      <TargetStep
        v-else-if="store.step === 'target'"
        :roles="profile.data!.available_roles"
      />
      <StackStep v-else-if="store.step === 'stack'" />
      <ContextStep v-else-if="store.step === 'context'" />
      <CalibrationStep
        v-else-if="store.step === 'calibration'"
        :baseline="today.baseline.data"
      />
      <ReadyStep
        v-else
        :profile="profile.data!"
        :baseline="today.baseline.data"
      />

      <ul
        v-if="store.errors.length"
        class="errors"
        role="alert"
        data-testid="ob-errors"
      >
        <li
          v-for="e in store.errors"
          :key="e"
        >
          {{ e }}
        </li>
      </ul>

      <div
        v-if="store.step !== 'ready'"
        class="actions"
      >
        <button
          v-if="store.index > 0"
          type="button"
          class="btn btn-ghost"
          data-testid="ob-back"
          @click="store.back()"
        >
          Back
        </button>
        <span class="spacer" />
        <button
          v-if="store.step === 'context'"
          type="button"
          class="btn btn-ghost"
          data-testid="ob-skip"
          @click="last ? primary() : store.next()"
        >
          Skip this step
        </button>
        <button
          type="button"
          class="btn btn-primary btn-lg"
          :disabled="store.saving"
          data-testid="ob-next"
          @click="primary"
        >
          <template v-if="store.step === 'welcome'">
            Get started
          </template>
          <template v-else-if="last">
            {{ store.saving ? 'Saving…' : store.editing ? 'Save changes' : 'Save my starting point' }}
          </template>
          <template v-else>
            Continue
          </template>
        </button>
      </div>
    </main>
  </div>
</template>

<style scoped>
.onboarding { min-height: 100vh; padding: var(--s-5) var(--s-4) var(--s-7); max-width: 46rem; margin: 0 auto; display: grid; gap: var(--s-5); align-content: start; }
.top { display: flex; justify-content: space-between; align-items: center; }
.brand { display: flex; align-items: center; gap: var(--s-2); }
.card { display: grid; gap: var(--s-5); padding: var(--s-6); border-radius: var(--r-xl); }
h1 { font-size: var(--fs-2xl); letter-spacing: -0.025em; text-wrap: balance; outline: none; }
.actions { display: flex; align-items: center; gap: var(--s-3); padding-top: var(--s-3); border-top: 1px solid var(--border); }
.spacer { flex: 1; }
.errors { color: var(--critical-fg); display: grid; gap: var(--s-1); font-size: var(--fs-sm); }
@media (max-width: 767px) {
  .card { padding: var(--s-5) var(--s-4); }
  .actions { flex-wrap: wrap; }
  .actions .btn-primary { flex: 1 1 100%; order: -1; }
}
</style>
