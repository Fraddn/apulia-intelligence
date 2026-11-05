import pluginVue from 'eslint-plugin-vue'
import { defineConfig } from 'eslint/config'
import globals from 'globals'
import tseslint from 'typescript-eslint'

export default defineConfig(
  { ignores: ['dist/**', 'node_modules/**'] },
  ...tseslint.configs.recommended,
  ...pluginVue.configs['flat/recommended'],
  {
    files: ['**/*.vue'],
    languageOptions: {
      parserOptions: { parser: tseslint.parser, extraFileExtensions: ['.vue'] },
      globals: globals.browser,
    },
    rules: {
      'vue/block-order': ['error', { order: ['template', 'script', 'style'] }],
      'vue/enforce-style-attribute': ['error', { allow: ['plain'] }],
      'vue/no-restricted-block': ['error', { element: 'style', message: 'Styles go only in the global <style> of App.vue.' }],
      'vue/max-attributes-per-line': 'off',
      'vue/singleline-html-element-content-newline': 'off',
      'vue/multi-word-component-names': 'off',
    },
  },
  {
    files: ['src/App.vue'],
    rules: { 'vue/no-restricted-block': 'off' },
  },
)
