"""Data export downloads (JSON document, CSV zip). Read-only."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_clock
from app.domain.clock import Clock
from app.infrastructure.db import get_session
from app.services.export_service import ExportService

router = APIRouter(prefix="/export", tags=["export"])


def get_export(
    session: Annotated[Session, Depends(get_session)], clock: Annotated[Clock, Depends(get_clock)]
) -> ExportService:
    return ExportService(session, clock)


Export = Annotated[ExportService, Depends(get_export)]


@router.get("/json")
def export_json(export: Export) -> Response:
    name = f"master-mentor-export-{export.filename_stamp()}.json"
    return Response(
        export.json_bytes(),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.get("/csv")
def export_csv(export: Export) -> Response:
    name = f"master-mentor-export-{export.filename_stamp()}.zip"
    return Response(
        export.csv_zip_bytes(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )
