import type { Router } from 'vue-router'
import { api } from '../api'
import type { LearningSession } from '../api/types'

/** Start (or resume: the server returns the active one) a learning session and open it. */
export async function openSession(
  router: Router,
  input: { skill: string; stage?: string | null; plan_item_id?: number; budget_minutes?: number },
): Promise<LearningSession> {
  const body: Record<string, unknown> = { skill: input.skill }
  if (input.stage) body.stage = input.stage
  if (input.plan_item_id !== undefined) body.plan_item_id = input.plan_item_id
  if (input.budget_minutes !== undefined) body.budget_minutes = input.budget_minutes
  const session = (await api.post<LearningSession>('/learning/sessions', body)).data
  await router.push({ name: 'session', params: { id: session.id } })
  return session
}
