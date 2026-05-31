---
name: wordpress
display_name: WordPress (custom themes / plugins)
role: source
---

## Detection

Strong signals:

- `wp-config.php` at repo root (or `wp-config-sample.php`)
- `wp-content/themes/<custom-theme>/` with `functions.php` and `style.css`
- `wp-content/plugins/<custom-plugin>/` with main plugin file declaring `Plugin Name:`
- WordPress core files (`wp-load.php`, `wp-blog-header.php`) — typically NOT version-controlled by the team; their presence flags a full-WordPress repo

Weak signals:

- `style.css` opening with WordPress theme header (`Theme Name:`, `Author:`)
- `*.php` files using WordPress template tags (`get_header()`, `the_content()`, `wp_enqueue_script()`)
- `composer.json` (modern WordPress setups via Bedrock / Roots)

## Entry-point heuristic

For custom **themes**: each page template (`page.php`, `single.php`, `archive.php`, `front-page.php`, custom `page-*.php`) is one entry point. Unit `id` = template file name; `kind = "page"`.

For custom **plugins**: each shortcode handler, REST endpoint registration (`register_rest_route`), or admin page is one entry point.

## Recommended target

Two common migration patterns:

1. **Headless WordPress**: keep WordPress as the CMS/API (via WPGraphQL or REST API plugin), build the frontend in `next-app-router` or `astro`. Lowest editorial disruption.
2. **Full replatform**: migrate content to a different CMS (Sanity, Contentful, Strapi) and build the frontend in `next-app-router` or `astro`. Higher effort but eliminates WordPress maintenance.

`astro` is often the sweet spot for content-heavy WordPress sites — static-first, fast, SEO-friendly.
