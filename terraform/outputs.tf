output "platform_namespace" {
  description = "Namespace the sandbox-platform application is deployed into."
  value       = kubernetes_namespace.platform.metadata[0].name
}

output "backend_service_account" {
  description = "Name of the ServiceAccount FastAPI uses for sandbox lifecycle management."
  value       = kubernetes_service_account.backend.metadata[0].name
}

output "argocd_application_name" {
  description = "Name of the bootstrapped ArgoCD Application."
  value       = kubernetes_manifest.sandbox_platform_application.manifest.metadata.name
}
