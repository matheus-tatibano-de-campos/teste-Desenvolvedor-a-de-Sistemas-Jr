"""Testes da regra de comissão e do relatório do arquivo de vendas."""

from __future__ import annotations

import unittest
from decimal import Decimal
from pathlib import Path

from comissao import (
    calcular_comissao,
    carregar_vendas,
    formatar_reais,
    resumir_por_vendedor,
)

RAIZ = Path(__file__).resolve().parent


class TestFaixas(unittest.TestCase):
    def test_limites_da_regra(self) -> None:
        casos = [
            (Decimal("0"), Decimal("0.00")),
            (Decimal("99.99"), Decimal("0.00")),
            (Decimal("100.00"), Decimal("1.00")),
            (Decimal("499.99"), Decimal("5.00")),
            (Decimal("500.00"), Decimal("25.00")),
            (Decimal("500.01"), Decimal("25.00")),
        ]
        for valor, esperado in casos:
            with self.subTest(valor=valor):
                self.assertEqual(calcular_comissao(valor), esperado)

    def test_arredondamento_half_up_por_venda(self) -> None:
        # 1100.90 * 5% = 55.045 -> 55.05; 250.30 * 1% = 2.503 -> 2.50
        self.assertEqual(calcular_comissao(Decimal("1100.90")), Decimal("55.05"))
        self.assertEqual(calcular_comissao(Decimal("250.30")), Decimal("2.50"))
        self.assertEqual(calcular_comissao(Decimal("480.75")), Decimal("4.81"))

    def test_valor_negativo_e_rejeitado(self) -> None:
        with self.assertRaises(ValueError):
            calcular_comissao(Decimal("-0.01"))


class TestResumo(unittest.TestCase):
    def test_soma_comissoes_ja_arredondadas(self) -> None:
        # 100.00 * 1% = 1.00; 500.00 * 5% = 25.00. Não aplica 5% sobre o total.
        vendas = [
            {"vendedor": "Ana", "valor": Decimal("100.00")},
            {"vendedor": "Ana", "valor": Decimal("500.00")},
            {"vendedor": "Bia", "valor": Decimal("50.00")},
        ]
        resumos = resumir_por_vendedor(vendas)
        self.assertEqual([r.vendedor for r in resumos], ["Ana", "Bia"])
        self.assertEqual(resumos[0].quantidade, 2)
        self.assertEqual(resumos[0].total_vendido, Decimal("600.00"))
        self.assertEqual(resumos[0].comissao, Decimal("26.00"))
        self.assertEqual(resumos[1].comissao, Decimal("0.00"))

    def test_venda_invalida(self) -> None:
        with self.assertRaises(ValueError):
            resumir_por_vendedor([{"valor": Decimal("10")}])


class TestArquivoDeVendas(unittest.TestCase):
    def test_totais_do_json(self) -> None:
        # Totais calculados à mão, venda a venda, com half up em centavos.
        esperados = {
            "João Silva": (10, Decimal("10754.70"), Decimal("495.69")),
            "Maria Souza": (9, Decimal("9874.30"), Decimal("465.96")),
            "Carlos Oliveira": (8, Decimal("7928.35"), Decimal("379.38")),
            "Ana Lima": (9, Decimal("8763.95"), Decimal("404.99")),
        }
        resumos = resumir_por_vendedor(carregar_vendas(RAIZ / "vendas.json"))
        self.assertEqual([r.vendedor for r in resumos], list(esperados))
        for resumo in resumos:
            quantidade, vendido, comissao = esperados[resumo.vendedor]
            self.assertEqual(resumo.quantidade, quantidade)
            self.assertEqual(resumo.total_vendido, vendido)
            self.assertEqual(resumo.comissao, comissao)

    def test_formato_brasileiro(self) -> None:
        self.assertEqual(formatar_reais(Decimal("1746.02")), "R$ 1.746,02")
        self.assertEqual(formatar_reais(Decimal("0")), "R$ 0,00")


if __name__ == "__main__":
    unittest.main()
