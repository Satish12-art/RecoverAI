# RecoverAI

> **"Don't just tell merchants what revenue they lost. Recover it."**

AI-powered revenue recovery agent for merchants. Detects failed payments, diagnoses failure reasons, determines recoverability, selects recovery actions through a deterministic policy engine, and executes bounded recovery actions.

## Architecture

```
Razorpay Test Webhook / Synthetic Failed Payment
                         ↓
                 Event Normalizer
                         ↓
               Existing Payment Model
                         ↓
              Existing Recovery Case
                         ↓
       Eligibility Gate → Revenue Scorer
                         ↓
          AI Agent (Structured Recommendation)
                         ↓
      Deterministic Policy Engine (10 Rules)
                         ↓
             Bounded Tools (Retry / Message / Escalate)
                         ↓
                 Outcome Observer
                         ↓
               Verified Settled Cash
```

The LLM never directly modifies financial state or bypasses policy governance. All financial actions pass through deterministic policies.

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- npm 9+

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py
```

Backend runs at `http://localhost:8000`. API docs available at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:3000`.

---

## Razorpay Test Mode Setup

RecoverAI includes a dedicated, isolated Razorpay test-mode integration that ingests webhook events and feeds them into the authoritative RecoverAI recovery pipeline.

### Step-by-Step Setup

1. **Create / Use Razorpay Test Account**:
   - Log into the [Razorpay Dashboard](https://dashboard.razorpay.com/) in **Test Mode**.
2. **Configure Test Credentials** in `.env`:
   ```bash
   RECOVERY_MODE=simulation   # or razorpay_test
   RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxx
   RAZORPAY_KEY_SECRET=your_test_key_secret
   RAZORPAY_WEBHOOK_SECRET=your_test_webhook_secret
   ```
3. **Configure Webhook in Razorpay**:
   - Webhook URL: `https://your-domain.com/api/webhooks/razorpay` (or local ngrok tunnel)
   - Secret: Matches `RAZORPAY_WEBHOOK_SECRET`
   - Active Events: `payment.failed`, `payment.captured`, `payment.authorized`, `order.paid`
4. **Test Webhook Ingestion**:
   - In the frontend dashboard, use the **Razorpay Test-Mode Webhook Ingestion Console**.
   - Trigger a simulated `payment.failed` event.
   - Observe the resulting **Recovery Case** created in `/cases`.
   - Inspect the **Agent Trace** at `/cases/[id]` to see the AI diagnosis, policy approval checklist, and action execution.
   - Inspect the **Audit Trail** at `/audit` for immutable governance logging.

---

## Project Structure

```
RecoverAI/
├── frontend/          # Next.js 14 + TypeScript + Tailwind CSS
├── backend/           # FastAPI + SQLAlchemy + Pydantic
│   ├── app/
│   │   ├── agent/         # Bounded State Machine & LLM Client
│   │   ├── api/           # REST endpoints
│   │   ├── core/          # Config & DB Session
│   │   ├── evaluation/    # Frozen Benchmark & Metrics Suite
│   │   ├── integrations/  # Isolated Razorpay Test Mode Integration
│   │   ├── models/        # SQLAlchemy Models (7 tables)
│   │   ├── policies/      # 10 Deterministic Policy Rules & Message Templates
│   │   ├── schemas/       # Pydantic Schemas
│   │   ├── services/      # Eligibility, Risk, Scorer, Metrics, Simulation
│   │   └── tools/         # Bounded Read/Write Tools & Outcome Observer
│   └── tests/             # 185 Unit and Integration Tests
├── data/              # Synthetic dataset & Evaluation Artifacts
├── scripts/           # Generator, Seeder, Simulation, Evaluation CLI runners
└── README.md
```

---

## Running Tests

```bash
source backend/venv/bin/activate
pytest backend/tests -v
```

All 185 unit and integration tests pass.
