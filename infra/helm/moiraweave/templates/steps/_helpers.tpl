{{/*
Fully qualified name for a pipeline step.
Usage: include "moiraweave.step.fullname" (dict "root" . "pipelineName" "audio-rag" "stepId" "transcribe")
*/}}
{{- define "moiraweave.step.fullname" -}}
{{- printf "%s-step-%s-%s" (include "moiraweave.fullname" .root) .pipelineName .stepId | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Selector labels for a specific pipeline step.
Usage: include "moiraweave.step.selectorLabels" (dict "root" . "pipelineName" "audio-rag" "stepId" "transcribe")
*/}}
{{- define "moiraweave.step.selectorLabels" -}}
app.kubernetes.io/name: {{ include "moiraweave.name" .root }}
app.kubernetes.io/instance: {{ .root.Release.Name }}
app.kubernetes.io/component: step
moiraweave.io/pipeline: {{ .pipelineName }}
moiraweave.io/step: {{ .stepId }}
{{- end }}
