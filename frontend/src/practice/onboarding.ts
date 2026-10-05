import type { OnboardingBody, SelfReportClaim, StartingProfile } from '../api/types'

/** The wizard's draft (UI units) and its conversion to the API body. Validation here is for fast feedback only. */
export type Claims = Record<SelfReportClaim, string[]>

export interface Draft {
  name: string
  years: number | null
  currentRole: string
  previousRole: string
  roleKey: string | null
  targetDate: string
  budgets: number[]
  companyProfile: string
  technologies: string[]
  claims: Claims
}

export const DEFAULT_BUDGETS = [90, 90, 90, 90, 90, 75, 75]
export const MAX_TECHNOLOGIES = 30
export const STEPS = ['welcome', 'profile', 'target', 'stack', 'context', 'calibration', 'ready'] as const
export type Step = (typeof STEPS)[number]
/** Editing an existing profile skips the welcome, the calibration explanation and the "ready" screen. */
export const EDIT_STEPS: readonly Step[] = ['profile', 'target', 'stack', 'context']

export function emptyClaims(): Claims {
  return { strengths: [], weaknesses: [], never_studied: [], recently_studied: [] }
}

export function emptyDraft(): Draft {
  return {
    name: '', years: null, currentRole: '', previousRole: '', roleKey: null, targetDate: '', budgets: [...DEFAULT_BUDGETS],
    companyProfile: '', technologies: [], claims: emptyClaims(),
  }
}

/** Prefill from what the server already knows ("Owner" is the untouched default name, not a real one). */
export function draftFromProfile(p: StartingProfile): Draft {
  return {
    name: p.display_name === 'Owner' ? '' : p.display_name,
    years: p.experience.years,
    currentRole: p.experience.current_role ?? '',
    previousRole: p.experience.previous_role ?? '',
    roleKey: p.target?.role.profile_key ?? p.available_roles[0]?.profile_key ?? null,
    targetDate: p.target?.target_date ?? '',
    budgets: p.target ? [...p.target.weekday_budgets] : [...DEFAULT_BUDGETS],
    companyProfile: p.company_profile ?? '',
    technologies: [...p.technologies],
    claims: {
      strengths: [...p.self_report.strengths], weaknesses: [...p.self_report.weaknesses],
      never_studied: [...p.self_report.never_studied], recently_studied: [...p.self_report.recently_studied],
    },
  }
}

/** A group cannot be strong and weak, strong and never studied, or never studied and recently studied. */
const EXCLUSIVE: Record<SelfReportClaim, SelfReportClaim[]> = {
  strengths: ['weaknesses', 'never_studied'],
  weaknesses: ['strengths'],
  never_studied: ['strengths', 'recently_studied'],
  recently_studied: ['never_studied'],
}

export function toggleClaim(claims: Claims, claim: SelfReportClaim, group: string): Claims {
  const next: Claims = {
    strengths: [...claims.strengths], weaknesses: [...claims.weaknesses],
    never_studied: [...claims.never_studied], recently_studied: [...claims.recently_studied],
  }
  if (next[claim].includes(group)) {
    next[claim] = next[claim].filter((g) => g !== group)
    return next
  }
  next[claim].push(group)
  for (const other of EXCLUSIVE[claim]) next[other] = next[other].filter((g) => g !== group)
  return next
}

export function claimsOf(claims: Claims, group: string): SelfReportClaim[] {
  return (Object.keys(claims) as SelfReportClaim[]).filter((c) => claims[c].includes(group))
}

export function toggleTechnology(list: string[], name: string): string[] {
  const clean = name.trim()
  if (!clean) return list
  const found = list.findIndex((t) => t.toLowerCase() === clean.toLowerCase())
  if (found >= 0) return list.filter((_, i) => i !== found)
  return list.length >= MAX_TECHNOLOGIES ? list : [...list, clean]
}

export function weeklyMinutes(budgets: number[]): number {
  return budgets.reduce((a, b) => a + (Number(b) || 0), 0)
}

export function stepErrors(step: Step, d: Draft): string[] {
  const errors: string[] = []
  if (step === 'profile') {
    if (!d.name.trim()) errors.push('Tell us what to call you.')
    if (d.years !== null && (!Number.isInteger(d.years) || d.years < 0 || d.years > 60)) errors.push('Years of experience: 0 to 60.')
  }
  if (step === 'target') {
    if (d.budgets.some((b) => !Number.isFinite(Number(b)) || Number(b) < 0 || Number(b) > 600)) errors.push('Daily minutes: 0 to 600 each.')
    else if (weeklyMinutes(d.budgets) <= 0) errors.push('Give at least one day some time.')
  }
  return errors
}

export function buildOnboardingBody(d: Draft): OnboardingBody {
  const trim = (v: string) => v.trim() || null
  return {
    display_name: d.name.trim(),
    experience: { years: d.years, current_role: trim(d.currentRole), previous_role: trim(d.previousRole) },
    technologies: d.technologies,
    company_profile: d.companyProfile.trim(),
    self_report: { ...d.claims },
    goal: {
      target_date: d.targetDate || null,
      weekday_budgets: d.budgets.map((b) => Number(b) || 0),
      ...(d.roleKey ? { profile_key: d.roleKey } : {}),
    },
  }
}
