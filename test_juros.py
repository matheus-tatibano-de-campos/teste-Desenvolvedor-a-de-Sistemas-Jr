"""Testes dos juros de 2,5% ao dia até uma data de referência."""

from __future__ import annotations

import subprocess
import sys
import unittest
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from juros import analisar_data, analisar_valor, calcular_juros

RAIZ = Path(__file__).resolve().parent
HOJE = date(2026, 10, 14)


class TestCalculo(unittest.TestCase):
    def test_dez_dias_de_atraso(self) -> None:
        # 1000 × 2,5% × 10 = 250,00
        resultado = calcular_juros(Decimal("1000.00"), date(2026, 10, 4), HOJE)
        self.assertEqual(resultado.dias_atraso, 10)
        self.assertEqual(resultado.juros, Decimal("250.00"))
        self.assertEqual(resultado.total, Decimal("1250.00"))

    def test_vencimento_hoje_e_futuro_nao_geram_juros(self) -> None:
        no_dia = calcular_juros(Decimal("80.00"), HOJE, HOJE)
        futuro = calcular_juros(Decimal("80.00"), date(2026, 10, 20), HOJE)
        self.assertEqual(no_dia.dias_atraso, 0)
        self.assertEqual(no_dia.juros, Decimal("0.00"))
        self.assertEqual(futuro.dias_atraso, 0)
        self.assertEqual(futuro.juros, Decimal("0.00"))

    def test_um_dia_arredonda_meio_centavo_para_cima(self) -> None:
        # 1,00 × 2,5% = 0,025 → 0,03
        resultado = calcular_juros(Decimal("1.00"), date(2026, 10, 13), HOJE)
        self.assertEqual(resultado.dias_atraso, 1)
        self.assertEqual(resultado.juros, Decimal("0.03"))

    def test_tres_dias_arredonda_a_parcela_unica(self) -> None:
        # 100,10 × 2,5% × 3 = 7,5075 → 7,51
        resultado = calcular_juros(Decimal("100.10"), date(2026, 10, 11), HOJE)
        self.assertEqual(resultado.juros, Decimal("7.51"))

    def test_valor_negativo_e_rejeitado(self) -> None:
        with self.assertRaises(ValueError):
            calcular_juros(Decimal("-1"), HOJE, HOJE)


class TestEntrada(unittest.TestCase):
    def test_valor_em_formato_brasileiro(self) -> None:
        self.assertEqual(analisar_valor("1.500,50"), Decimal("1500.50"))
        self.assertEqual(analisar_valor("200"), Decimal("200"))

    def test_data_brasileira_e_iso(self) -> None:
        self.assertEqual(analisar_data("01/10/2026"), date(2026, 10, 1))
        self.assertEqual(analisar_data("2026-10-01"), date(2026, 10, 1))

    def test_data_invalida(self) -> None:
        with self.assertRaises(ValueError):
            analisar_data("31/02/2026")


class TestLinhaDeComando(unittest.TestCase):
    def test_atraso_de_um_dia_usa_a_data_de_hoje(self) -> None:
        ontem = (date.today() - timedelta(days=1)).strftime("%d/%m/%Y")
        concluido = subprocess.run(
            [sys.executable, str(RAIZ / "juros.py"), "200", ontem],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(concluido.returncode, 0, concluido.stderr)
        self.assertIn("Dias em atraso: 1", concluido.stdout)
        self.assertIn("Juros: R$ 5,00", concluido.stdout)
        self.assertIn("Total: R$ 205,00", concluido.stdout)

    def test_vencido_hoje_tem_juros_zero(self) -> None:
        hoje = date.today().strftime("%d/%m/%Y")
        concluido = subprocess.run(
            [sys.executable, str(RAIZ / "juros.py"), "80,00", hoje],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(concluido.returncode, 0, concluido.stderr)
        self.assertIn("Dias em atraso: 0", concluido.stdout)
        self.assertIn("Juros: R$ 0,00", concluido.stdout)


if __name__ == "__main__":
    unittest.main()
