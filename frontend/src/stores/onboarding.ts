import { defineStore } from 'pinia'
import { computed, reactive, ref } from 'vue'
import { api } from '../api'
import { ApiError } from '../api/client'
import type { StartingProfile } from '../api/types'
import {
  buildOnboardingBody, draftFromProfile, EDIT_STEPS, emptyDraft, STEPS, stepErrors, type Draft, type Step,
} from '../practice/onboarding'
import { refreshDerivedData, useStartingProfileStore } from './data'

/** The starting-profile wizard: draft, current step and the final save. The server validates everything again. */
export const useOnboardingStore = defineStore('onboarding', () => {
  const draft = reactive<Draft>(emptyDraft())
  const step = ref<Step>('welcome')
  const editing = ref(false)
  const saving = ref(false)
  const errors = ref<string[]>([])

  const steps = computed<readonly Step[]>(() => (editing.value ? EDIT_STEPS : STEPS.filter((s) => s !== 'ready')))
  const index = computed(() => steps.value.indexOf(step.value))

  /** Load the draft from the server profile; an already completed profile opens in edit mode. */
  function start(profile: StartingProfile): void {
    Object.assign(draft, draftFromProfile(profile))
    editing.value = profile.onboarding.completed
    step.value = editing.value ? 'profile' : 'welcome'
    errors.value = []
  }

  function next(): boolean {
    errors.value = stepErrors(step.value, draft)
    if (errors.value.length) return false
    const target = steps.value[index.value + 1]
    if (target) step.value = target
    return true
  }

  function back(): void {
    errors.value = []
    const target = steps.value[index.value - 1]
    if (target) step.value = target
  }

  /** Saves profile + goal + the first-run flag. Returns true on success (then `step` is "ready" on first run). */
  async function save(): Promise<boolean> {
    errors.value = [...stepErrors('profile', draft), ...stepErrors('target', draft)]
    if (errors.value.length) return false
    saving.value = true
    try {
      await api.post('/onboarding/complete', buildOnboardingBody(draft))
      const store = useStartingProfileStore()
      await store.refresh()
      await refreshDerivedData()
      if (!editing.value) step.value = 'ready'
      return true
    } catch (caught) {
      if (caught instanceof ApiError) {
        const details = caught.details.errors as { loc: string[]; msg: string }[] | undefined
        errors.value = details?.map((d) => `${String(d.loc.at(-1)).replace(/_/g, ' ')}: ${d.msg}`) ?? [caught.message]
      } else {
        errors.value = [String(caught)]
      }
      return false
    } finally {
      saving.value = false
    }
  }

  return { draft, step, steps, index, editing, saving, errors, start, next, back, save }
})
