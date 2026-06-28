from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.order import CanalPedido


class ConsentimentoCreate(BaseModel):
    finalidade: str
    base_legal: str = "CONSENTIMENTO"
    concedido: bool = True
    canal_coleta: CanalPedido | None = None
    versao_termo: str | None = None


class ConsentimentoOut(BaseModel):
    consentimento_id: uuid.UUID
    cliente_id: uuid.UUID
    finalidade: str
    status: str
    concedido_em: datetime | None = None
    revogado_em: datetime | None = None
