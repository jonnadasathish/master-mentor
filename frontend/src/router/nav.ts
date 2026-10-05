import { PREPARE_NAV, prepareRoute } from '../presentation/language'

/** Primary navigation. Developer/system tools are deliberately absent (they live under Settings → Developer). */
export interface NavItem {
  key: string
  label: string
  icon: string
  to: { name: string; params?: Record<string, string> }
  /** Path prefixes that mark this item active. '/' is matched exactly. */
  prefixes: string[]
  children?: NavItem[]
}

export const NAV_ITEMS: NavItem[] = [
  { key: 'today', label: 'Today', icon: 'today', to: { name: 'today' }, prefixes: ['/'] },
  {
    key: 'prepare',
    label: 'Prepare',
    icon: 'prepare',
    to: { name: 'prepare' },
    prefixes: ['/prepare', '/skills', '/log', '/baseline'],
    children: PREPARE_NAV.map((c) => ({
      key: c.slug,
      label: c.label,
      icon: c.icon,
      to: prepareRoute(c.slug),
      prefixes: [`/prepare/${c.slug}`],
    })),
  },
  { key: 'revise', label: 'Revise', icon: 'revise', to: { name: 'revision' }, prefixes: ['/revise'] },
  { key: 'mocks', label: 'Mocks', icon: 'mocks', to: { name: 'mocks' }, prefixes: ['/mocks'] },
  { key: 'progress', label: 'Progress', icon: 'progress', to: { name: 'progress' }, prefixes: ['/progress', '/review'] },
  { key: 'roadmap', label: 'Roadmap', icon: 'roadmap', to: { name: 'roadmap' }, prefixes: ['/roadmap'] },
  { key: 'settings', label: 'Settings', icon: 'settings', to: { name: 'settings' }, prefixes: ['/settings'] },
]

export function isActive(item: NavItem, path: string): boolean {
  return item.prefixes.some((p) => (p === '/' ? path === '/' : path === p || path.startsWith(`${p}/`)))
}
