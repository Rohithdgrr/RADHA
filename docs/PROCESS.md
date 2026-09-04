# 🔄 Development Process

This document defines the workflow for contributing to the AI Council project.

## Git Branching Strategy (GitFlow)

- **`main`**: Production-ready code. Only merged from `develop` after testing.
- **`develop`**: Integration branch for features. All feature branches branch off and merge back here.
- **`feature/xxx`**: Individual features or bug fixes.
- **`hotfix/xxx`**: Urgent production fixes.

## Commit Convention

We follow **Conventional Commits**:

```
<type>(<scope>): <subject>

<body>
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`

**Example**: `feat(backend): add consensus synthesis algorithm`

## Code Review Process

1.  Developer creates a feature branch and opens a Pull Request (PR) against `develop`.
2.  At least **one reviewer** must approve.
3.  All GitHub Actions checks must pass (tests, linting, build).
4.  PR is merged via **Squash and Merge**.

## Testing Requirements

| Test Type | Coverage Target | Tool |
| :--- | :--- | :--- |
| Unit Tests | 80% | Jest (frontend), Pytest (backend) |
| Integration Tests | Critical paths | Pytest + pytest-asyncio |
| E2E Tests | User flows | Playwright |

Run tests locally:

```bash
# Backend
cd backend && pytest

# Frontend
cd frontend && npm test

# E2E
npx playwright test
```

## CI/CD Pipeline (GitHub Actions)

1.  **On Push to `feature/*`**:
    - Run linting and unit tests.
2.  **On PR to `develop`**:
    - Run full test suite.
    - Build Docker image (dry-run).
3.  **On Merge to `develop`**:
    - Deploy to staging environment (if configured).
4.  **On Release**:
    - Merge `develop` to `main`.
    - Tag release (e.g., `v1.0.0`).
    - Deploy to production.

## Documentation Standards

- All public APIs must have OpenAPI (Swagger) documentation.
- All environment variables must be documented in `ENV.md`.
- Every feature PR must update relevant docs.

## Issue Tracking

- Use GitHub Issues with labels: `bug`, `feature`, `enhancement`, `documentation`, `help-wanted`.
- Milestones correspond to phases (Phase 1, Phase 2, etc.).
