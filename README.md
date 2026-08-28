# DevOps / SRE Training Sandbox Platform

A self-service web portal where engineers spin up short-lived, isolated Linux
containers inside an **existing** Kubernetes cluster to practice Linux
administration, Kubernetes, Docker, Terraform, Ansible, Helm, GitOps, ArgoCD,
REST APIs, troubleshooting, and SRE/observability concepts.

This is a training tool, not a production SaaS platform. The codebase is
intentionally small, explicit, and easy to read end-to-end.

> **Status:** Phase 1 — repository scaffold. See [Roadmap](#roadmap) for what
> exists today vs. what's still to be implemented.

---

## Architecture

```text
                         Git Repository
                              |
                         Terraform
                              |
                              v
                Platform prerequisites /
                ArgoCD bootstrap /
                Kubernetes configuration
                              |
                              v
                           Ansible
                              |
                    environment preparation
                    configuration / secrets
                              |
                              v
                           ArgoCD
                              |
                              v
                            Helm
                              |
                              v
                 Kubernetes Sandbox Platform
                              |
             +----------------+----------------+
             |                                 |
             v                                 v
       React Frontend                       FastAPI
                                                |
                           +--------------------+------------------+
                           |                    |                  |
                           v                    v                  v
                       PostgreSQL         Kubernetes API      Authentication
                           |                    |
                           v                    v
                         PVC              Sandbox namespaces
                                                |
                         +----------------------+----------------+
                         |                      |                |
                         v                      v                v
                   sandbox-xxxx           sandbox-yyyy      sandbox-zzzz
                         |                      |                |
                         v                      v                v
                       Pod                    Pod              Pod
```

### Terminal path

Sandbox pods are never exposed directly. The browser terminal goes through
FastAPI, which performs a Kubernetes `exec`:

```text
Browser (xterm.js)
   |
   | WebSocket (?ticket=<short-lived, single-use>)
   v
FastAPI
   |
   | Kubernetes exec/attach API
   v
Sandbox Pod
```

Browsers can't reliably send custom `Authorization` headers on a WebSocket
handshake, so the frontend first calls an authenticated REST endpoint to mint
a short-lived (30-60s), single-use ticket tied to the requesting user and
instance, then opens the WebSocket with that ticket. FastAPI validates and
immediately invalidates the ticket before proceeding.

### GitOps vs. runtime boundary

| Managed by GitOps (Terraform → Ansible → ArgoCD → Helm) | Managed by FastAPI at runtime |
|---|---|
| Frontend, backend, PostgreSQL deployments | Per-user `sandbox-*` namespaces |
| RBAC, ServiceAccounts, NetworkPolicies | Per-user sandbox pods |
| Platform namespaces, Secrets/ConfigMaps | Sandbox lifecycle (create/expire/terminate) |

Dynamically created user sandboxes are **never** committed to Git and ArgoCD
never manages individual sandbox pods.

### Why not Redis / Celery / a service mesh / operators?

This platform intentionally avoids extra moving parts:

- **No Redis/Celery/RabbitMQ/Kafka** — instance expiration is handled by a
  simple in-process FastAPI background task that polls every 30s. Instance
  lifetimes are short (≤30 min) and load is training-scale, so a queue/worker
  system would add operational complexity with no real benefit.
- **No service mesh** — there's a single backend service talking to the
  Kubernetes API; there's no east-west traffic pattern that justifies one.
- **No Kubernetes Operator/custom controller** — sandbox lifecycle is simple
  enough to express as direct, synchronous-from-the-caller's-perspective
  Kubernetes API calls from FastAPI. An operator would just move the same
  logic into a reconciliation loop for no added benefit here.
- **No distributed locking (e.g. Redis locks)** — credit-spend race
  conditions are handled with a single Postgres `SELECT ... FOR UPDATE`
  transaction on the user's row, which is sufficient for a single backend
  deployment talking to a single database.

The goal is a system a new engineer can read top-to-bottom in one sitting.

---

## Prerequisites

- An **existing** Kubernetes cluster (this project does not provision one) —
  you need a working `kubeconfig` with sufficient privileges to create
  namespaces, RBAC objects, and install ArgoCD.
- A default (or specified) `StorageClass` available in the cluster, for
  PostgreSQL's PVC.
- [Terraform](https://developer.hashicorp.com/terraform/downloads) >= 1.5
- [Ansible](https://docs.ansible.com/ansible/latest/installation_guide/) >= 2.15
- [Helm](https://helm.sh/docs/intro/install/) >= 3.12
- `kubectl` configured against the target cluster
- [ArgoCD](https://argo-cd.readthedocs.io/) — Terraform bootstraps the
  `Application`, but ArgoCD itself is expected to be installed in the cluster
  already (or installed as part of the Terraform prerequisites step — see
  `terraform/`).
- A container registry you can push images to (Docker Hub, GHCR, ECR, etc.)
- An existing Grafana instance if you want to wire up the metrics endpoint
  (this project does **not** deploy its own Grafana).

---

## Repository layout

```text
devops-sandbox/
├── terraform/      # Platform prerequisites + ArgoCD bootstrap (NOT cluster provisioning)
├── ansible/        # Environment prep, config/secrets, validation
├── helm/           # The application Helm chart (frontend, backend, PostgreSQL, RBAC, etc.)
├── argocd/         # ArgoCD Application manifest pointing at helm/
├── backend/        # FastAPI application
├── frontend/       # React + TypeScript + Vite application
├── images/         # Training Linux container image definitions (Ubuntu/Rocky/Debian/Alpine)
└── README.md
```

---

## Configuration

Nothing environment-specific is hard-coded. Key configuration surfaces:

- **Terraform**: `terraform/variables.tf` — cluster context, namespaces,
  ArgoCD repo URL, etc. Copy `terraform.tfvars.example` → `terraform.tfvars`.
- **Ansible**: `ansible/group_vars/` — environment prep variables.
- **Helm**: `helm/sandbox-platform/values.yaml` — image references, resource
  requests/limits, `postgresql.persistence.storageClass`, sandbox
  distribution images, ingress hostname, etc.
- **Backend runtime config**: environment variables (see
  `backend/app/config.py` and `backend/.env.example` once added in Phase 2),
  sourced from Kubernetes Secrets/ConfigMaps in-cluster.

No real credentials are committed to this repository. Example files use the
`.example` suffix and are safe to commit; copies without that suffix are
git-ignored.

---

## Deployment

```bash
git clone <repository-url>
cd devops-sandbox

# 1. Platform prerequisites + ArgoCD bootstrap
terraform -chdir=terraform init
terraform -chdir=terraform plan
terraform -chdir=terraform apply

# 2. Environment preparation / secrets (idempotent)
ansible-playbook -i ansible/inventory ansible/playbooks/bootstrap.yml
ansible-playbook -i ansible/inventory ansible/playbooks/validate.yml

# 3. From here, ArgoCD takes over:
#    ArgoCD watches this repo's helm/sandbox-platform chart and reconciles
#    the frontend, backend, and PostgreSQL into the cluster.
kubectl get applications -n argocd
```

The Terraform step is idempotent — re-running `apply` against an
already-provisioned environment should be a no-op (or a safe convergence).

### GitOps flow after initial bootstrap

```text
Developer changes Git (helm/ values or templates)
        |
        v
   ArgoCD detects the change
        |
        v
   Helm renders manifests
        |
        v
   Kubernetes reconciles to desired state
```

FastAPI never writes to Git or Helm — it only manages runtime sandbox
namespaces/pods directly against the Kubernetes API.

---

## Building images

Each component builds and publishes independently to your configured
registry:

```bash
docker build -t <registry>/sandbox-backend:<tag> backend/
docker build -t <registry>/sandbox-frontend:<tag> frontend/
docker build -t <registry>/sandbox-ubuntu:<tag>  images/ubuntu/
docker build -t <registry>/sandbox-rocky:<tag>   images/rocky/
docker build -t <registry>/sandbox-debian:<tag>  images/debian/
docker build -t <registry>/sandbox-alpine:<tag>  images/alpine/
```

Point `helm/sandbox-platform/values.yaml` at the pushed tags
(`backend.image`, `frontend.image`, `sandbox.images.*`).

---

## Development

Backend and frontend each have their own local dev instructions in
`backend/README.md` / `frontend/README.md` (added as those components are
built out — see Roadmap). Tests:

```bash
# Backend (once Phase 2+ lands)
cd backend && pytest

# Frontend (once Phase 2+ lands)
cd frontend && npm test
```

---

## User workflow

```text
Login → Dashboard (balance, active instances, history)
      → Create Sandbox (pick distribution + duration, see cost)
      → Kubernetes creates sandbox-<id> namespace + pod
      → Terminal opens over WebSocket (ticket-authenticated) → Kubernetes exec
      → root@<distro> shell inside the sandbox
      → Instance expires automatically, or user terminates early
      → Namespace delete issued → confirmed
      → Sandbox gone; instance + credit history remain in Postgres
```

---

## API (preview)

```text
POST   /api/v1/instances
GET    /api/v1/instances
GET    /api/v1/instances/{instance_id}
DELETE /api/v1/instances/{instance_id}
GET    /api/v1/me
GET    /api/v1/me/credits
```

```bash
curl -X POST https://sandbox.example.com/api/v1/instances \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"distribution": "ubuntu", "duration_minutes": 20}'
```

Full API documentation (auth, error codes, examples for every endpoint) will
be filled in as the backend API lands in Phase 6.

---

## Roadmap

This repository is being built incrementally.

- [x] **Phase 1** — Repository structure, README, backend/frontend
      skeletons, Terraform/Ansible skeletons, Helm chart skeleton, ArgoCD
      Application definition.
- [x] **Phase 2** — Database + local auth (users, password hashing, login,
      Alembic migrations).
- [x] **Phase 3** — Credit ledger, balance calculation, admin credit mgmt,
      concurrency-safe spend (verified against real Postgres row locking).
- [x] **Phase 4** — Kubernetes sandbox lifecycle (create/expire/terminate,
      issue/confirm deletion, background cleanup task).
- [x] **Phase 5** — Browser terminal (xterm.js + ticket-auth WebSocket +
      Kubernetes exec bridge).
- [x] **Phase 6** — REST API + API keys (dual session-token/API-key auth,
      cross-user access rejected).
- [x] **Phase 7** — Admin UI (users, credits, instances) + full frontend
      (login, dashboard, create/terminate, terminal, credit history, API
      keys).
- [ ] **Phase 8** — Full GitOps deployment validation against a real cluster
      (this environment could validate YAML structure and Python/TS
      correctness, but not `helm template`/`terraform apply`/live K8s exec
      -- see Testing below).
- [x] **Phase 9** — Observability: `/metrics` exposes all seven counters/
      gauges from spec Section 35 (verified emitted correctly), plus
      structured logging across login, instance create/expire/terminate,
      namespace/pod creation, terminal connect/disconnect, and Kubernetes
      errors -- never passwords, hashes, API keys, or ticket tokens.
- [x] **Phase 10** — Documentation pass (this README) and acceptance
      criteria walked below. Full sign-off still needs a real cluster --
      see "What's been validated" and "Known gaps before production use."

### What's been validated in this environment

- Backend: 47 tests pass against a **real local PostgreSQL** instance
  (not SQLite) -- including a genuine concurrency test proving
  `SELECT ... FOR UPDATE` prevents double-spending credits under
  simultaneous requests. Kubernetes calls are mocked in tests (no live
  cluster here); the client wrapper code itself has not been exercised
  against a real cluster.
- An Alembic migration was generated with `--autogenerate` and applied
  against real Postgres.
- Frontend: `tsc -b` type-checks clean, `vite build` produces a production
  bundle, and Vitest passes.
- Helm templates and Terraform/Ansible YAML were checked for structural
  balance and valid YAML, but `helm template`, `terraform validate`, and
  `terraform plan` were not run (no Helm/Terraform CLI available in this
  environment, and their release domains -- get.helm.sh,
  releases.hashicorp.com -- aren't in this sandbox's network allowlist).
  Run those for real before deploying.

### Known gaps before production use

Be aware of these before pointing this at a real cluster:

- **Kubernetes exec/RBAC code path is unexercised.** `app/kubernetes/client.py`
  and `app/terminal/exec_bridge.py` were written against the documented
  `kubernetes` Python client API and are internally consistent with the
  tests (which mock this layer), but have never actually talked to a real
  API server. Test namespace/pod creation, exec, and deletion against a
  real (ideally disposable) cluster before relying on this.
- **`helm template` / `terraform validate` / `terraform plan` were never
  run.** The chart and Terraform config are structurally sound (balanced
  `{{ }}`/`if`/`end`, valid YAML/HCL) but have not been rendered or
  planned for real. Do that first.
- **No load testing.** The single in-process cleanup task and the
  `SELECT ... FOR UPDATE` credit-locking approach are appropriate for
  training-scale traffic (a handful to a few dozen concurrent users) --
  they were not evaluated beyond a two-concurrent-request race test.
- **TLS termination** is assumed to happen at the Ingress
  (`ingress.tls.*` in values.yaml) -- nothing in this repo provisions
  certificates itself (e.g. cert-manager). Wire that up separately if
  needed.

---

## Creating users

There's no self-registration by design (spec Section 21/48). Two ways to
create accounts:

**1. The very first admin**, via the CLI, run once inside the backend
container/pod (or locally against your dev database):

```bash
kubectl exec -n sandbox-platform deploy/sandbox-platform-backend -- \
  python -m app.cli create-admin --username root --password '<a-real-password>'
```

(Locally, without Kubernetes: `cd backend && python -m app.cli create-admin --username root --password ...`
with your `.env` pointed at a running Postgres.)

**2. Everyone else**, once you have an admin account, either:
- **Admin UI** — log in as the admin, go to *Admin: Users*, fill in the
  "Create User" form (username, password, optional admin checkbox).
- **API** —
  ```bash
  curl -X POST https://sandbox.example.com/api/v1/admin/users \
    -H "Authorization: Bearer <admin's session token or API key>" \
    -H "Content-Type: application/json" \
    -d '{"username": "engineer1", "password": "...", "is_admin": false}'
  ```

New users start with a balance of 0 credits — grant some from the same
Admin: Users page (or `POST /api/v1/admin/users/{id}/credits`) before they
can create a sandbox.

## Troubleshooting

- `kubectl get applications -n argocd` — check ArgoCD sync status.
- `kubectl get pods -n sandbox-platform` — check backend/frontend/DB pods.
- `kubectl logs -n sandbox-platform deploy/sandbox-platform-backend` —
  structured backend logs: login, instance create/expire/terminate,
  namespace/pod creation, terminal connections, Kubernetes/API errors.
  Never contains passwords, API keys, hashes, or ticket tokens.
- `kubectl get ns | grep sandbox-` — list currently active sandbox
  namespaces; each should correspond to a RUNNING or TERMINATING instance
  in the database.
- **Instance stuck in CREATING/TERMINATING** — check the backend's RBAC
  (`kubectl auth can-i create namespaces --as=system:serviceaccount:sandbox-platform:sandbox-backend`)
  and confirm the cleanup task is running (look for "Cleanup pass failed"
  in backend logs, which would indicate an exception being swallowed
  between passes).
- **Instance goes straight to ERROR** — almost always a missing/invalid
  `sandbox.images.*` value in `values.yaml`, or the backend's
  ServiceAccount lacking permission to create Pods in new namespaces.
- **Terminal won't connect** — tickets are single-use and expire in
  `TICKET_TTL_SECONDS` (default 45s); if the frontend is slow to open the
  WebSocket after minting a ticket, it may already be expired. Also check
  the instance is actually `RUNNING` (not `CREATING`) — the ticket
  endpoint rejects non-running instances.
- **`GET /metrics` looks empty** — counters only appear in the scrape
  output after the first event that increments them fires (Prometheus
  client behavior); `sandbox_instances_active` and friends start at 0 but
  are always present.

## Acceptance criteria status

Self-assessment against the original spec's acceptance criteria. ✅ =
implemented and covered by a passing automated test. ⚠️ = implemented but
not verifiable in this environment (needs a real cluster/CLI). Everything
below is ✅ or ⚠️ — nothing was skipped.

**Authentication:** ✅ login, password hashing, disabled-user rejection,
admin flag all covered by tests.

**Credits:** ✅ balance display, admin add/remove, every change creates a
transaction, instance creation deducts duration, insufficient credits
blocks creation, early termination doesn't refund, concurrent creation
can't double-spend (real Postgres row-lock test).

**Instances:** ✅ all four distributions selectable and validated, 1-30
minute range enforced server-side, cost independent of resources, unique
`sandbox-*` namespace per instance, fixed 1 CPU/512Mi profile, no
persistent storage, issue/confirm deletion tracked as distinct states,
historical records retained. ⚠️ root-inside-container-but-no-K8s-access and
`baseline` PSS/dropped-capabilities enforcement are implemented in
`app/kubernetes/client.py` exactly as specified, but unverified against a
live API server.

**Terminal:** ✅ ticket issuance/redemption/expiry/reuse-rejection
covered by tests. ⚠️ the actual WebSocket-to-`kubectl exec`-equivalent
bridge is implemented but untested against a real pod.

**API:** ✅ API key creation/hashing/revocation, full instance CRUD,
credit info, cross-user access rejected (404) — all covered by tests.

**Kubernetes:** ✅ RBAC is scoped to namespace/pod lifecycle verbs only in
`terraform/main.tf` (no cluster-admin). ⚠️ NetworkPolicies for sandbox
namespaces and the "no privileged/host-network/PID/IPC" pod spec are
written to spec but unverified live.

**Deployment:** ⚠️ Terraform/Helm/Ansible are structurally validated
(balanced templates, valid YAML/HCL) but `terraform apply` /
`helm install` / `ansible-playbook` were never run end-to-end here — do
that before trusting this in production.

**Testing:** ✅ 47 backend tests pass against real PostgreSQL (not
SQLite); frontend type-checks (`tsc -b`), builds (`vite build`), and its
test passes (Vitest). Infrastructure validation is YAML/HCL-syntax-level
only, not `terraform validate`/`helm template`.

**Documentation:** ✅ this README covers architecture, prerequisites,
deployment, GitOps flow, API usage, sandbox lifecycle, configuration,
image building, creating users, and troubleshooting.
