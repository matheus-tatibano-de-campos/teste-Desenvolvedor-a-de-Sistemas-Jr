"""Calcula os juros de um valor até a data de hoje.

A multa é de 2,5% ao dia, em juros simples, sobre os dias corridos de atraso:

    juros = valor × 0,025 × dias

O dia do vencimento não gera juros. Vencimento hoje ou no futuro também não.
O resultado é arredondado para centavos (half up).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

CENTAVOS = Decimal("0.01")
TAXA_AO_DIA = Decimal("0.025")


@dataclass(frozen=True)
class ResultadoJuros:
    valor: Decimal
    vencimento: date
    hoje: date
    dias_atraso: int
    juros: Decimal

    @property
    def total(self) -> Decimal:
        return self.valor + self.juros


def analisar_valor(texto: str) -> Decimal:
    limpo = texto.strip().replace("R$", "").strip()
    if not limpo:
        raise ValueError("informe o valor")
    # 1.500,50 é o formato brasileiro; 1500.50 permanece decimal.
    if "," in limpo:
        limpo = limpo.replace(".", "").replace(",", ".")
    try:
        valor = Decimal(limpo)
    except Exception as erro:
        raise ValueError(f"valor inválido: {texto}") from erro
    if valor < 0:
        raise ValueError("valor não pode ser negativo")
    return valor


def analisar_data(texto: str) -> date:
    bruto = texto.strip()
    for formato in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(bruto, formato).date()
        except ValueError:
            continue
    raise ValueError("data deve estar em DD/MM/AAAA")


def calcular_juros(valor: Decimal, vencimento: date, hoje: date | None = None) -> ResultadoJuros:
    if valor < 0:
        raise ValueError("valor não pode ser negativo")
    data_hoje = date.today() if hoje is None else hoje
    dias = (data_hoje - vencimento).days
    if dias < 0:
        dias = 0
    juros = (valor * TAXA_AO_DIA * dias).quantize(CENTAVOS, rounding=ROUND_HALF_UP)
    return ResultadoJuros(
        valor=valor,
        vencimento=vencimento,
        hoje=data_hoje,
        dias_atraso=dias,
        juros=juros,
    )


def formatar_reais(valor: Decimal) -> str:
    centavos = valor.quantize(CENTAVOS, rounding=ROUND_HALF_UP)
    sinal = "-" if centavos < 0 else ""
    inteiro, fracao = f"{abs(centavos):.2f}".split(".")
    grupos: list[str] = []
    while inteiro:
        grupos.append(inteiro[-3:])
        inteiro = inteiro[:-3]
    return f"{sinal}R$ {'.'.join(reversed(grupos))},{fracao}"


def formatar_relatorio(resultado: ResultadoJuros) -> str:
    return "\n".join(
        [
            f"Valor: {formatar_reais(resultado.valor)}",
            f"Vencimento: {resultado.vencimento.strftime('%d/%m/%Y')}",
            f"Hoje: {resultado.hoje.strftime('%d/%m/%Y')}",
            f"Dias em atraso: {resultado.dias_atraso}",
            "Multa: 2,5% ao dia",
            f"Juros: {formatar_reais(resultado.juros)}",
            f"Total: {formatar_reais(resultado.total)}",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    argumentos = list(sys.argv[1:] if argv is None else argv)
    try:
        if not argumentos:
            valor = analisar_valor(input("Valor: "))
            vencimento = analisar_data(input("Data de vencimento (DD/MM/AAAA): "))
        elif len(argumentos) == 2:
            valor = analisar_valor(argumentos[0])
            vencimento = analisar_data(argumentos[1])
        else:
            raise ValueError("uso: python juros.py VALOR DD/MM/AAAA")
        print(formatar_relatorio(calcular_juros(valor, vencimento)))
        return 0
    except (ValueError, OSError) as erro:
        print(erro, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
