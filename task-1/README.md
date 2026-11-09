# Callzo — Call Usage Metering Service

A webhook-driven backend for processing call lifecycle events, tracking account usage, enforcing monthly spending limits, and maintaining accurate usage records.

## Features

- HMAC-SHA256 webhook signature verification against the exact raw request body.
- Constant-time signature comparison.
- Idempotent webhook ingestion using unique event IDs.
- Call lifecycle processing: `call.started`, `call.ended`, and `call.failed`.
- Handling of duplicate, delayed, and out-of-order events.
- PostgreSQL-backed event queue with retries and dead-letter handling.
- Monthly usage tracking using integer-based cost calculations (cents).
- Hard monthly spending cap with authorization reservations.
- Usage reconciliation from stored webhook events.
- Bearer-token authentication for account APIs.
- Docker Compose deployment with PostgreSQL, API, and background worker.
- Health and readiness endpoints.

## Architecture

```text
             Incoming Webhook
                    |
                    v
          POST /webhooks/calls
                    |
                    v
          HMAC Signature Check
                    |
                    v
             Payload Validation
                    |
                    v
           PostgreSQL Event Store
                    |
                    v
           Background Event Worker
                    |
                    v
          Call Lifecycle Processing
                    |
          +---------+---------+
          |                   |
          v                   v
     Calls Table         Monthly Usage
          |                   |
          +---------+---------+
                    |
                    v
           Account Usage APIs
```

### Main components

- **FastAPI:** HTTP API and webhook ingestion.
- **PostgreSQL:** Persistent event storage, call records, account data, and monthly usage.
- **SQLAlchemy:** Database models and queries.
- **Alembic:** Database migrations.
- **Background worker:** Processes pending events and retries failed events.
- **Docker Compose:** Runs the API, worker, and database.

## Project Structure

```text
task-1/
├── app/
│   ├── api/
│   │   └── routes/
│   │       ├── accounts.py
│   │       └── webhooks.py
│   ├── core/
│   │   ├── auth.py
│   │   └── security.py
│   ├── db/
│   │   ├── base.py
│   │   └── session.py
│   ├── models/
│   ├── schemas/
│   ├── services/
│   │   ├── event_processor.py
│   │   ├── reconciliation_service.py
│   │   └── usage_service.py
│   ├── workers/
│   │   └── event_worker.py
│   └── main.py
├── migrations/
├── scripts/
├── tests/
├── .env.example
├── .gitignore
├── alembic.ini
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Requirements

For Docker deployment:

- Docker
- Docker Compose

For local development:

- Python 3.12+
- PostgreSQL 16+
- pip

## Configuration

Copy `.env.example` to `.env` and configure your local values. Do not commit `.env` or expose production secrets.

The default monthly cap of 1,000 cents is a configurable development value, not a fixed assessment requirement.

## Run with Docker Compose

Build and start the services:

```bash
docker-compose up --build -d
```

Check running services:

```bash
docker-compose ps
```

View API logs:

```bash
docker-compose logs -f api
```

View worker logs:

```bash
docker-compose logs -f worker
```

Check readiness:

```bash
curl http://localhost:8080/ready
```

Check health:

```bash
curl http://localhost:8080/health
```

The API is available at `http://localhost:8080`.

Interactive API documentation: `http://localhost:8080/docs`.

## Database Migrations

Migrations are automatically applied when the API container starts.

Apply migrations manually:

```bash
docker-compose exec api alembic upgrade head
```

Inspect the current migration:

```bash
docker-compose exec api alembic current
```

## API Endpoints

All account endpoints require:

```http
Authorization: Bearer <API_TOKEN>
```

### 1. Webhook ingestion

**POST** `/webhooks/calls`

Required headers:

```http
X-Signature: <hexadecimal HMAC-SHA256 signature>
Content-Type: application/json
```

The signature is calculated over the exact raw request body using the configured `WEBHOOK_SECRET`.

Supported event types:

- `call.started`
- `call.ended`
- `call.failed`

Example event:

