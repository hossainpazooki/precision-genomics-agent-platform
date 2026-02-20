"""Biomarker panel endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/biomarkers", tags=["Biomarkers"])

# In-memory panel store for demo/testing
_panels: list[dict] = [
    {
        "id": 1,
        "target": "msi",
        "modality": "proteomics",
        "n_features": 26,
        "features": [
            {"gene": "TAP1", "importance": 0.15},
            {"gene": "LCP1", "importance": 0.12},
            {"gene": "PTPN6", "importance": 0.10},
            {"gene": "ICAM1", "importance": 0.09},
            {"gene": "ITGB2", "importance": 0.08},
        ],
        "method": "multi_strategy",
        "created_at": "2025-01-01T00:00:00Z",
    },
    {
        "id": 2,
        "target": "msi",
        "modality": "rnaseq",
        "n_features": 26,
        "features": [
            {"gene": "EPDR1", "importance": 0.14},
            {"gene": "CIITA", "importance": 0.11},
            {"gene": "IRF1", "importance": 0.10},
            {"gene": "GBP4", "importance": 0.09},
            {"gene": "LAG3", "importance": 0.08},
        ],
        "method": "multi_strategy",
        "created_at": "2025-01-01T00:00:00Z",
    },
]


def _get_panels_from_db() -> list[dict]:
    """Try to load panels from the database, fall back to in-memory store."""
    try:
        from sqlmodel import Session, select

        from core.database import get_engine
        from core.models import BiomarkerPanel

        engine = get_engine()
        with Session(engine) as session:
            panels = session.exec(select(BiomarkerPanel)).all()
            if panels:
                return [
                    {
                        "id": p.id,
                        "target": p.target,
                        "modality": p.modality,
                        "n_features": len(p.features),
                        "features": p.features,
                        "created_at": p.created_at.isoformat() + "Z" if p.created_at else None,
                    }
                    for p in panels
                ]
    except Exception:
        pass
    return _panels


@router.get("/panels")
async def list_panels() -> list[dict]:
    """List all available biomarker panels."""
    return _get_panels_from_db()


@router.get("/{panel_id}/features")
async def get_panel_features(panel_id: int) -> dict:
    """Get detailed feature list for a specific panel."""
    panels = _get_panels_from_db()
    for panel in panels:
        if panel["id"] == panel_id:
            return {
                "panel_id": panel_id,
                "target": panel["target"],
                "modality": panel["modality"],
                "features": panel["features"],
                "n_features": panel.get("n_features", len(panel["features"])),
            }
    raise HTTPException(status_code=404, detail=f"Panel {panel_id} not found")
