# Callzo Task 2 — UI Usage Admin Console

A React-based admin console for browsing account usage, monitoring usage trends, and configuring account settings through a four-step wizard. The application is served by Nginx and communicates with the supplied mock API through an Nginx reverse proxy.

## Features

- Account directory with server-side pagination.
- Search across account name, email, and company.
- Filters for status, country, plan, and signup-date range.
- Sorting by supported account and usage fields.
- Account selection independent of background table refreshes.
- Usage summary charts with independent loading, error, and retry handling.
- URL-synchronized table filters and pagination.
- Four-step account settings wizard:
  1. Account details — name and email.
  2. Subscription — plan and billing country.
  3. Usage limits — minutes and SMS caps.
  4. Integrations — webhook URL.
- Settings drafts loaded from and saved to the mock API.
- Final settings submission after all four steps have been saved.
- Dockerized frontend served through Nginx.

## Tech stack

- React, TypeScript, Vite
- Tailwind CSS, Recharts
- Nginx
- Docker and Docker Compose
- Supplied Callzo mock usage API

## Architecture

The browser loads the static React application from the frontend Nginx container. API requests use the `/api` path, which Nginx forwards to the `mock-api` service over the Docker Compose network.

```text
Browser
  |
  | HTTP :3000
  v
Frontend container (Nginx)
  |
  | /api/*
  v
Mock API container (mock-api:8001)
```

The browser does not need to resolve the Docker-internal hostname `mock-api`; only Nginx uses that hostname.

### State management

- **URL state:** table filters, sorting, and pagination are synchronized with query parameters so the current view can be shared or restored.
- **React component state:** account rows, totals, selected account IDs, loading/error states, summary data, and the currently edited account.
- **Settings state:** the wizard loads previously saved step data from the API and maintains the current draft while the wizard is open. Successful step saves are persisted by the mock API.
- **Independent summary state:** summary-chart loading and errors are managed separately from the accounts table so a summary failure does not block account browsing.

## Prerequisites

- Docker Engine
- Docker Compose plugin (`docker compose`)
- Network access to pull the mock API image and the published frontend image

## Run with Docker Compose

Published frontend image:

`shauryasehgal/callzo-task2:latest`

From the `task-2` directory:

```bash
docker compose pull
docker compose up -d
docker compose ps
```

Open `http://localhost:3000`.

The Compose configuration starts:

- `frontend` — the published React/Nginx image, exposed on port `3000`.
- `mock-api` — the supplied mock usage API, available internally on port `8001`.

The supplied mock API image is ARM64. The Compose file specifies `platform: linux/arm64`; hosts without ARM64 support may need compatible emulation or an ARM64 host.

### Verify the services

```bash
curl -I http://localhost:3000
curl http://localhost:3000/api/health
curl "http://localhost:3000/api/accounts?page=1&page_size=5"
```

The health endpoint should return an `ok` status and the account count. The summary endpoint can deliberately return HTTP 500 intermittently; the UI provides an independent retry action.

### Stop the application

```bash
docker compose down
```

This removes the Compose containers and network, but not the pulled images.

## Development

Install dependencies and start the Vite development server:

```bash
npm ci
npm run dev
```

The Vite development proxy forwards `/api` requests to `http://localhost:8001`. Make sure the supplied mock API is running and reachable on that host port during local development.

Build the production frontend:

```bash
npm run build
```

## Mock API behavior

The settings wizard uses the supplied mock API to load drafts, save individual steps, and submit completed settings.

The assessment API intentionally includes a validation quirk: after a Step 4 draft exists for an account, a Step 2 save can reject `billing_country` with a `billing_country is required` validation message even when a valid value is selected. The frontend displays the validation error and preserves the draft so the user can recover and save Step 4 again. This behavior is retained rather than changing the supplied API.

The summary endpoint also deliberately fails intermittently (approximately one in five requests according to the assessment specification). The chart handles this independently and exposes a retry action; the accounts table remains usable.

## Design decisions and scope

- Used native `fetch` for API calls and `URLSearchParams` for query construction.
- Kept table state in the URL where shareability and refresh restoration are useful.
- Kept account selection in React state so background data refreshes do not inherently reset it.
- Kept summary-chart state independent from table state.
- Used the supplied mock API rather than introducing a separate backend.
- Used Nginx as the production static server and API reverse proxy so browser code only needs same-origin `/api` requests.
- Prioritized the required account browsing, usage summary, and four-step settings workflow over additional features outside the assessment scope.

## Published image

`shauryasehgal/callzo-task2:latest`

## Notes

- Do not expose the mock API port publicly for the normal Compose deployment; Nginx reaches it over the internal Compose network.
- After changing frontend source code, rebuild and push the image, then pull the updated image before restarting the Compose deployment.
