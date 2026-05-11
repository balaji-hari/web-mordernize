<!--
  migration.md — web-modernize plugin configuration

  This file is the single source of truth for what your team is migrating, to what,
  and how. The web-modernize plugin reads it on every command.

  Fill in every section marked REQUIRED before running /web-modernize:plan.
  Sections marked AUTO are populated by /web-modernize:analyze; you can override them.
  Sections marked OPTIONAL may be left as "none" or "unchanged".

  Edit freely and commit with the rest of the repo.
-->

# Modernization Configuration

## 1. Project identity

- **Project name**: <!-- fill in -->
- **Owning team**: <!-- fill in -->
- **Primary contact**: <!-- email or Slack handle -->
- **Tracking ticket / epic**: <!-- URL -->
- **Target completion date**: <!-- YYYY-MM-DD -->

## 2. Source stack (AUTO — filled by `/web-modernize:analyze`)

<!--
  After running /web-modernize:analyze, this section will be populated. Edit if
  detection got something wrong; the plugin re-reads on every command.
-->

- **Primary framework**: <!-- e.g., aspnet-webforms, java-jsp-struts, angularjs-1.x -->
- **Detected version**:
- **Build tool / package manager**:
- **Notable libraries** (top 5):
- **Approximate LOC**:
- **Detection confidence** (0.0–1.0):

## 3. Target UI framework — REQUIRED

Pick one. Add a one-line rationale.

- **Framework**: <!-- react-vite-ts | next-app-router | vue3-vite | angular-17 | svelte-kit -->
- **Language**: <!-- TypeScript | JavaScript -->
- **State management**: <!-- e.g., Redux Toolkit, Zustand, Pinia, NgRx, "minimal" -->
- **Styling**: <!-- e.g., Tailwind, CSS Modules, MUI, Bootstrap -->
- **Rationale**:

### Legacy design system / custom CSS — OPTIONAL

Describe the legacy app's class-name conventions and where their CSS lives. If the app uses a custom design system, the migration agent will preserve those class names (or map them faithfully) rather than reducing them to generic utility classes. Leave blank to use heuristics (the agent will scan for prefix patterns like `esh-*`, `app-*`, `mat-*` automatically).

- **Class-name prefix(es)**: <!-- e.g., esh-, app-, acme-button-, mui- -->
- **Stylesheet locations**: <!-- e.g., Content/site.css, wwwroot/css/site.css, src/main/webapp/resources/css/ -->
- **Notes**: <!-- e.g., "Uses BEM, esh-card has padding+shadow+rounded+bg; reproduce as @apply component class in Tailwind" -->

### Asset directories — OPTIONAL

List paths in the legacy tree that contain images, fonts, favicons, or other static assets. `/web-modernize:scaffold` copies these into the target's `public/` (or Angular's `src/assets/`) so migrated pages don't break on missing assets. Leave blank to let `/scaffold` auto-detect (it scans for `Pics/`, `images/`, `Content/`, `wwwroot/`, `assets/`, `fonts/`, `static/`, `favicon.ico` by default).

- <!-- e.g., Pics/ -->
- <!-- e.g., Content/images/ -->
- <!-- e.g., wwwroot/lib/ -->
- <!-- e.g., favicon.ico -->

## 4. Target API framework — OPTIONAL

If your migration includes a new backend, fill this in. Otherwise set `Framework: none` and `/web-modernize:plan` will skip API work entirely.

- **Framework**: <!-- dotnet-minimal-api | spring-boot-3 | nestjs | fastapi | reuse-existing | none -->
- **Language**:
- **API style**: <!-- REST | GraphQL | gRPC | tRPC -->
- **Authentication scheme**: <!-- JWT | session-cookie | OAuth2 | OIDC -->
- **Rationale**:

## 5. Database — OPTIONAL

- **Disposition**: <!-- unchanged | schema-migrate-to-X | replatform-to-Y -->
- **Current DB**:
- **Target DB** (only if changing):
- **ORM / data access library** (target side): <!-- e.g., EF Core, TypeORM, Prisma, JPA, none -->
- **Data migration strategy** (only if replatforming):

## 6. Migration strategy — REQUIRED

Pick one. Write a paragraph explaining the trade-offs you weighed.

- **Strategy**: <!-- strangler-fig | big-bang | module-by-module -->
- **Rationale**:
- **Cutover plan** (one paragraph — when does legacy get retired?):

## 7. Auth provider — REQUIRED

Auth is migrated first as a distinct phase because it touches almost every other unit.

- **Current auth provider**: <!-- e.g., ASP.NET Forms Authentication, custom JWT, Spring Security, Azure AD, Okta -->
- **Target auth provider**:
- **Identity store** (where users live): <!-- e.g., AD, SQL table, Okta directory -->
- **Sessions** (target): <!-- cookie | bearer token | both -->
- **Notable claims / roles to preserve**:

## 8. Constraints

- **Must-keep URLs** (legacy URLs that must not break):
- **SEO concerns**:
- **Compliance regimes**: <!-- e.g., HIPAA, SOX, PCI-DSS, none -->
- **Browser support floor**: <!-- e.g., last 2 Chrome/Edge, IE11 required, etc. -->
- **Deployment target**: <!-- e.g., Azure App Service, AKS, on-prem IIS, AWS ECS -->
- **CI/CD platform**:
- **Other constraints**:

## 9. Out of scope

List items the plugin should **not** plan or migrate. Each line becomes an entry in `state.json.out_of_scope`.

- <!-- e.g., LegacyReportsModule -->
- <!-- e.g., FaxIntegration -->

## 9b. Unit rename map — OPTIONAL

Only relevant when re-running `/web-modernize:plan` after the unit list has shifted (a file moved, a controller was split, the analyzer picked a new id). Each entry tells `/plan` "this old unit became that new unit — carry the status, history, notes, and verification forward."

Format: one bullet per rename, `old_id → new_id`. Splits and merges are not auto-supported; perform those by editing `state.json` directly.

- <!-- LegacyLogin → LoginController -->
- <!-- OrdersListPage → OrderListPage -->

If `/plan` finds a previously-tracked unit that has progress (status beyond `pending`) but is no longer in the regenerated unit list, it will keep the unit and print a warning telling you to either add a mapping here or add it to §9 above. Pending units that fall off the plan are silently dropped.

## 10. Acceptance criteria — REQUIRED

The checklist `/web-modernize:verify` will use to call a unit (or the whole migration) "done."

- [ ] All in-scope pages render without runtime errors in target stack
- [ ] All in-scope API endpoints pass contract tests against legacy parity fixtures
- [ ] Auth flow end-to-end works (login, logout, session refresh)
- [ ] No legacy URLs return 404 (redirects or new routes in place)
- [ ] Lighthouse / accessibility / performance budgets met (specify thresholds below)
- [ ] <!-- add team-specific items -->

## 11. Risks & open questions

Free-form. Update as the migration progresses. The plugin reads this section as context but does not validate it.

- <!-- e.g., "Unknown how OrderProcessor uses HttpContext.Items — investigate before migrating" -->
