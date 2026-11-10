# Callzo Engineering Assessment

This repository contains the two tasks completed for the Callzo Software Engineer Intern take-home assessment.

## Repository structure

```text
Callzo/
├── task-1/
│   ├── app/
│   ├── tests/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── alembic.ini
│   ├── .env.example
│   └── README.md
│
├── task-2/
│   ├── src/
│   ├── public/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── docker-compose.yml
│   ├── .dockerignore
│   └── README.md
│
└── README.md
```

Each task is self-contained and has its own README with task-specific setup and implementation details.

## Task 1 — Webhook processing and usage metering

Task 1 is implemented as a Python service with a PostgreSQL-backed processing workflow and a separate worker.

The implementation covers:

- Webhook ingestion and request authentication.
- HMAC signature verification.
- Idempotent event handling.
- Durable event processing backed by PostgreSQL.
- Worker-based processing and retry handling.
- Usage metering and monthly cap handling.
- Reconciliation from stored events.
- API and worker deployment with PostgreSQL through Docker Compose.
- Automated tests.

See [`task-1/README.md`](task-1/README.md) for architecture, configuration, commands, and test instructions.

### Run Task 1

```bash
cd task-1
cp .env.example .env
# Edit .env and set the required local configuration values.
docker compose up -d --build
docker compose ps
```

Run the tests using the instructions in `task-1/README.md`.

## Task 2 — UI Usage Admin Console

Task 2 is a React and TypeScript admin console for browsing account usage, viewing usage summaries, and configuring account settings.

The implementation covers:

- Account table with pagination.
- Search, filtering, and sorting.
- Usage summary charts with independent error and retry handling.
- URL-synchronized table state.
- Account selection and background refresh behavior.
- Four-step account settings wizard.
- Draft restoration and step persistence through the supplied mock API.
- Nginx reverse proxy for same-origin `/api` requests.
- Dockerized frontend and mock API deployment.

Published frontend image:

`shauryasehgal/callzo-task2:latest`

See [`task-2/README.md`](task-2/README.md) for architecture, mock API behavior, Docker instructions, and development commands.

### Run Task 2

```bash
cd task-2
docker compose pull
docker compose up -d
docker compose ps
```

Open `http://localhost:3000`.

The supplied mock API image is ARM64. The Task 2 Compose configuration specifies `platform: linux/arm64`; hosts without ARM64 support may require compatible emulation or an ARM64 host.

## General notes

- Run each task independently from its own directory.
- Do not commit real `.env` files, passwords, access tokens, or other credentials.
- Use the task-specific `.env.example` and README instructions for local setup.
- Task 2 uses the assessment-provided mock API; it is not a separate production backend.
- The summary endpoint may deliberately return intermittent HTTP 500 responses. Task 2 handles this with an independent retry flow.
- The Task 2 settings API includes an intentional Step 2 validation quirk after a Step 4 draft exists. The frontend preserves drafts and displays the returned validation error rather than modifying the supplied API behavior.

## Assessment submission

Both tasks are included in this repository under separate folders. Refer to each task's README for its individual run instructions and implementation details.
