---
name: spring-boot-3
display_name: Spring Boot 3
role: target-api
---

## Scaffold

Fetch a skeleton from `start.spring.io` with `web,actuator` and an **explicit `packageName`** (Initializr otherwise strips hyphens silently from `artifactId` and the generated base package will surprise the team):

```sh
curl -G https://start.spring.io/starter.tgz \
  -d type=maven-project -d language=java \
  -d javaVersion=21 -d packaging=jar \
  -d groupId=com.example -d artifactId=api-new -d name=api-new \
  -d packageName=com.example.apinew \
  -d dependencies=web,actuator \
  | tar -xzf - -C apps/api-new
```

Use `starter.tgz` (Windows boxes don't need unzip). Then under `src/main/java/<packageDir>/` write:

- A `HealthController` with `@RestController` + `@GetMapping("/health")` returning `Map.of("status", "UP")`. Actuator's `/actuator/health` does **not** match the smoke gate's `/health` — `agents/permanent-gotchas.md` explains why.
- A `CorsConfig` `@Configuration` class implementing `WebMvcConfigurer.addCorsMappings(...)` with the dev allow-list (`http://localhost:5173`, `http://localhost:3000`, `http://localhost:4200`).

## Test framework

`junit5` (default; brought by `spring-boot-starter-test`). Add the latest JaCoCo Maven plugin to `pom.xml` — resolve the current version from Maven Central (`org.jacoco:jacoco-maven-plugin`) at scaffold time, do not hardcode a version (JaCoCo gates on the bytecode version of analyzed classes and stale pins silently break coverage on newer JDKs):

```xml
<plugin>
  <groupId>org.jacoco</groupId>
  <artifactId>jacoco-maven-plugin</artifactId>
  <version><!-- latest from Maven Central --></version>
  <executions>
    <execution><goals><goal>prepare-agent</goal></goals></execution>
    <execution><id>report</id><phase>test</phase><goals><goal>report</goal></goals></execution>
  </executions>
</plugin>
```

Write `src/test/java/<base-package>/HealthControllerTests.java` using **`@SpringBootTest` + `@AutoConfigureMockMvc` + `MockMvc`** to assert `GET /health` returns 200. `MockMvc` is the right default for Spring Boot 3's MVC (Tomcat) stack:

```java
mockMvc.perform(get("/health")).andExpect(status().isOk());
```

Use `WebTestClient` only if the target is WebFlux (reactive) — it requires adding `spring-boot-starter-webflux` as a test dependency.

Test smoke: `./mvnw -q test` (fall back to `mvn -q test`).

## Verify commands

| Check | Command |
|---|---|
| lint | `./mvnw checkstyle:check` (or `./mvnw spotless:check` if Spotless is configured instead) |
| typecheck | `./mvnw compile` (the Java compiler is the type checker — there's no separate typecheck step) |
| test | `./mvnw test` (scope to one class with `-Dtest=${target_path}` when verifying a single unit) |

## Auth notes

Use **`BCryptPasswordEncoder`** from `spring-security-crypto`. Standard pattern — register as a `@Bean`, inject into the auth service, use `encode(...)` / `matches(...)`.

Seed dev users via a `@Profile("dev")` + `CommandLineRunner` at `src/main/java/<base-package>/devseed/DevUserSeeder.java`. Auto-runs on `./mvnw spring-boot:run -Dspring-boot.run.profiles=dev`.

Refer to `agents/permanent-gotchas.md` for cross-cutting auth rules.

## Data migration

Apply: `./mvnw flyway:migrate`
Status (read-only reachability probe): `./mvnw flyway:info`

## Dev server

| Dev port | Install/activate | Dev command | URL | Health check |
|---|---|---|---|---|
| 8080 | `./mvnw -q -DskipTests package` *(Windows: `mvnw.cmd -q -DskipTests package`)* | `./mvnw spring-boot:run` *(Windows: `mvnw.cmd spring-boot:run`)* | http://localhost:8080 | `curl http://localhost:8080/health` |

## Recommendation context

Natural fit for any Java-shop migration — pairs with any UI framework but works especially well with `react-vite-ts` (clean separation) or `angular` (consistent strict-typing posture).
