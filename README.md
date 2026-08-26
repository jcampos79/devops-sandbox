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

This repository is being built incrementally. Current phase: **Phase 1**.

- [x] **Phase 1** — Repository structure, README, backend/frontend
      skeletons, Terraform/Ansible skeletons, Helm chart skeleton, ArgoCD
      Application definition.
- [ ] **Phase 2** — Database + local auth (users, password hashing, login).
- [ ] **Phase 3** — Credit ledger, balance calculation, admin credit mgmt,
      concurrency-safe spend.
- [ ] **Phase 4** — Kubernetes sandbox lifecycle (create/expire/terminate).
- [ ] **Phase 5** — Browser terminal (xterm.js + ticket-auth WebSocket + exec).
- [ ] **Phase 6** — REST API + API keys.
- [ ] **Phase 7** — Admin UI.
- [ ] **Phase 8** — Full GitOps deployment validation.
- [ ] **Phase 9** — Observability (metrics, logging, health endpoints).
- [ ] **Phase 10** — Documentation and final validation against acceptance
      criteria.

---

## Troubleshooting

Will be expanded as each phase lands. General starting points:

- `kubectl get applications -n argocd` — check ArgoCD sync status.
- `kubectl get pods -n <platform-namespace>` — check backend/frontend/DB pods.
- `kubectl get ns | grep sandbox-` — list currently active sandbox namespaces.
- Backend structured logs cover login, instance create/expire/terminate,
  namespace/pod creation, terminal connections, and Kubernetes/API errors —
  never passwords, API keys, hashes, or ticket tokens.
