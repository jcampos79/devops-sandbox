# Platform prerequisites and ArgoCD bootstrap for the sandbox platform.
#
# What this DOES:
#   - creates the platform namespace (frontend/backend/PostgreSQL live here)
#   - optionally installs ArgoCD (if install_argocd = true)
#   - registers an ArgoCD Application pointing at helm/sandbox-platform
#
# What this DOES NOT do:
#   - provision the Kubernetes cluster itself (control plane, nodes, CNI,
#     cluster storage infra, autoscaling)
#   - deploy the sandbox-platform application (that's ArgoCD + Helm's job)
#   - create per-user sandbox namespaces (that's FastAPI's job at runtime)

resource "kubernetes_namespace" "platform" {
  metadata {
    name = var.platform_namespace
    labels = {
      "app.kubernetes.io/part-of" = "sandbox-platform"
    }
  }
}

# RBAC prerequisite: the ServiceAccount FastAPI runs as, and the Role
# granting it exactly the sandbox-lifecycle permissions it needs. The
# ClusterRole is intentionally scoped to namespace/pod lifecycle verbs only
# -- see backend/app/kubernetes for what these permissions are used for.
resource "kubernetes_service_account" "backend" {
  metadata {
    name      = "sandbox-backend"
    namespace = kubernetes_namespace.platform.metadata[0].name
  }
}

resource "kubernetes_cluster_role" "backend_sandbox_lifecycle" {
  metadata {
    name = "sandbox-backend-lifecycle"
  }

  rule {
    api_groups = [""]
    resources  = ["namespaces"]
    verbs      = ["get", "list", "watch", "create", "delete"]
  }

  rule {
    api_groups = [""]
    resources  = ["pods", "pods/log", "pods/exec", "pods/attach", "pods/status"]
    verbs      = ["get", "list", "watch", "create", "delete"]
  }
}

resource "kubernetes_cluster_role_binding" "backend_sandbox_lifecycle" {
  metadata {
    name = "sandbox-backend-lifecycle"
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "ClusterRole"
    name      = kubernetes_cluster_role.backend_sandbox_lifecycle.metadata[0].name
  }

  subject {
    kind      = "ServiceAccount"
    name      = kubernetes_service_account.backend.metadata[0].name
    namespace = kubernetes_namespace.platform.metadata[0].name
  }
}

# Optional: install ArgoCD itself. Most environments will already have
# ArgoCD running; this is provided for a clean bootstrap of a fresh cluster.
resource "helm_release" "argocd" {
  count = var.install_argocd ? 1 : 0

  name             = "argocd"
  repository       = "https://argoproj.github.io/argo-helm"
  chart            = "argo-cd"
  version          = var.argocd_chart_version
  namespace        = var.argocd_namespace
  create_namespace = true
}

# Bootstrap the ArgoCD Application that points at this repo's Helm chart.
# From here on, ArgoCD reconciles the sandbox-platform application; this
# Terraform module does not manage it further.
resource "kubernetes_manifest" "sandbox_platform_application" {
  manifest = {
    apiVersion = "argoproj.io/v1alpha1"
    kind       = "Application"
    metadata = {
      name      = "sandbox-platform"
      namespace = var.argocd_namespace
    }
    spec = {
      project = "default"
      source = {
        repoURL        = var.git_repo_url
        targetRevision = var.git_target_revision
        path           = var.helm_chart_path
        helm = {
          valueFiles = ["values.yaml"]
          parameters = [
            {
              name  = "postgresql.persistence.storageClass"
              value = var.storage_class
            }
          ]
        }
      }
      destination = {
        server    = "https://kubernetes.default.svc"
        namespace = var.platform_namespace
      }
      syncPolicy = {
        automated = {
          prune    = true
          selfHeal = true
        }
        syncOptions = ["CreateNamespace=false"]
      }
    }
  }

  depends_on = [kubernetes_namespace.platform]
}
