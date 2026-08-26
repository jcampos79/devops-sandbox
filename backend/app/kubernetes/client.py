"""Thin wrapper around the Kubernetes Python client for sandbox lifecycle
management. Every namespace/pod the backend creates goes through here so
the security posture (Pod Security Standard, dropped capabilities, no
token mount, no host access -- spec Sections 8/9) is enforced in exactly
one place, not re-implemented per call site.

Loads in-cluster config when running inside Kubernetes (the normal case);
falls back to a local kubeconfig for development if KUBECONFIG_PATH is set.
"""

import logging
from datetime import datetime, timezone

from kubernetes import client, config
from kubernetes.client.rest import ApiException

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger("sandbox_platform")


def _load_kube_config() -> None:
    if settings.kubeconfig_path:
        config.load_kube_config(config_file=settings.kubeconfig_path)
    else:
        config.load_incluster_config()


class KubernetesUnavailableError(Exception):
    """Raised when the Kubernetes API cannot be reached at all (spec
    Section 38: 'Kubernetes API unavailable')."""


class SandboxKubernetesClient:
    def __init__(self) -> None:
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            _load_kube_config()
            self._loaded = True

    @property
    def core_v1(self) -> client.CoreV1Api:
        self._ensure_loaded()
        return client.CoreV1Api()

    def create_sandbox_namespace(self, namespace: str) -> None:
        """Creates the namespace with the `baseline` Pod Security Standard
        enforced (spec Section 9)."""
        body = client.V1Namespace(
            metadata=client.V1ObjectMeta(
                name=namespace,
                labels={
                    "app.kubernetes.io/part-of": "sandbox-platform",
                    "app.kubernetes.io/managed-by": "sandbox-backend",
                    "pod-security.kubernetes.io/enforce": "baseline",
                    "pod-security.kubernetes.io/enforce-version": "latest",
                },
            )
        )
        try:
            self.core_v1.create_namespace(body)
        except ApiException as e:
            raise KubernetesUnavailableError(str(e)) from e

    def create_sandbox_pod(
        self,
        namespace: str,
        pod_name: str,
        image: str,
        shell: str,
    ) -> None:
        """Creates the sandbox Pod. Explicitly:
        - no ServiceAccount token mount (spec Section 8)
        - not privileged, no host networking/PID/IPC, no hostPath (Section 9)
        - allowPrivilegeEscalation: false, capabilities dropped (Section 9)
        - fixed resource profile only -- never user-supplied (Section 6)
        """
        security_context = client.V1SecurityContext(
            allow_privilege_escalation=False,
            capabilities=client.V1Capabilities(drop=["ALL"]),
        )
        resources = client.V1ResourceRequirements(
            requests={"cpu": settings.sandbox_cpu, "memory": settings.sandbox_memory},
            limits={"cpu": settings.sandbox_cpu, "memory": settings.sandbox_memory},
        )
        container = client.V1Container(
            name="sandbox",
            image=image,
            command=[shell],
            args=["-c", "sleep infinity"],
            security_context=security_context,
            resources=resources,
        )
        pod_spec = client.V1PodSpec(
            containers=[container],
            automount_service_account_token=False,
            host_network=False,
            host_pid=False,
            host_ipc=False,
            restart_policy="Never",
        )
        body = client.V1Pod(
            metadata=client.V1ObjectMeta(
                name=pod_name,
                namespace=namespace,
                labels={"app.kubernetes.io/part-of": "sandbox-platform"},
            ),
            spec=pod_spec,
        )
        try:
            self.core_v1.create_namespaced_pod(namespace=namespace, body=body)
        except ApiException as e:
            raise KubernetesUnavailableError(str(e)) from e

    def get_pod_phase(self, namespace: str, pod_name: str) -> str | None:
        """Returns the pod's phase (Pending/Running/...) or None if not found."""
        try:
            pod = self.core_v1.read_namespaced_pod_status(name=pod_name, namespace=namespace)
        except ApiException as e:
            if e.status == 404:
                return None
            raise KubernetesUnavailableError(str(e)) from e
        return pod.status.phase

    def delete_namespace(self, namespace: str) -> None:
        """Issues namespace deletion. Deletion is asynchronous -- this call
        returning does not mean the namespace is gone yet (spec Section
        14/46). Idempotent: a namespace already gone/going is not an error."""
        try:
            self.core_v1.delete_namespace(name=namespace)
        except ApiException as e:
            if e.status == 404:
                return
            raise KubernetesUnavailableError(str(e)) from e

    def namespace_exists(self, namespace: str) -> bool:
        """Used to confirm actual removal after delete_namespace() was
        issued (issue/confirm pattern, spec Section 14/46)."""
        try:
            self.core_v1.read_namespace(name=namespace)
        except ApiException as e:
            if e.status == 404:
                return False
            raise KubernetesUnavailableError(str(e)) from e
        return True


# Process-wide singleton; the underlying kubernetes client objects are
# lightweight and thread-safe to construct per call.
k8s = SandboxKubernetesClient()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
