# Final Submission Checklist

Status values: **DONE**, **PENDING**, or **MANUAL**. Items marked manual require the owner
to perform and confirm the action; no submission or publication was performed by this work.

## Repository and security

- [x] **DONE** Public-release audit document created: [PUBLIC_RELEASE_AUDIT.md](PUBLIC_RELEASE_AUDIT.md).
- [ ] **MANUAL** Initialize/use the intended Git repository.
- [ ] **MANUAL** Verify Git status, branches, tracked files, and commit history.
- [ ] **MANUAL** Scan all Git history for secrets and rotate any exposed credential.
- [ ] **MANUAL** Confirm the repository name satisfies the anonymous/random naming requirement.
- [ ] **MANUAL** Suggested neutral name: `northwind-eval-7f3c`.
- [ ] **MANUAL** Decide whether to add a license.

## Documentation

- [x] **DONE** README updated with architecture, methodology, links, setup, APIs, limitations,
  validation, and AI disclosure.
- [x] **DONE** [ARCHITECTURE.md](ARCHITECTURE.md) created.
- [x] **DONE** [DEPLOYMENT.md](DEPLOYMENT.md) created.
- [x] **DONE** [DATA_METHODOLOGY.md](DATA_METHODOLOGY.md) created.
- [x] **DONE** [DATA_VALIDATION.md](DATA_VALIDATION.md) created.
- [x] **DONE** [DEMO_VIDEO_SCRIPT.md](DEMO_VIDEO_SCRIPT.md) created.
- [x] **DONE** This checklist created.

## Application and deployment verification

- [ ] **MANUAL** Confirm the GitHub repository is public.
- [ ] **MANUAL** Verify the GitHub URL in an incognito/private browser window.
- [ ] **MANUAL** Verify frontend URL in an incognito/private browser window:
  <https://gridbricks-wind-frontend.vercel.app>
- [ ] **MANUAL** Verify backend URL in an incognito/private browser window:
  <https://gridbricks-wind-backend.vercel.app>
- [ ] **MANUAL** Check `/api/health`, `/api/metadata`, overview, series, accuracy, vintages,
  and provenance endpoints.
- [ ] **MANUAL** Confirm CORS and browser requests use `/api/...`.
- [ ] **MANUAL** Recheck January data counts and metrics against the validation report.
- [ ] **MANUAL** Run Docker Compose build, startup, health, proxy, and restart checks on a
  Docker-capable machine.

## Video and challenge submission

- [ ] **MANUAL** Record the two-part demonstration using [DEMO_VIDEO_SCRIPT.md](DEMO_VIDEO_SCRIPT.md).
- [ ] **MANUAL** Keep total video duration under 10 minutes.
- [ ] **MANUAL** Include both customer-facing and technical sections.
- [ ] **MANUAL** Upload the video as unlisted.
- [ ] **MANUAL** Verify the unlisted video from a second/private browser session.
- [ ] **MANUAL** Complete the challenge form:
  <https://forms.cloud.microsoft/r/Ljmf1aWESK>
- [ ] **MANUAL** Verify the submitted links and final description before sending.

## Final order

1. Complete Git and security/history checks.
2. Choose the neutral repository name and license decision.
3. Re-run automated and Docker validation.
4. Verify public frontend/backend behavior privately.
5. Publish the repository only after the preceding checks pass.
6. Record the video and verify it privately.
7. Complete and submit the challenge form.
