from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import exigir_self_ou_admin, get_current_user
from app.core.database import get_db
from app.models.catalog import AuditLog
from app.models.user import Consentimento, StatusConsentimento, Usuario
from app.schemas.consent import ConsentimentoCreate, ConsentimentoOut

router = APIRouter(prefix="/v1", tags=["lgpd"])


@router.post(
    "/clientes/{cliente_id}/consentimentos",
    response_model=ConsentimentoOut,
    status_code=status.HTTP_201_CREATED,
)
def registrar_consentimento(
    cliente_id: uuid.UUID,
    payload: ConsentimentoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> ConsentimentoOut:
    """Registra que o cliente concordou (ou não) com uma finalidade de uso dos dados dele,
    por exemplo `FIDELIDADE` (que é o que libera o acúmulo de pontos quando o pedido é pago) ou
    `MARKETING_SEGMENTADO`. Só o próprio cliente ou um ADMIN pode registrar isso, se tentar
    registrar pra outra pessoa retorna 403.
    """
    exigir_self_ou_admin(cliente_id, usuario)
    cliente = db.get(Usuario, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")

    consentimento = Consentimento(
        usuario_id=cliente_id,
        finalidade=payload.finalidade,
        base_legal=payload.base_legal,
        status=StatusConsentimento.CONCEDIDO if payload.concedido else StatusConsentimento.REVOGADO,
        versao_termo=payload.versao_termo,
    )
    db.add(consentimento)
    db.add(
        AuditLog(
            ator_id=cliente_id,
            acao="REGISTRAR_CONSENTIMENTO",
            entidade="consentimento",
            detalhes={"finalidade": payload.finalidade, "concedido": payload.concedido},
        )
    )
    db.commit()
    db.refresh(consentimento)

    return ConsentimentoOut(
        consentimento_id=consentimento.id,
        cliente_id=cliente_id,
        finalidade=consentimento.finalidade,
        status=consentimento.status.value,
        concedido_em=consentimento.concedido_em,
        revogado_em=consentimento.revogado_em,
    )


@router.delete("/clientes/{cliente_id}/consentimentos/{consentimento_id}", response_model=ConsentimentoOut)
def revogar_consentimento(
    cliente_id: uuid.UUID,
    consentimento_id: uuid.UUID,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> ConsentimentoOut:
    """Revoga um consentimento que já tinha sido dado, usando o `consentimento_id` que veio na
    resposta de quando ele foi registrado. Depois disso o consentimento para de valer, por
    exemplo, revogar o `FIDELIDADE` faz o cliente parar de acumular pontos.
    """
    exigir_self_ou_admin(cliente_id, usuario)
    consentimento = db.scalar(
        select(Consentimento).where(
            Consentimento.id == consentimento_id,
            Consentimento.usuario_id == cliente_id,
        )
    )
    if consentimento is None:
        raise HTTPException(status_code=404, detail="Consentimento não encontrado.")
    if consentimento.status == StatusConsentimento.REVOGADO:
        raise HTTPException(status_code=409, detail="Consentimento já revogado.")

    consentimento.revogar()
    db.add(
        AuditLog(
            ator_id=cliente_id,
            acao="REVOGAR_CONSENTIMENTO",
            entidade="consentimento",
            detalhes={"consentimento_id": str(consentimento_id)},
        )
    )
    db.commit()
    db.refresh(consentimento)

    return ConsentimentoOut(
        consentimento_id=consentimento.id,
        cliente_id=cliente_id,
        finalidade=consentimento.finalidade,
        status=consentimento.status.value,
        concedido_em=consentimento.concedido_em,
        revogado_em=consentimento.revogado_em,
    )
