---
name: vue-2
display_name: Vue 2 (LTS ended Dec 2023)
role: source
---

## Detection

Strong signals:

- `package.json` with `"vue": "^2.x"` (or `~2.x`)
- `*.vue` single-file components using Options API exclusively (no `<script setup>`)
- `vue-router` `< 4.0` or `vuex` `< 4.0` in deps
- `main.js` calling `new Vue({...}).$mount('#app')` (Vue 2 instantiation pattern)

Weak signals:

- `vue.config.js` (Vue CLI 4/5 config file)
- `babel.config.js` with `@vue/cli-plugin-babel/preset`
- Use of `Vue.filter(...)`, `Vue.mixin(...)`, `Vue.directive(...)` global APIs

## Entry-point heuristic

Each top-level route definition in `src/router/index.js` (or `routes.js`) is one entry point. Unit `id` = route name (PascalCased component name); `kind = "component"`. Include the `.vue` SFC file plus any closely-coupled child components.

For non-routed apps, treat each top-level `.vue` file in `src/views/` (or `src/pages/`) as an entry point.

## Recommended target

`vue3-vite` is the natural target — preserves Vue knowledge, smallest migration delta (Composition API conversion, `Vue.x` global API removal, `v-model` semantics change). For teams who want to leave Vue entirely, `react-vite-ts` is the alternate.

Vue 2's official LTS ended in December 2023; security patches are now paid-only via NES (Never-Ending Support). Migration is urgent for any production app.
