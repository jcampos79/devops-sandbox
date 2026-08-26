variable "kubeconfig_path" {
  description = "Path to a kubeconfig file for the EXISTING target Kubernetes cluster."
  type        = string
  default     = "~/.kube/config"
}

variable "kube_context" {
  description = "kubeconfig context to use. Empty string uses the current context."
  type        = string
  default     = ""
}

variable "platform_namespace" {
  description = "Namespace the sandbox platform (frontend/backend/PostgreSQL) is deployed into."
  type        = string
  default     = "sandbox-platform"
}

variable "sandbox_namespace_prefix" {
  description = "Prefix used for dynamically-created per-user sandbox namespaces. Must match backend/app/config.py."
  type        = string
  default     = "sandbox-"
}

variable "argocd_namespace" {
  description = "Namespace where ArgoCD is installed. This project assumes ArgoCD already exists in the cluster."
  type        = string
  default     = "argocd"
}

variable "install_argocd" {
  description = "If true, installs ArgoCD via Helm as a prerequisite. If false, assumes ArgoCD is already installed."
  type        = bool
  default     = false
}

variable "argocd_chart_version" {
  description = "ArgoCD Helm chart version, used only when install_argocd = true."
  type        = string
  default     = "7.7.11"
}

variable "git_repo_url" {
  description = "Git repository URL ArgoCD should track for the sandbox-platform Helm chart."
  type        = string
}

variable "git_target_revision" {
  description = "Git branch/tag/commit ArgoCD should track."
  type        = string
  default     = "main"
}

variable "helm_chart_path" {
  description = "Path within the Git repository to the sandbox-platform Helm chart."
  type        = string
  default     = "helm/sandbox-platform"
}

variable "storage_class" {
  description = "StorageClass to use for the PostgreSQL PVC. Empty string uses the cluster default."
  type        = string
  default     = ""
}
