{{/*
Expand the name of the chart.
*/}}
{{- define "inferflow.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
Truncated to 63 chars because some Kubernetes name fields have those limits.
*/}}
{{- define "inferflow.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart label value (name-version).
*/}}
{{- define "inferflow.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels applied to every resource.
*/}}
{{- define "inferflow.labels" -}}
helm.sh/chart: {{ include "inferflow.chart" . }}
{{ include "inferflow.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels (used in matchLabels + podSelector — must remain stable).
*/}}
{{- define "inferflow.selectorLabels" -}}
app.kubernetes.io/name: {{ include "inferflow.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Service account name.
*/}}
{{- define "inferflow.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "inferflow.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Fully qualified name for the api-gateway component.
*/}}
{{- define "inferflow.apiGateway.fullname" -}}
{{- printf "%s-api-gateway" (include "inferflow.fullname" .) }}
{{- end }}

{{/*
Fully qualified name for the worker component.
*/}}
{{- define "inferflow.worker.fullname" -}}
{{- printf "%s-worker" (include "inferflow.fullname" .) }}
{{- end }}

{{/*
Redis URL — points to the Bitnami Redis master service.
*/}}
{{- define "inferflow.redisUrl" -}}
{{- printf "redis://%s-redis-master:6379/0" .Release.Name }}
{{- end }}

{{/*
Qdrant URL — points to the Qdrant service.
*/}}
{{- define "inferflow.qdrantUrl" -}}
{{- printf "http://%s-qdrant:6333" .Release.Name }}
{{- end }}
