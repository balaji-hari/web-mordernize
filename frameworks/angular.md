---
name: angular
display_name: Angular (latest LTS)
role: target-ui
---

## Scaffold

```sh
npx @angular/cli@latest new apps/web-new --routing --style=scss --strict --skip-git
```

Node ≥ **20.11** required. Adjust `--style=` per `migration.md §3` styling choices (`css` / `scss` / `sass` / `less`).

### Wire to API

Angular doesn't read `.env`. Write `apps/web-new/src/environments/environment.ts`:
```ts
export const environment = { production: false, apiUrl: "http://localhost:<api-port>" };
```
And a sibling `environment.production.ts` with `production: true` plus a placeholder prod URL. Verify `angular.json` has the production `fileReplacements` block (CLI sets this by default).

## Test framework

`karma-jasmine` (Angular default). If `karma.conf.js` is missing from the CLI output (Angular 18+ no longer generates it in some configurations), install Karma manually:

```sh
npm i -D karma karma-jasmine karma-chrome-launcher karma-coverage jasmine-core @types/jasmine
npx karma init karma.conf.js
```

Then add `coverageReporter` to `karma.conf.js`:
```js
coverageReporter: {
  dir: require('path').join(__dirname, './coverage/'),
  reporters: [{ type: 'html' }, { type: 'text-summary' }, { type: 'json-summary' }]
}
```

Scripts: `"test": "ng test --watch=false --browsers=ChromeHeadless"`, `"test:coverage": "ng test --watch=false --code-coverage --browsers=ChromeHeadless"`. Headless Chrome required on CI.

Karma is on Angular's long deprecation runway — for greenfield Angular migrations consider `other: web-test-runner` or `other: vitest` in `migration.md §12` instead.

Test smoke: `npm run test -- --watch=false --browsers=ChromeHeadless`.

## Dev server

| Dev port | Install/activate | Dev command | URL |
|---|---|---|---|
| 4200 | `npm install` | `npm start` | http://localhost:4200 |

## Recommendation context

Natural target for: `angularjs-1` — closest mental model for teams coming from AngularJS (modules → modules, services → injectables, directives → components). Also a fit for any team with strong opinionation preferences who want Angular's batteries-included shape.

## Assets

Angular's static assets convention is `<scaffold.ui.path>/src/assets/`, NOT `<scaffold.ui.path>/public/`. The scaffold's "Copy legacy assets" step routes there automatically when the target UI is `angular`.