```json
{
  "event_id": "evt_a1b2c3d4e5f6",
  "event_type": "call.started",
  "account_id": "acct_001",
  "call_id": "call_9f8e7d6c5b4a",
  "timestamp": "2026-11-01T10:15:30.123456+00:00",
  "duration_seconds": 0,
  "cost_cents": 0,
  "destination_country": "US"
}
```

Invalid or missing signatures are rejected before payload processing. Duplicate event IDs are handled idempotently.

### 2. Get monthly account usage

**GET** `/api/v1/accounts/{account_id}/usage?month=YYYY-MM-DD`

Returns monthly usage, reserved amount, cap, and remaining balance.

### 3. Authorize a call

**POST** `/api/v1/accounts/{account_id}/authorize-call`

Example request:

```json
{
  "call_id": "call_9f8e7d6c5b4a",
  "estimated_cost_cents": 100
}
```

The service checks the account's monthly spending limit and reserves the estimated amount when authorization is allowed. Repeated authorization requests for the same call and amount are handled idempotently.

### 4. Reconcile monthly usage

**POST** `/api/v1/accounts/{account_id}/reconcile`

Recomputes monthly usage from stored webhook events and updates the corresponding usage record.

## Monthly Cap Policy

The service uses a hard monthly spending cap.

- Call authorization checks actual usage plus outstanding reservations plus the requested amount.
- A request that would exceed the cap is denied.
- Authorized calls reserve their estimated cost.
- Reservations are released or settled when terminal call events are processed.
- Actual costs already incurred are recorded even if they cause usage to exceed the configured cap.
- Existing calls are not retroactively stopped when a cap is reached.
- Billing months are based on UTC timestamps.

All monetary values are stored as integer cents to avoid floating-point rounding errors.

## Event Processing and Retry Strategy

Webhook ingestion and event processing are separated:

1. The API validates the signature and event payload.
2. The event is persisted in PostgreSQL.
3. The background worker claims pending events.
4. Events are processed transactionally.
5. Failed events are scheduled for retry.
6. Retry delays use exponential backoff, capped at 300 seconds.
7. Events exceeding the configured maximum attempts are marked as dead-letter events.

The worker uses PostgreSQL row locking with `SKIP LOCKED` to support safe event claiming.

## Reconciliation

The reconciliation service rebuilds monthly usage from persisted webhook events. It provides a way to repair usage records if derived totals become inconsistent and is designed to be repeatable without incrementing totals multiple times.

## Testing

Run the automated test suite locally:

```powershell
python -m pytest tests/ -v
```

The test suite covers signature verification, payload validation, duplicate events, usage calculations, cap enforcement, worker processing and retries, account API authentication and authorization, and reconciliation.

Latest local test result:

```text
24 passed
```

## Simulator Scenarios

The local scenario runner is `scripts/simulate_scenarios.py`.

It exercises normal calls, duplicate events, out-of-order events, late events, malformed payloads, invalid signatures, and cap-burst authorization.

Run it with:

```powershell
python scripts/simulate_scenarios.py
```

The official simulator image was not run on the development machine because the available image architecture was incompatible with the machine's AMD64 architecture. The scenario checks described above were run using the local HTTP simulator.

## Health and Readiness

- `GET /health` checks application health.
- `GET /ready` checks application readiness, including database connectivity.

## Security Notes

- Webhook signatures are verified against raw request bytes.
- HMAC comparison uses `hmac.compare_digest`.
- Account API endpoints require bearer-token authentication.
- Secrets are loaded from environment configuration.
- Invalid webhook payloads are rejected before event persistence.
- Database operations use SQLAlchemy transactions.

## Design Decisions

- PostgreSQL is used as both the primary data store and durable event queue.
- Event IDs are unique to provide idempotent ingestion.
- Integer cents are used for monetary calculations.
- Event timestamps are used to handle delayed and out-of-order events.
- Background processing keeps webhook ingestion independent from business processing.
- Monthly usage is stored separately from individual call records for efficient account queries.
