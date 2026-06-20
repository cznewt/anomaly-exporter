{{/* Chart name and version, for the chart label */}}
{{- define "anomaly-exporter.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end }}

{{/* Resource name, deduplicating release and chart name */}}
{{- define "anomaly-exporter.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end }}

{{/* Common labels */}}
{{- define "anomaly-exporter.labels" -}}
app.kubernetes.io/name: {{ default .Chart.Name .Values.nameOverride }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ include "anomaly-exporter.chart" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
{{- end }}

{{/* Selector labels */}}
{{- define "anomaly-exporter.selectorLabels" -}}
app.kubernetes.io/name: {{ default .Chart.Name .Values.nameOverride }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/* ConfigMap name: a user-provided existing one, or chart-generated */}}
{{- define "anomaly-exporter.configMapName" -}}
{{- if .Values.existingConfigMap -}}
{{ .Values.existingConfigMap }}
{{- else -}}
{{ include "anomaly-exporter.fullname" . }}-config
{{- end -}}
{{- end }}
