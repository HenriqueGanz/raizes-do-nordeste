from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import catalog_service

router = APIRouter(prefix="/v1", tags=["cardapio"])


@router.get("/unidades")
def listar_unidades(db: Session = Depends(get_db)) -> list[dict]:
    """Lista as lojas (unidades) cadastradas. É por aqui que você pega o `unidade_id` pra usar
    nas outras rotas. Depois do seed, deve aparecer uma chamada "Raízes - Recife Boa Viagem".
    """
    return [
        {
            "unidade_id": str(u.id),
            "nome": u.nome,
            "cidade": u.cidade,
            "regiao": u.regiao,
            "formato_operacao": u.formato_operacao.value,
        }
        for u in catalog_service.listar_unidades(db)
    ]


@router.get("/unidades/{unidade_id}/cardapio")
def obter_cardapio(
    unidade_id: uuid.UUID,
    categoria: str | None = Query(default=None),
    data: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict:
    """Mostra o cardápio de uma unidade, já considerando o que está disponível na data escolhida
    (por padrão, hoje). No seed tem a "Tapioca de carne de sol com queijo coalho" (R$ 18,90,
    disponível o ano todo) e a "Canjica junina" (R$ 9,50, só aparece se a data estiver entre
    01/06/2026 e 31/07/2026, porque é sazonal).
    """
    unidade = catalog_service.obter_unidade(db, unidade_id)
    if unidade is None:
        raise HTTPException(status_code=404, detail="Unidade não encontrada ou inativa.")

    referencia = data or date.today()
    itens = catalog_service.listar_cardapio(db, unidade_id, referencia, categoria)
    return {
        "unidade_id": str(unidade.id),
        "nome": unidade.nome,
        "regiao": unidade.regiao,
        "vigente_em": referencia.isoformat(),
        "itens": [
            {
                "produto_id": str(i.produto_id),
                "nome": i.nome,
                "categoria": i.categoria,
                "preco": float(i.preco),
                "sazonal": i.sazonal,
                "disponivel": i.disponivel,
            }
            for i in itens
        ],
    }
