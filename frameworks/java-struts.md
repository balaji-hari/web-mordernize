---
name: java-struts
display_name: Java Struts (1.x or 2.x)
role: source
---

## Detection

Strong signals:

- `struts-config.xml` (Struts 1) or `struts.xml` (Struts 2) at classpath root
- Action classes extending `org.apache.struts.action.Action` (Struts 1) or annotated with `@Action` (Struts 2)

Weak signals:

- `*.action` URL mappings in deployment descriptor
- Struts taglibs (`<s:form>`, `<html:form>`) in JSPs

## Entry-point heuristic

Each top-level `.jsp` is one entry point; include its Struts action class in `files`. Unit `id` = action name (from struts config); `kind = "page"`.

## Recommended target

`react-vite-ts` paired with `spring-boot-3` (if keeping Java backend). Struts has been EOL for years — the migration is non-optional.
