{{/*
Chart name, respecting nameOverride.
*/}}
{{- define "sandbox-platform.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Fully qualified app name.
*/}}
{{- define "sandbox-platform.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s" (include "sandbox-platform.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{/*
Common labels.
*/}}
{{- define "sandbox-platform.labels" -}}
app.kubernetes.io/name: {{ include "sandbox-platform.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
{{- end -}}

{{/*
Component-scoped selector labels, e.g. (include "sandbox-platform.selectorLabels" (dict "context" . "component" "backend"))
*/}}
{{- define "sandbox-platform.selectorLabels" -}}
app.kubernetes.io/name: {{ include "sandbox-platform.name" .context }}
app.kubernetes.io/instance: {{ .context.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end -}}
