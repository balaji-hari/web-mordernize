---
name: jquery-spaghetti
display_name: jQuery (no framework — ad-hoc DOM manipulation)
role: source
---

## Detection

Strong signals:

- jQuery usage (`$(...)`, `jQuery(...)`, `$.ajax(...)`) without any module pattern
- No Angular / React / Vue / Backbone detected
- No clear MVC structure (controllers, views, models separation)

Weak signals:

- `$(document).ready(function() {...})` blocks scattered across many files
- jQuery plugins loaded via `<script>` tags rather than imports
- HTML pages embedding `<script>` blocks with business logic inline

## Entry-point heuristic

Best-effort: each top-level HTML page is one entry point. `kind = "page"`. Include any inline `<script>` block plus referenced external `.js` files in `files`.

## Recommended target

`react-vite-ts` — the simplest target for teams making their first move into a framework-based UI. Component decomposition will be the main migration effort.
