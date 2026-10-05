/** Display labels for Spec v2 vocabularies (values are sent unchanged to the server). */
export const OUTCOMES = [
  { value: 'PASS', label: 'Solved' },
  { value: 'PARTIAL', label: 'Partial' },
  { value: 'FAIL', label: 'Failed' },
] as const

export const MISTAKES = [
  { value: 'WRONG_PATTERN', label: 'Wrong pattern' },
  { value: 'NO_APPROACH', label: 'No approach' },
  { value: 'MISREAD_PROBLEM', label: 'Misread problem' },
  { value: 'EDGE_CASE_MISSED', label: 'Edge case missed' },
  { value: 'OFF_BY_ONE', label: 'Off by one' },
  { value: 'IMPLEMENTATION_BUG', label: 'Implementation bug' },
  { value: 'LANGUAGE_SYNTAX', label: 'Python syntax' },
  { value: 'DATA_STRUCTURE_API', label: 'Data-structure API' },
  { value: 'WRONG_COMPLEXITY', label: 'Wrong complexity' },
  { value: 'TIME_OVERRUN', label: 'Time overrun' },
] as const

export function outcomeLabel(value: string): string {
  return OUTCOMES.find((o) => o.value === value)?.label ?? value
}

export function mistakeLabel(value: string): string {
  return MISTAKES.find((m) => m.value === value)?.label ?? value
}

export function formatDuration(seconds: number | null): string {
  if (seconds === null) return '—'
  const minutes = Math.floor(seconds / 60)
  return `${minutes} min${seconds % 60 ? ` ${seconds % 60} s` : ''}`
}

export function hintsLabel(count: number): string {
  return `${count} ${count === 1 ? 'hint' : 'hints'}`
}
