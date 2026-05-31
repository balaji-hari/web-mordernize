---
name: java-spring-mvc
display_name: Java Spring MVC (classic, not Boot)
role: source
---

## Detection

Strong signals:

- `@Controller` annotations on classes
- `applicationContext.xml` or `dispatcher-servlet.xml`
- `pom.xml` with `spring-webmvc` dependency (without `spring-boot-starter-web`)

Weak signals:

- `*.jsp` files alongside Spring deps
- `web.xml` declaring `DispatcherServlet`

## Entry-point heuristic

Each `@Controller` or `@RestController` class is one entry point. Unit `id` = controller class name; `kind = "controller"`. Include the controller class plus any associated JSP views.

## Recommended target

`react-vite-ts` (UI) + `spring-boot-3` (API). Keeps Java skills relevant on the backend while moving to a modern frontend.
