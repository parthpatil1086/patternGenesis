from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Form, HTTPException, UploadFile, File

from app.core.exceptions import PatternGenesisError
from app.services.analysis import analyze_image
from app.services.generation import _instruction_parameters, generate_from_analysis, generate_pattern
from app.services.reconstruction import reconstruct_pattern
router = APIRouter(prefix="/api")


@router.post("/analyze")
async def analyze_endpoint(file: UploadFile = File(...)) -> dict[str, Any]:
    try:
        return await analyze_image(file)
    except PatternGenesisError as exc:
        raise HTTPException(status_code=400, detail={"error": exc.code, "message": exc.message, "suggestion": exc.suggestion}) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail={"error": "ANALYSIS_FAILED", "message": str(exc), "suggestion": "Check the uploaded image and try again."}) from exc


@router.post("/reconstruct")
async def reconstruct_endpoint(file: UploadFile = File(...)) -> dict[str, Any]:
    try:
        return await reconstruct_pattern(file)
    except PatternGenesisError as exc:
        raise HTTPException(status_code=400, detail={"error": exc.code, "message": exc.message, "suggestion": exc.suggestion}) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail={"error": "RECONSTRUCTION_FAILED", "message": str(exc), "suggestion": "Check the source image and retry."}) from exc


@router.post("/generate")
async def generate_endpoint(payload: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
    grammar = payload.get("grammar", {}) if isinstance(payload, dict) else {}
    parameters = payload.get("parameters", {}) if isinstance(payload, dict) else {}
    instructions = payload.get("instructions", "") if isinstance(payload, dict) else ""
    parameters = {**parameters, **_instruction_parameters(str(instructions))}
    try:
        return generate_pattern(grammar, parameters)
    except PatternGenesisError as exc:
        raise HTTPException(status_code=400, detail={"error": exc.code, "message": exc.message, "suggestion": exc.suggestion}) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail={"error": "GENERATION_FAILED", "message": str(exc), "suggestion": "Check your grammar and parameters."}) from exc


@router.post("/generate/image")
async def generate_image_endpoint(
    file: UploadFile = File(...),
    instructions: str = Form(default=""),
    parameters: str = Form(default="{}"),
) -> dict[str, Any]:
    import json

    try:
        parsed_parameters = json.loads(parameters) if parameters else {}
        analysis = await analyze_image(file)
        return generate_from_analysis(analysis, parsed_parameters, instructions)
    except PatternGenesisError as exc:
        raise HTTPException(status_code=400, detail={"error": exc.code, "message": exc.message, "suggestion": exc.suggestion}) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail={"error": "IMAGE_GENERATION_FAILED", "message": str(exc), "suggestion": "Check the reference image and parameters."}) from exc


@router.post("/variations")
async def variations_endpoint(payload: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
    grammar = payload.get("grammar", {}) if isinstance(payload, dict) else {}
    parameters = payload.get("parameters", {}) if isinstance(payload, dict) else {}
    try:
        return generate_pattern(grammar, parameters, variations=True)
    except PatternGenesisError as exc:
        raise HTTPException(status_code=400, detail={"error": exc.code, "message": exc.message, "suggestion": exc.suggestion}) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail={"error": "VARIATION_FAILED", "message": str(exc), "suggestion": "Adjust the grammar and retry."}) from exc


@router.post("/export/3d")
async def export_3d() -> dict[str, Any]:
    return {"status": "planned", "format": "3d"}

