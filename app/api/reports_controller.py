from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import require_papel
from app.core.database import get_db
from app.models.user import Usuario
from app.services import report_service

router = APIRouter(prefix="/v1/relatorios", tags=["relatorios"])


@router.get("/vendas")
def relatorio_vendas(
    unidade_id: uuid.UUID | None = Query(default=None),
    data_inicio: date | None = Query(default=None),
    data_fim: date | None = Query(default=None),
    db: Session = Depends(get_db),
    admin: Usuario = Depends(require_papel("ADMIN")),
) -> dict:
    linhas = report_service.vendas_por_unidade(db, unidade_id, data_inicio, data_fim)
    return {
        "filtro": {
            "unidade_id": str(unidade_id) if unidade_id else None,
            "data_inicio": data_inicio.isoformat() if data_inicio else None,
            "data_fim": data_fim.isoformat() if data_fim else None,
        },
        "total_faturamento": round(sum(l["faturamento"] for l in linhas), 2),
        "unidades": linhas,
    }
