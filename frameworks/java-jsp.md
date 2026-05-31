---
name: java-jsp
display_name: Java JSP (Servlet-based, no framework)
role: source
---

## Detection

Strong signals:

- `*.jsp` files under `WEB-INF/` or `src/main/webapp/`
- `WEB-INF/web.xml` deployment descriptor
- `pom.xml` (or `build.gradle`) with `javax.servlet` dependency

Weak signals:

- JSTL taglibs (`<c:if>`, `<c:forEach>`)
- `src/main/webapp/WEB-INF/lib/` containing JSTL jars

## Entry-point heuristic

Each top-level `.jsp` (excluding includes) is one entry point. Unit `id` = JSP filename without extension; `kind = "page"`. Include any servlet class declared in `web.xml` `<servlet-mapping>` for that URL.

Skip files under `WEB-INF/jsp/includes/` or any directory named `includes/` — those are partial templates, not entry points.

## Recommended target

`react-vite-ts` — simplest path off a templating engine. If the team wants to keep Java on the backend, pair with `spring-boot-3` as the API.
