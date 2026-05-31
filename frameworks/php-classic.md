---
name: php-classic
display_name: PHP (classic / no framework — mixed HTML+PHP)
role: source
---

## Detection

Strong signals:

- `*.php` files with mixed HTML and PHP code (`<?php ... ?>` blocks inside HTML)
- No `composer.json` with Laravel, Symfony, CakePHP, or other major framework dependency
- `index.php` at document root

Weak signals:

- Inline `<?php echo $var ?>` patterns throughout
- `include 'header.php'` / `require 'config.php'` patterns
- `.htaccess` rewrite rules

## Entry-point heuristic

Each top-level `.php` file (excluding `header.php`, `footer.php`, `config.php`, and similar partials/includes) is one entry point. `kind = "page"`.

## Recommended target

`react-vite-ts` (UI) + a new API backend (pick `fastapi` for the smallest jump, or `spring-boot-3` / `dotnet-minimal-api` if the team's broader skills favor those).
