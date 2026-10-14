"""Calcula a comissão de cada vendedor a partir de um JSON de vendas.

Faixas, aplicadas por venda:
- abaixo de R$ 100,00: 0%
- de R$ 100,00 até abaixo de R$ 500,00: 1%
- a partir de R$ 500,00: 5%

Cada comissão é arredondada para centavos antes da soma.
O total do vendedor é a soma dessas comissões, não a alíquota sobre o total.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

CENTAVOS = Decimal("0.01")
LIMITE_SEM_COMISSAO = Decimal("100")
LIMITE_COMISSAO_ALTA = Decimal("500")
TAXA_BAIXA = Decimal("0.01")
TAXA_ALTA = Decimal("0.05")


@dataclass(frozen=True)
class ResumoVendedor:
    vendedor: str
    quantidade: int
    total_vendido: Decimal
    comissao: Decimal


def taxa_comissao(valor: Decimal) -> Decimal:
    if valor < LIMITE_SEM_COMISSAO:
        return Decimal("0")
    if valor < LIMITE_COMISSAO_ALTA:
        return TAXA_BAIXA
    return TAXA_ALTA


def calcular_comissao(valor: Decimal) -> Decimal:
    if valor < 0:
        raise ValueError(f"valor da venda não pode ser negativo: {valor}")
    return (valor * taxa_comissao(valor)).quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def _como_decimal(valor: object) -> Decimal:
    if isinstance(valor, Decimal):
        return valor
    if isinstance(valor, bool) or not isinstance(valor, (int, float, str)):
        raise ValueError(f"valor da venda inválido: {valor!r}")
    return Decimal(str(valor))


def resumir_por_vendedor(vendas: list[dict]) -> list[ResumoVendedor]:
    # quantidade, total vendido, comissão — na ordem em que o vendedor aparece
    totais: dict[str, tuple[int, Decimal, Decimal]] = {}

    for indice, venda in enumerate(vendas):
        if not isinstance(venda, dict):
            raise ValueError(f"venda {indice} não é um objeto")
        vendedor = venda.get("vendedor")
        if not isinstance(vendedor, str) or not vendedor.strip():
            raise ValueError(f"venda {indice} sem vendedor")
        if "valor" not in venda:
            raise ValueError(f"venda {indice} sem valor")

        valor = _como_decimal(venda["valor"])
        comissao = calcular_comissao(valor)
        quantidade, vendido, comissao_acc = totais.get(
            vendedor, (0, Decimal("0"), Decimal("0"))
        )
        totais[vendedor] = (quantidade + 1, vendido + valor, comissao_acc + comissao)

    return [
        ResumoVendedor(
            vendedor=vendedor,
            quantidade=quantidade,
            total_vendido=vendido,
            comissao=comissao,
        )
        for vendedor, (quantidade, vendido, comissao) in totais.items()
    ]


def carregar_vendas(caminho: Path) -> list[dict]:
    with caminho.open(encoding="utf-8") as arquivo:
        # parse_float=Decimal lê o token numérico do JSON como texto,
        # então 1200.50 vira Decimal("1200.50") e não um float binário.
        dados = json.load(arquivo, parse_float=Decimal)

    if not isinstance(dados, dict) or not isinstance(dados.get("vendas"), list):
        raise ValueError("JSON deve ter a chave 'vendas' com uma lista")
    return dados["vendas"]


def formatar_reais(valor: Decimal) -> str:
    centavos = valor.quantize(CENTAVOS, rounding=ROUND_HALF_UP)
    sinal = "-" if centavos < 0 else ""
    inteiro, fracao = f"{abs(centavos):.2f}".split(".")
    grupos: list[str] = []
    while inteiro:
        grupos.append(inteiro[-3:])
        inteiro = inteiro[:-3]
    return f"{sinal}R$ {'.'.join(reversed(grupos))},{fracao}"


def formatar_relatorio(resumos: list[ResumoVendedor]) -> str:
    linhas = [
        "Comissão por vendedor",
        "Abaixo de R$ 100,00: 0% | de R$ 100,00 a R$ 499,99: 1% | a partir de R$ 500,00: 5%",
        "Cada venda é arredondada para centavos antes de somar.",
        "",
        f"{'Vendedor':<20} {'Qtd':>4} {'Total vendido':>16} {'Comissão':>14}",
    ]
    total_qtd = 0
    total_vendido = Decimal("0")
    total_comissao = Decimal("0")
    for resumo in resumos:
        linhas.append(
            f"{resumo.vendedor:<20} {resumo.quantidade:>4} "
            f"{formatar_reais(resumo.total_vendido):>16} "
            f"{formatar_reais(resumo.comissao):>14}"
        )
        total_qtd += resumo.quantidade
        total_vendido += resumo.total_vendido
        total_comissao += resumo.comissao
    linhas.append("-" * 58)
    linhas.append(
        f"{'TOTAL':<20} {total_qtd:>4} "
        f"{formatar_reais(total_vendido):>16} "
        f"{formatar_reais(total_comissao):>14}"
    )
    return "\n".join(linhas)


def main(argv: list[str] | None = None) -> int:
    # O console do Windows costuma não estar em UTF-8; sem isso, "Comissão" sai quebrado.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    argumentos = list(sys.argv[1:] if argv is None else argv)
    caminho = Path(argumentos[0]) if argumentos else Path(__file__).with_name("vendas.json")
    resumos = resumir_por_vendedor(carregar_vendas(caminho))
    print(formatar_relatorio(resumos))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
