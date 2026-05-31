---
name: ruby-on-rails
display_name: Ruby on Rails (server-rendered ERB)
role: source
---

## Detection

Strong signals:

- `Gemfile` at repo root with `gem "rails"` entry
- `config/routes.rb` present
- `app/controllers/`, `app/models/`, `app/views/` directory layout (classic Rails convention)
- `bin/rails` executable

Weak signals:

- `*.erb` template files under `app/views/`
- `config/database.yml`
- `Rakefile` at repo root
- `db/migrate/` with timestamped migrations
- Use of `sprockets` (asset pipeline) or `webpacker` (older JS bundling)

## Entry-point heuristic

Each controller class in `app/controllers/` is one entry point. Unit `id` = controller class name (e.g., `UsersController`); `kind = "controller"`. Include the controller `.rb` and the matching view directory under `app/views/<resource>/`.

For API-only Rails apps (`config.api_only = true` in `config/application.rb`), include only the controller `.rb`.

## Recommended target

For full-stack Rails apps (ERB views): `react-vite-ts` + a separate API (often `fastapi` if rewriting Ruby-to-Python feels natural, or keep Rails and add `react-vite-ts` as a separate UI calling Rails as JSON-only).

For API-only Rails apps already returning JSON: only the UI needs migration — pick any UI framework based on team preference.
