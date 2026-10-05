import pluginVue from 'eslint-plugin-vue'
import tseslint from 'typescript-eslint'

export default tseslint.config(
  { ignores: ['dist/**', 'coverage/**', 'node_modules/**'] },
  ...tseslint.configs.recommended,
  ...pluginVue.configs['flat/recommended'],
  {
    files: ['**/*.vue'],
    languageOptions: { parserOptions: { parser: tseslint.parser } },
  },
  {
    rules: {
      // UI components render server read models; no business calculations (CLAUDE.md rule 4).
      'no-console': ['error', { allow: ['error'] }],
      'vue/multi-word-component-names': 'off',
    },
  },
)
