"""Pydantic schema for engagements/<name>/engagement.yaml (deliverable D-01, FR-01)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _Strict(BaseModel):
    # Unknown keys are errors: a typo in YAML should fail fast, not be silently ignored.
    model_config = ConfigDict(extra="forbid")


class EngagementInfo(_Strict):
    name: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    customer: str
    description: str = ""


class LLMConfig(_Strict):
    provider: Literal["openai", "anthropic", "azure_openai", "bedrock", "vertex", "fake"] = "openai"
    model: str
    # None = don't send it; the model uses its own default. Some models (e.g. gpt-6-luna) reject the
    # parameter outright with HTTP 400, so it is opt-in per engagement (DC-016).
    temperature: float | None = Field(None, ge=0, le=2)
    max_steps: int = Field(8, ge=1, le=50)


class EmbeddingsConfig(_Strict):
    provider: Literal["openai", "azure_openai", "bedrock", "vertex", "fake"] = "openai"
    model: str
    dimensions: int = Field(1536, gt=0)


class VectorStoreConfig(_Strict):
    backend: Literal["pgvector", "faiss", "chroma"] = "pgvector"
    dsn: str


class RetrievalConfig(_Strict):
    top_k: int = Field(5, ge=1, le=50)
    hybrid: bool = True
    chunk_size: int = Field(800, ge=100)
    chunk_overlap: int = Field(100, ge=0)
    min_score: float = Field(0.3, ge=-1, le=1)  # below this best similarity -> "I don't know"

    @model_validator(mode="after")
    def _overlap_smaller_than_size(self) -> RetrievalConfig:
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("retrieval.chunk_overlap must be smaller than retrieval.chunk_size")
        return self


class DocumentSource(_Strict):
    type: Literal["local", "gcs", "s3", "azure_blob"] = "local"
    path: str
    include: list[str] = ["*.md", "*.pdf", "*.txt"]


class TableSource(_Strict):
    type: Literal["csv", "json", "sql"] = "csv"
    path: str
    target_schema: str = "ops"


class Sources(_Strict):
    documents: list[DocumentSource] = []
    tables: list[TableSource] = []


class SQLTool(_Strict):
    enabled: bool = True
    dsn: str
    schema_: str = Field("ops", alias="schema")
    tables: list[str] = []
    row_limit: int = Field(200, ge=1, le=10_000)


class OpenAPIAuth(_Strict):
    type: Literal["none", "bearer", "api_key"] = "none"
    token: str = ""


class OpenAPITool(_Strict):
    spec: str
    base_url: str
    auth: OpenAPIAuth = OpenAPIAuth()
    include_operations: list[str] = []
    require_approval: list[Literal["GET", "POST", "PUT", "PATCH", "DELETE"]] = [
        "POST", "PUT", "PATCH", "DELETE",
    ]


class Tools(_Strict):
    sql: SQLTool | None = None
    openapi: list[OpenAPITool] = []
    extensions: list[str] = []


class Guardrails(_Strict):
    pii_redaction: list[Literal["email", "phone", "ssn"]] = []
    injection_filter: bool = True
    log_prompts: bool = False


class Evals(_Strict):
    golden_set: str
    threshold: float = Field(0.85, ge=0, le=1)


class Deploy(_Strict):
    target: Literal["gcp_cloud_run", "kind", "compose"] = "compose"
    region: str = "us-east1"


class EngagementConfig(_Strict):
    engagement: EngagementInfo
    llm: LLMConfig
    embeddings: EmbeddingsConfig
    vector_store: VectorStoreConfig
    retrieval: RetrievalConfig = RetrievalConfig()
    sources: Sources = Sources()
    tools: Tools = Tools()
    guardrails: Guardrails = Guardrails()
    evals: Evals
    deploy: Deploy = Deploy()
