/**
 * Optional communication skills (``comm.*``, D-087) carry the data component ``coding`` only because every skill
 * needs one. The UI must never present them as part of DSA or Coding & Execution, so everything that groups or
 * labels by component goes through these helpers.
 */
export const COMMUNICATION_LABEL = 'Communication'
export const COMMUNICATION_SECTION_LABEL = 'Communication & professional English (optional)'

export function isCommunicationSkill(key: string): boolean {
  return key.startsWith('comm.')
}

/** The label to show for a skill's area: Communication for ``comm.*``, else the component's own label. */
export function areaLabel(skillKey: string, component: string, labels: Record<string, string>): string {
  return isCommunicationSkill(skillKey) ? COMMUNICATION_LABEL : (labels[component] ?? component)
}
