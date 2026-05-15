{{/*
Fully qualified name for a pipeline step.
Usage: include "inferflow.step.fullname" (dict "root" . "pipelineName" "audio-rag" "stepId" "transcribe")
*/}}
{{- define "inferflow.step.fullname" -}}
{{- printf "%s-step-%s-%s" (include "inferflow.fullname" .root) .pipelineName .stepId | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Selector labels for a specific pipeline step.
Usage: include "inferflow.step.selectorLabels" (dict "root" . "pipelineName" "audio-rag" "stepId" "transcribe")
*/}}
{{- define "inferflow.step.selectorLabels" -}}
app.kubernetes.io/name: {{ include "inferflow.name" .root }}
app.kubernetes.io/instance: {{ .root.Release.Name }}
app.kubernetes.io/component: step
inferflow.io/pipeline: {{ .pipelineName }}
inferflow.io/step: {{ .stepId }}
{{- end }}
