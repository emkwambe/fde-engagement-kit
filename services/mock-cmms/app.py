"""Mock CMMS (work-order system) for Coastline Climate Services (fictional): engagement #2's "someone else's system".

Run:   uv run python services/mock-cmms/app.py              (http://localhost:8200, docs at /docs)
Spec:  uv run python services/mock-cmms/app.py export-spec  (writes services/mock-cmms/openapi.yaml)

What it simulates
  * Work orders are READ-ONLY here (loaded from the CMMS export the seed script writes).
  * Dispatches can be CREATED: the one write the agent may make, after a human approves it.
  * Business rules the real CMMS enforces: after-hours fee at most $150; outside hours only on-call technicians;
    the technician's skill must match the equipment; one dispatch per open work order.
Deliberately independent of core/. Each operationId is the tool name the agent sees.
"""

import csv
import json
import os
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA = ROOT / "engagements" / "coastline-hvac" / "data" / "tables"
DEFAULT_DISPATCHES = Path(__file__).resolve().parent / "data" / "dispatches.json"
SKILL_BY_KIND = {"furnace": "residential", "heat pump": "residential", "central AC": "residential",
                 "rooftop unit": "commercial", "boiler": "commercial", "walk-in cooler": "refrigeration"}
TRUE = {"true", "t", "yes", "y", "1"}


# ----------------------------------------------------------------------------- models (the contract)
class WorkOrder(BaseModel):
    work_order_id: str = Field(examples=["WO-5040"])
    customer_id: str
    equipment_id: str | None = None
    equipment_kind: str | None = None
    priority: Literal["emergency", "routine"]
    status: str = Field(description="open, dispatched or closed")
    opened_at: datetime
    responded_at: datetime | None = None
    tech_id: str | None = None
    after_hours: bool
    summary: str | None = None


class DispatchCreate(BaseModel):
    """Fields the dispatch rules require (technician-dispatch.md#dispatch-rules)."""

    work_order_id: str = Field(pattern=r"^WO-\d+$", examples=["WO-5040"])
    tech_id: str = Field(pattern=r"^T-\d{2}$", examples=["T-02"])
    priority: Literal["emergency", "routine"]
    after_hours_fee_usd: float = Field(ge=0, le=150, description="From after-hours-fees.md; never above $150")
    reason: str = Field(min_length=5, max_length=500)


class Dispatch(DispatchCreate):
    dispatch_id: str = Field(examples=["DSP-0001"])
    created_at: datetime
    created_by: str = Field(description="Which client created it (from the X-Client header)")


class Health(BaseModel):
    status: Literal["ok"]
    work_orders_loaded: int
    dispatches: int


# ----------------------------------------------------------------------------- storage
def _ts(value: str) -> datetime | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        dt = datetime.strptime(value, "%m/%d/%Y %H:%M")  # the export mixes formats
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


class Store:
    def __init__(self, data_dir: Path, dispatches_file: Path, load_data: bool = True) -> None:
        self.dispatches_file = dispatches_file
        self._lock = threading.Lock()
        self.work_orders: dict[str, WorkOrder] = {}
        self.technicians: dict[str, dict[str, str]] = {}
        self.dispatches: dict[str, Dispatch] = {}
        if load_data:
            self._load(data_dir)
            if dispatches_file.exists():
                raw = json.loads(dispatches_file.read_text(encoding="utf-8"))
                self.dispatches = {d["dispatch_id"]: Dispatch.model_validate(d) for d in raw}

    def _load(self, data_dir: Path) -> None:
        if not (data_dir / "work_orders.csv").exists():
            raise RuntimeError(f"CMMS export not found in {data_dir}. Run: .\\tasks.ps1 seed -Engagement coastline-hvac")
        with (data_dir / "equipment.csv").open(newline="", encoding="utf-8") as f:
            kinds = {r["equipment_id"]: r["kind"] for r in csv.DictReader(f)}
        with (data_dir / "technicians.csv").open(newline="", encoding="utf-8") as f:
            self.technicians = {r["tech_id"]: r for r in csv.DictReader(f)}
        with (data_dir / "work_orders.csv").open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                self.work_orders[r["work_order_id"]] = WorkOrder(
                    work_order_id=r["work_order_id"], customer_id=r["customer_id"],
                    equipment_id=r["equipment_id"] or None, equipment_kind=kinds.get(r["equipment_id"]),
                    priority=r["priority"], status=r["status"], opened_at=_ts(r["opened_at"]),
                    responded_at=_ts(r["responded_at"]), tech_id=r["tech_id"] or None,
                    after_hours=r["after_hours"].strip().lower() in TRUE, summary=r.get("summary"))

    def create_dispatch(self, body: DispatchCreate, created_by: str) -> Dispatch:
        with self._lock:
            order = self.work_orders.get(body.work_order_id)
            if order is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, f"Work order {body.work_order_id} not found")
            if order.status != "open" or any(d.work_order_id == body.work_order_id for d in self.dispatches.values()):
                raise HTTPException(status.HTTP_409_CONFLICT, f"{body.work_order_id} is not open for dispatch")
            tech = self.technicians.get(body.tech_id)
            if tech is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, f"Technician {body.tech_id} not found")
            if order.after_hours and tech["on_call"].strip().lower() not in TRUE:
                raise HTTPException(status.HTTP_409_CONFLICT, f"{body.tech_id} is not on call (after-hours dispatch)")
            needed = SKILL_BY_KIND.get(order.equipment_kind or "")
            if needed and tech["skill"] != needed:
                raise HTTPException(status.HTTP_409_CONFLICT,
                                    f"{body.tech_id} is {tech['skill']}; {order.equipment_kind} needs {needed}")
            dispatch = Dispatch(**body.model_dump(), dispatch_id=f"DSP-{len(self.dispatches) + 1:04d}",
                                created_at=datetime.now(UTC), created_by=created_by)
            self.dispatches[dispatch.dispatch_id] = dispatch
            self.dispatches_file.parent.mkdir(parents=True, exist_ok=True)
            self.dispatches_file.write_text(json.dumps([d.model_dump(mode="json") for d in self.dispatches.values()],
                                                       indent=2), encoding="utf-8")
            return dispatch


