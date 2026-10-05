/**
 * The content text subset (CONTENT_AUTHORING_GUIDE §3): paragraphs, "- " / "1. " lists, fenced code blocks,
 * `inline code` and **bold**. Parsed into plain data; rendered with render functions (never as HTML).
 */
export type Inline = { kind: 'text' | 'code' | 'bold'; text: string }
export type Block =
  | { kind: 'p'; inlines: Inline[] }
  | { kind: 'ul' | 'ol'; items: Inline[][] }
  | { kind: 'code'; language: string; code: string }

const INLINE = /(`[^`\n]+`|\*\*[^*\n]+\*\*)/g

export function parseInline(text: string): Inline[] {
  const out: Inline[] = []
  for (const part of text.split(INLINE)) {
    if (!part) continue
    if (part.startsWith('`') && part.endsWith('`') && part.length > 1) out.push({ kind: 'code', text: part.slice(1, -1) })
    else if (part.startsWith('**') && part.endsWith('**') && part.length > 3) out.push({ kind: 'bold', text: part.slice(2, -2) })
    else out.push({ kind: 'text', text: part })
  }
  return out
}

export function parseBlocks(source: string): Block[] {
  const lines = source.replace(/\r\n/g, '\n').split('\n')
  const blocks: Block[] = []
  let paragraph: string[] = []
  const flush = () => {
    if (paragraph.length) blocks.push({ kind: 'p', inlines: parseInline(paragraph.join(' ')) })
    paragraph = []
  }
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i] ?? ''
    const fence = line.match(/^\s*```(\w*)\s*$/)
    if (fence) {
      flush()
      const code: string[] = []
      i++
      while (i < lines.length && !/^\s*```\s*$/.test(lines[i] ?? '')) code.push(lines[i++] ?? '')
      blocks.push({ kind: 'code', language: fence[1] || 'text', code: code.join('\n') })
      continue
    }
    const bullet = line.match(/^\s*-\s+(.*)$/)
    const numbered = line.match(/^\s*\d+\.\s+(.*)$/)
    if (bullet || numbered) {
      flush()
      const kind = bullet ? 'ul' : 'ol'
      const last = blocks[blocks.length - 1]
      const item = parseInline((bullet ?? numbered)![1] ?? '')
      if (last && last.kind === kind) last.items.push(item)
      else blocks.push({ kind, items: [item] })
      continue
    }
    if (!line.trim()) {
      flush()
      continue
    }
    const last = blocks[blocks.length - 1]
    if (!paragraph.length && last && (last.kind === 'ul' || last.kind === 'ol') && /^\s{2,}\S/.test(line)) {
      last.items[last.items.length - 1]!.push({ kind: 'text', text: ` ${line.trim()}` }) // wrapped list item
      continue
    }
    paragraph.push(line.trim())
  }
  flush()
  return blocks
}
