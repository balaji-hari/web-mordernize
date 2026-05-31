---
name: django
display_name: Django (server-rendered Python templates)
role: source
---

## Detection

Strong signals:

- `manage.py` at repo root
- `settings.py` (or `<project>/settings/`) declaring `INSTALLED_APPS` with `"django.contrib.admin"` or similar
- `urls.py` with `urlpatterns = [...]`
- `requirements.txt` or `pyproject.toml` listing `Django` package

Weak signals:

- `*.html` templates under `templates/` or `<app>/templates/<app>/`
- `models.py` with `models.Model` subclasses
- `wsgi.py` / `asgi.py` entry points
- `django-admin` or `django-allauth` in deps

## Entry-point heuristic

Each view function or class-based view in any `<app>/views.py` is one entry point. Unit `id` = view name (e.g., `UserListView`); `kind = "controller"`. Include `views.py` plus any template under `<app>/templates/<app>/` referenced by `template_name`.

For Django REST Framework apps, include the matching serializer from `serializers.py` in `files`.

## Recommended target

For server-rendered Django apps: `react-vite-ts` + keep Django as the API (modernize to Django 5.x + DRF) OR `react-vite-ts` + `fastapi` (more aggressive rewrite).

For DRF-only API projects: only UI needs migration — any UI framework works.