def create_app(data_dir: Path | None = None, dispatches_file: Path | None = None, token: str | None = None,
               load_data: bool = True) -> FastAPI:
    store = Store(data_dir or Path(os.environ.get("CMMS_DATA_DIR", DEFAULT_DATA)),
                  dispatches_file or Path(os.environ.get("CMMS_DISPATCHES_FILE", DEFAULT_DISPATCHES)),
                  load_data=load_data)
    expected = token or os.environ.get("CMMS_API_TOKEN", "dev-token")
    app = FastAPI(title="Coastline CMMS (mock)", version="1.0.0",
                  description="Work orders and dispatches. Authenticate with `Authorization: Bearer <token>`.")
    app.state.store = store

    def require_token(authorization: Annotated[str | None, Header()] = None) -> None:
        if authorization != f"Bearer {expected}":
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing or invalid bearer token",
                                headers={"WWW-Authenticate": "Bearer"})

    Auth = Depends(require_token)

    @app.get("/health", operation_id="health", response_model=Health, tags=["system"])
    def health() -> Health:
        return Health(status="ok", work_orders_loaded=len(store.work_orders), dispatches=len(store.dispatches))

    @app.get("/work-orders/{work_order_id}", operation_id="getWorkOrder", response_model=WorkOrder,
             dependencies=[Auth], tags=["work orders"], summary="Get the live status of one work order")
    def get_work_order(work_order_id: str) -> WorkOrder:
        order = store.work_orders.get(work_order_id.strip().upper())
        if order is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Work order {work_order_id} not found")
        return order

    @app.get("/work-orders", operation_id="listWorkOrders", response_model=list[WorkOrder], dependencies=[Auth],
             tags=["work orders"], summary="List work orders, filtered by customer, status or priority")
    def list_work_orders(
        customer_id: Annotated[str | None, Query(description="Exact customer id, e.g. CU-004")] = None,
        status_is: Annotated[Literal["open", "dispatched", "closed"] | None, Query(alias="status")] = None,
        priority: Annotated[Literal["emergency", "routine"] | None, Query()] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
    ) -> list[WorkOrder]:
        rows = list(store.work_orders.values())
        if customer_id:
            rows = [w for w in rows if w.customer_id == customer_id.strip().upper()]
        if status_is:
            rows = [w for w in rows if w.status == status_is]
        if priority:
            rows = [w for w in rows if w.priority == priority]
        return rows[:limit]

    @app.post("/dispatches", operation_id="createDispatch", response_model=Dispatch, status_code=status.HTTP_201_CREATED,
              dependencies=[Auth], tags=["dispatches"],
              summary="Dispatch a technician to an open work order (a WRITE action: agents must get approval first)")
    def create_dispatch(body: DispatchCreate, x_client: Annotated[str | None, Header()] = None) -> Dispatch:
        return store.create_dispatch(body, created_by=x_client or "unknown")

    return app


def export_spec(path: Path) -> None:
    import yaml

    path.write_text(yaml.safe_dump(create_app(load_data=False).openapi(), sort_keys=False, allow_unicode=False),
                    encoding="utf-8")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "export-spec":
        out = Path(__file__).resolve().parent / "openapi.yaml"
        export_spec(out)
        print(f"wrote {out}")
    else:
        import uvicorn

        uvicorn.run(create_app(), host="127.0.0.1", port=int(os.environ.get("CMMS_PORT", "8200")))
