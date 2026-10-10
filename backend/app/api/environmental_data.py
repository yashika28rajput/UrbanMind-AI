from __future__ import annotations

import json
import logging

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.schemas.environmental_data import (
    EnvironmentalImportResult,
    EnvironmentalRecord,
    EnvironmentalRecordInput,
    EnvironmentalRecordPage,
    ImportValidationReport,
    UploadPreview,
)
from app.services import environmental_data as environmental_data_service

router = APIRouter(prefix="/api/v1/environmental-data", tags=["environmental-data"])
logger = logging.getLogger(__name__)


async def _upload_content(file: UploadFile) -> bytes:
    content = await file.read(settings.ENVIRONMENTAL_UPLOAD_MAX_BYTES + 1)
    if len(content) > settings.ENVIRONMENTAL_UPLOAD_MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {settings.ENVIRONMENTAL_UPLOAD_MAX_BYTES}-byte upload limit.",
        )
    return content


def _parse_mapping(mapping_json: str) -> dict[str, str]:
    try:
        mapping = json.loads(mapping_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="Column mapping must be valid JSON.") from exc
    if not isinstance(mapping, dict) or any(not isinstance(key, str) or not isinstance(value, str) for key, value in mapping.items()):
        raise HTTPException(status_code=422, detail="Column mapping must map canonical field names to source column names.")
    return mapping


def _service_error(exc: Exception) -> HTTPException:
    if isinstance(exc, environmental_data_service.DuplicateEnvironmentalRecord):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, environmental_data_service.EnvironmentalUploadError):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=422, detail=str(exc))
    logger.exception("Environmental data operation failed")
    return HTTPException(status_code=503, detail="Environmental data storage is unavailable.")


@router.post("/uploads/preview", response_model=UploadPreview)
async def preview_upload(file: UploadFile = File(...)) -> UploadPreview:
    content = await _upload_content(file)
    try:
        return environmental_data_service.preview_environmental_file(content, file.filename or "")
    except (ValueError, SQLAlchemyError) as exc:
        raise _service_error(exc) from exc


@router.post("/uploads/validate", response_model=ImportValidationReport)
async def validate_upload(
    file: UploadFile = File(...),
    mapping_json: str = Form(...),
) -> ImportValidationReport:
    content = await _upload_content(file)
    mapping = _parse_mapping(mapping_json)
    try:
        return environmental_data_service.validate_environmental_file(content, file.filename or "", mapping)
    except (ValueError, SQLAlchemyError) as exc:
        raise _service_error(exc) from exc


@router.post("/imports/confirm", response_model=EnvironmentalImportResult)
async def confirm_import(
    file: UploadFile = File(...),
    mapping_json: str = Form(...),
    checksum: str = Form(...),
) -> EnvironmentalImportResult:
    content = await _upload_content(file)
    mapping = _parse_mapping(mapping_json)
    try:
        return environmental_data_service.import_environmental_file(
            content,
            file.filename or "",
            mapping,
            checksum,
        )
    except (ValueError, SQLAlchemyError) as exc:
        raise _service_error(exc) from exc


@router.post("/records", response_model=EnvironmentalRecord, status_code=201)
async def create_record(request: EnvironmentalRecordInput) -> EnvironmentalRecord:
    try:
        return environmental_data_service.create_environmental_record(request)
    except (ValueError, SQLAlchemyError) as exc:
        raise _service_error(exc) from exc


@router.get("/records", response_model=EnvironmentalRecordPage)
async def list_records(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    ward_id: int | None = Query(default=None, gt=0),
    metric: str | None = None,
) -> EnvironmentalRecordPage:
    try:
        return environmental_data_service.list_environmental_records(
            limit=limit,
            offset=offset,
            ward_id=ward_id,
            metric=metric,
        )
    except SQLAlchemyError as exc:
        raise _service_error(exc) from exc