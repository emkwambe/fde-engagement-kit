"""Mock ERP: a stand-in for the customer's legacy system (Day 2, part 1).

Run:   .\\tasks.ps1 erp            (http://localhost:8100, interactive docs at /docs)
Spec:  .\\tasks.ps1 erp-spec       (writes services/mock-erp/openapi.yaml)

What it simulates
  * A system we can only reach through its REST API, never its database.
  * Bearer-token auth on every business endpoint (401 without it).
  * Shipments are READ-ONLY (loaded from the customer's shipment export).
  * Tickets can be CREATED (the one write action the agent may take, after human approval).

Deliberately independent of core/: in a real engagement this is someone else's system.
The operationId of each endpoint is the tool name the agent will see (Day 2, part 2).
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
DEFAULT_SHIPMENTS = ROOT / "engagements" / "demo-logistics" / "data" / "tables" / "shipments.csv"
DEFAULT_TICKETS = Path(__file__).resolve().parent / "data" / "tickets.json"

ShipmentStatus = Literal["Delivered", "In transit", "Arrived at hub", "Out for delivery", "Delayed"]


# ----------------------------------------------------------------------------- models (the contract)
class Shipment(BaseModel):
    shipment_id: str = Field(examples=["SHP-2207"])
    order_id: str = Field(examples=["ORD-1207"])
    carrier: str
    origin: str | None = None
    destination: str | None = None
    last_scan_at: datetime | None = None
    last_status: str = Field(description="Free-text status from the last carrier scan")


class TicketCreate(BaseModel):
    """Fields required by the claims process (claims-process.md#required-ticket-fields)."""

    order_id: str = Field(pattern=r"^ORD-\d+$", examples=["ORD-1043"])
    customer_id: str = Field(pattern=r"^C-\d+$", examples=["C-007"])
    days_late: int = Field(ge=1, le=60)
    credit_percent: float = Field(gt=0, le=35, description="Never above the Platinum cap of 35%")
    credit_amount_usd: float = Field(gt=0, le=100_000)
    reason: str = Field(min_length=5, max_length=500)
    priority: Literal["P1", "P2", "P3", "P4"] = "P3"


class Ticket(TicketCreate):
    ticket_id: str = Field(examples=["TCK-0001"])
    status: Literal["open", "approved", "rejected", "closed"] = "open"
    created_at: datetime
    created_by: str = Field(description="Which client created it (from the X-Client header)")


class Health(BaseModel):
    status: Literal["ok"]
    shipments_loaded: int
    tickets: int


# ----------------------------------------------------------------------------- storage
class Store:
    """Shipments in memory (read-only); tickets in a small JSON file so they survive restarts."""

    def __init__(self, shipments_csv: Path, tickets_file: Path, load_data: bool = True) -> None:
        self.tickets_file = tickets_file
        self._lock = threading.Lock()
        self.shipments = self._load_shipments(shipments_csv) if load_data else {}
        self.tickets: dict[str, Ticket] = self._load_tickets() if load_data else {}

    @staticmethod
    def _parse_ts(value: str) -> datetime | None:
        value = (value or "").strip()
        if not value:
            return None
        try:
            dt = datetime.fromisoformat(value)
        except ValueError:
            dt = datetime.strptime(value, "%m/%d/%Y %H:%M")  # the legacy export mixes formats
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)

    def _load_shipments(self, path: Path) -> dict[str, Shipment]:
        if not path.exists():
            raise RuntimeError(f"Shipment export not found: {path}. Run: .\\tasks.ps1 seed")
        with path.open(newline="", encoding="utf-8") as f:
            return {
                r["shipment_id"]: Shipment(
                    shipment_id=r["shipment_id"], order_id=r["order_id"], carrier=r["carrier"],
                    origin=r.get("origin") or None, destination=r.get("destination") or None,
                    last_scan_at=self._parse_ts(r.get("last_scan_at", "")), last_status=r["last_status"],
                )
                for r in csv.DictReader(f)
            }

    def _load_tickets(self) -> dict[str, Ticket]:
        if not self.tickets_file.exists():
            return {}
        raw = json.loads(self.tickets_file.read_text(encoding="utf-8"))
        return {t["ticket_id"]: Ticket.model_validate(t) for t in raw}

    def _save_tickets(self) -> None:
        self.tickets_file.parent.mkdir(parents=True, exist_ok=True)
        data = [t.model_dump(mode="json") for t in self.tickets.values()]
        self.tickets_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def create_ticket(self, body: TicketCreate, created_by: str) -> Ticket:
        with self._lock:
            ticket_id = f"TCK-{len(self.tickets) + 1:04d}"
            ticket = Ticket(**body.model_dump(), ticket_id=ticket_id,
                            created_at=datetime.now(UTC), created_by=created_by)
            self.tickets[ticket_id] = ticket
            self._save_tickets()
            return ticket


def create_app(shipments_csv: Path | None = None, tickets_file: Path | None = None,
               token: str | None = None, load_data: bool = True) -> FastAPI:
    """load_data=False builds the same API with no data: used to export the spec (no CSV needed)."""
    store = Store(
        shipments_csv or Path(os.environ.get("ERP_SHIPMENTS_CSV", DEFAULT_SHIPMENTS)),
        tickets_file or Path(os.environ.get("ERP_TICKETS_FILE", DEFAULT_TICKETS)),
        load_data=load_data,
    )
    expected_token = token or os.environ.get("ERP_API_TOKEN", "dev-token")

    app = FastAPI(
        title="Northwind Legacy ERP (mock)",
        version="1.0.0",
        description="Shipment tracking and claims tickets. Authenticate with `Authorization: Bearer <token>`.",
    )
    app.state.store = store

    def require_token(authorization: Annotated[str | None, Header()] = None) -> None:
        if authorization != f"Bearer {expected_token}":
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing or invalid bearer token",
                                headers={"WWW-Authenticate": "Bearer"})

    Auth = Depends(require_token)

    @app.get("/health", operation_id="health", response_model=Health, tags=["system"])
    def health() -> Health:
        return Health(status="ok", shipments_loaded=len(store.shipments), tickets=len(store.tickets))

    @app.get("/shipments/{shipment_id}", operation_id="getShipment", response_model=Shipment,
             dependencies=[Auth], tags=["shipments"],
             summary="Get the latest carrier status of one shipment")
    def get_shipment(shipment_id: str) -> Shipment:
        shipment = store.shipments.get(shipment_id.strip().upper())
        if shipment is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Shipment {shipment_id} not found")
        return shipment

    @app.get("/shipments", operation_id="listShipments", response_model=list[Shipment],
             dependencies=[Auth], tags=["shipments"],
             summary="List shipments, filtered by order or status text")
    def list_shipments(
        order_id: Annotated[str | None, Query(description="Exact order id, e.g. ORD-1043")] = None,
        status_contains: Annotated[str | None, Query(description="Case-insensitive text in last_status")] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
    ) -> list[Shipment]:
        rows = list(store.shipments.values())
        if order_id:
            rows = [s for s in rows if s.order_id == order_id.strip().upper()]
        if status_contains:
            rows = [s for s in rows if status_contains.lower() in s.last_status.lower()]
        return rows[:limit]

    @app.post("/tickets", operation_id="createTicket", response_model=Ticket,
              status_code=status.HTTP_201_CREATED, dependencies=[Auth], tags=["tickets"],
              summary="Open a credit/claims ticket (a WRITE action: agents must get approval first)")
    def create_ticket(body: TicketCreate,
                      x_client: Annotated[str | None, Header()] = None) -> Ticket:
        return store.create_ticket(body, created_by=x_client or "unknown")

    @app.get("/tickets/{ticket_id}", operation_id="getTicket", response_model=Ticket,
             dependencies=[Auth], tags=["tickets"], summary="Get one ticket")
    def get_ticket(ticket_id: str) -> Ticket:
        ticket = store.tickets.get(ticket_id.strip().upper())
        if ticket is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Ticket {ticket_id} not found")
        return ticket

    return app


def export_spec(path: Path) -> None:
    """Write the OpenAPI contract the tool generator reads (engagement.yaml -> tools.openapi.spec)."""
    import yaml

    app = create_app(load_data=False)
    path.write_text(yaml.safe_dump(app.openapi(), sort_keys=False, allow_unicode=False), encoding="utf-8")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "export-spec":
        out = Path(__file__).resolve().parent / "openapi.yaml"
        export_spec(out)
        print(f"wrote {out}")
    else:
        import uvicorn

        uvicorn.run(create_app(), host="127.0.0.1", port=int(os.environ.get("ERP_PORT", "8100")))
