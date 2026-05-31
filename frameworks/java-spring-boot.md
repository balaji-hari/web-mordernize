---
name: java-spring-boot
display_name: Java Spring Boot (1.x or 2.x — older versions being modernized)
role: source
---

## Detection

Strong signals:

- `@SpringBootApplication` annotation on a main class
- `application.properties` or `application.yml`
- `pom.xml` (or `build.gradle`) with `spring-boot-starter-*` dependencies

Weak signals:

- `mvnw` / `gradlew` wrapper scripts
- `Dockerfile` exposing port 8080

## Entry-point heuristic

Each `@Controller` or `@RestController` class is one entry point. Unit `id` = controller class name; `kind = "controller"`. For server-rendered apps (Thymeleaf), include the template under `src/main/resources/templates/`.

## Recommended target

If the legacy app is server-rendered (Thymeleaf + Spring MVC), migrate UI to `react-vite-ts` and keep Spring Boot 3 on the backend. If it's already a REST API, the migration may only need a UI front-end — pick `react-vite-ts` or `next-app-router`.
