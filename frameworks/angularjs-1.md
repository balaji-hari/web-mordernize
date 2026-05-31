---
name: angularjs-1
display_name: AngularJS 1.x (legacy Angular, pre-2.0)
role: source
---

## Detection

Strong signals:

- `angular.module('foo', [...])` calls in JavaScript files
- `ng-controller=`, `ng-app=`, `ng-repeat=` directives in HTML
- `package.json` with `"angular": "1.x"` (or `1.7.x` etc.)
- `bower.json` referencing angular 1.x (older AngularJS apps used Bower)

Weak signals:

- `$scope`, `$routeProvider`, `$http` references throughout JS
- Folder structure `app/controllers/`, `app/services/`, `app/directives/`

## Entry-point heuristic

Each `angular.module().controller('FooCtrl', ...)` is one entry point. Unit `id` = controller name (`FooCtrl`); `kind = "controller"`. Include the controller JS file plus its template HTML (resolved via `templateUrl` or inline `template:`).

## Recommended target

`angular` (modern Angular 17+) — closest mental model for teams used to AngularJS modules, services, and directives. The migration story (AngularJS → modern Angular) is well-documented and many concepts carry across. If the team wants to fully break from Angular, `react-vite-ts` is the alternate.
