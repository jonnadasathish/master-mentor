import { defineComponent, h, type PropType, type VNode } from 'vue'
import { parseBlocks, type Inline } from '../../presentation/richtext'
import CodeBlock from './CodeBlock.vue'

/** Renders content text (paragraphs, lists, code, inline code, bold) as real elements. No HTML is interpreted. */
export default defineComponent({
  name: 'RichText',
  props: { text: { type: String as PropType<string>, required: true }, inline: { type: Boolean, default: false } },
  setup(props) {
    const inlines = (parts: Inline[]): (VNode | string)[] =>
      parts.map((p) => (p.kind === 'code' ? h('code', p.text) : p.kind === 'bold' ? h('strong', p.text) : p.text))
    return () => {
      const blocks = parseBlocks(props.text)
      if (props.inline && blocks.length === 1 && blocks[0]!.kind === 'p') return h('span', inlines(blocks[0]!.inlines))
      return h(
        'div',
        { class: 'rich' },
        blocks.map((b) => {
          if (b.kind === 'p') return h('p', inlines(b.inlines))
          if (b.kind === 'code') return h(CodeBlock, { language: b.language, code: b.code })
          return h(b.kind, b.items.map((item) => h('li', inlines(item))))
        }),
      )
    }
  },
})
