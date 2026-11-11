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
    examples: list[str] = []  # example questions shown as buttons in the console (GET /engagement)


class LLMConfig(_Strict):
    provider: Literal["openai", "anthropic", "azure_openai", "bedrock", "vertex", "fake"] = "openai"
    model: str
    # None = don't send it; the model uses its own default. Some models (e.g. gpt-6-luna) reject the
    # parameter outright with HTTP 400, so it is opt-in per engagement (DC-016).
    temperature: float | None = Field(None, ge=0, le=2)
    max_steps: int = Field(8, ge=1, le=50)
    # The agent's system prompt (Sprint 01, kit-generic). A file path relative to the repo root, written for this
    # customer; {customer} is filled in. Unset = the kit's generic prompt. prompt_version labels the text in eval
    # reports: change the label whenever the text changes, because --resume only reuses results of the same label.
    system_prompt: str | None = None
    prompt_version: str | None = None
    # FAKE_LLM=1 only: an engagement-owned Python file with a class FakeAgent (core.agent.fake.ScriptedFake subclass)
    # that plays this engagement's script offline. Unset = the generic fake (searches documents, answers extractively).
    fake_script: str | None = None

    @model_validator(mode="after")
    def _prompt_has_version(self) -> LLMConfig:
        if self.system_prompt and not self.prompt_version:
            raise ValueError("llm.prompt_version is required when llm.system_prompt is set")
        return self


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
    # What the model is told the search_documents tool searches (the model picks tools by their descriptions).
    tool_description: str = ("Search the customer's policy documents. Returns passages with a 'ref' label; "
                             "cite facts as [ref].")

    @model_validator(mode="after")
    def _overlap_smaller_than_size(self) -> RetrievalConfig:
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("retrieval.chunk_overlap must be smaller than retrieval.chunk_size")
        return self


class DocumentSource(_Strict):
    type: Literal["local", "gcs", "s3", "azure_blob"] = "local"
    path: str
    include: list[str] = ["*.md", "*.pdf", "*.txt"]


ColumnType = Literal["text", "int", "number", "money", "timestamp", "date", "bool", "enum"]


class ColumnSpec(_Strict):
    """How one CSV column is cleaned before loading (core/ingest/etl.py). Unfixable values reject the row."""
    type: ColumnType = "text"
    required: bool | None = None       # None = type default: text/enum/bool optional ... see etl.clean_value
    values: list[str] = []             # enum: canonical spellings; input matched case-insensitively, trimmed
    lower: bool = False                # text: store lower case
    default: str | None = None         # text: value used when the cell is empty


class TableSpecConfig(_Strict):
    name: str = Field(pattern=r"^[a-z_][a-z0-9_]*$")
    file: str
    key: str
    columns: dict[str, ColumnSpec]
    references: dict[str, str] = {}    # column -> parent table (loaded earlier); unknown parents reject the row


class TableSource(_Strict):
    type: Literal["csv", "json", "sql"] = "csv"
    path: str
    target_schema: str = Field("ops", pattern=r"^[a-z_][a-z0-9_]*$")
    tables: list[TableSpecConfig] = []  # load order = list order (parents first)
    schema_sql: list[str] = []          # engagement-owned, idempotent DDL files applied by core.db.migrate
    seed_script: str | None = None      # engagement-owned Python file with generate(out_dir) -> {table: rows}


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
    # The fixed reply to a blocked direct-injection attempt (the model is never called).
    blocked_answer: str = ("I can't follow instructions that try to change my rules. I can help with questions "
                           "within my normal permissions.")


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
