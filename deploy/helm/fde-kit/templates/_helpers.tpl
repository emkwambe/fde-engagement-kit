{{/* Shared names and blocks. A release called "fde" gives fde-api, fde-mock-erp, fde-postgres (runbook section 3). */}}

{{- define "fde.labels" -}}
app.kubernetes.io/part-of: fde-kit
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end -}}

{{- define "fde.secretName" -}}
{{- default (printf "%s-secrets" .Release.Name) .Values.existingSecret -}}
{{- end -}}

{{/* Pod and container hardening used by our own images (both run as uid 10001, see deploy/docker). */}}
{{- define "fde.podSecurity" -}}
runAsNonRoot: true
runAsUser: 10001
runAsGroup: 10001
fsGroup: 10001
seccompProfile: { type: RuntimeDefault }
{{- end -}}

{{- define "fde.containerSecurity" -}}
allowPrivilegeEscalation: false
readOnlyRootFilesystem: true
capabilities: { drop: ["ALL"] }
{{- end -}}

{{/* Environment shared by the API container and its init jobs. $(VAR) expands variables defined earlier in the list. */}}
{{- define "fde.apiEnv" -}}
- name: ENGAGEMENT
  value: {{ .Values.engagement | quote }}
- name: FAKE_LLM
  value: {{ .Values.models.fakeLlm | quote }}
- name: LLM_MODEL
  value: {{ .Values.models.llmModel | quote }}
- name: OPENAI_API_KEY
  valueFrom: { secretKeyRef: { name: {{ include "fde.secretName" . }}, key: openai-api-key, optional: true } }
- name: ERP_API_TOKEN
  valueFrom: { secretKeyRef: { name: {{ include "fde.secretName" . }}, key: erp-api-token } }
- name: ADMIN_TOKEN
  valueFrom: { secretKeyRef: { name: {{ include "fde.secretName" . }}, key: admin-token, optional: true } }
- name: ERP_API_URL
  value: "http://{{ .Release.Name }}-mock-erp:{{ .Values.mockErp.port }}"
{{- if .Values.postgres.enabled }}
- name: POSTGRES_PASSWORD
  valueFrom: { secretKeyRef: { name: {{ include "fde.secretName" . }}, key: postgres-password } }
- name: AGENT_RO_PASSWORD
  valueFrom: { secretKeyRef: { name: {{ include "fde.secretName" . }}, key: agent-ro-password } }
- name: DATABASE_URL
  value: "postgresql://fde:$(POSTGRES_PASSWORD)@{{ .Release.Name }}-postgres:5432/fde"
- name: AGENT_RO_DATABASE_URL
  value: "postgresql://agent_ro:$(AGENT_RO_PASSWORD)@{{ .Release.Name }}-postgres:5432/fde"
{{- else }}
- name: DATABASE_URL
  valueFrom: { secretKeyRef: { name: {{ include "fde.secretName" . }}, key: database-url } }
- name: AGENT_RO_DATABASE_URL
  valueFrom: { secretKeyRef: { name: {{ include "fde.secretName" . }}, key: agent-ro-database-url } }
- name: AGENT_RO_PASSWORD
  valueFrom: { secretKeyRef: { name: {{ include "fde.secretName" . }}, key: agent-ro-password } }
{{- end }}
{{- end -}}

{{- define "fde.configVolume" -}}
{{- if .Values.engagementConfig }}
- name: engagement-config
  mountPath: /app/engagements/{{ .Values.engagement }}/engagement.yaml
  subPath: engagement.yaml
  readOnly: true
{{- end }}
{{- end -}}
