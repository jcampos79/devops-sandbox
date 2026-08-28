"""Prometheus metrics (spec Section 35). A plain module of counters/gauges
imported wherever an event happens -- no metrics middleware framework, no
separate exporter process. Scraped via the existing GET /metrics endpoint
(app/main.py); the cluster's existing Grafana can point at it directly.
"""

from prometheus_client import Counter, Gauge

sandbox_instances_created_total = Counter(
    "sandbox_instances_created_total",
    "Total sandbox instances successfully created",
    ["distribution"],
)

sandbox_instances_active = Gauge(
    "sandbox_instances_active",
    "Currently active (CREATING or RUNNING) sandbox instances",
)

sandbox_instances_expired_total = Counter(
    "sandbox_instances_expired_total",
    "Total sandbox instances that reached EXPIRED (ran out their full duration)",
)

sandbox_instances_terminated_total = Counter(
    "sandbox_instances_terminated_total",
    "Total sandbox instances that reached TERMINATED (ended early by user or admin)",
)

sandbox_credits_consumed_total = Counter(
    "sandbox_credits_consumed_total",
    "Total credits deducted for instance creation",
)

sandbox_api_requests_total = Counter(
    "sandbox_api_requests_total",
    "Total API requests handled",
    ["method", "path", "status_code"],
)

sandbox_instance_creation_errors_total = Counter(
    "sandbox_instance_creation_errors_total",
    "Total instance creation attempts that failed during Kubernetes provisioning",
)
