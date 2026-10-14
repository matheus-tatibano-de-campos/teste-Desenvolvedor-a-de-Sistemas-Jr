"""Testes de entrada, saída, saldo e identificador único das movimentações."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

from estoque import carregar_estado, movimentar, registrar

RAIZ = Path(__file__).resolve().parent


class TestRegras(unittest.TestCase):
    def setUp(self) -> None:
        self.estado = {
            "estoque": [
                {"codigoProduto": 101, "descricaoProduto": "Caneta Azul", "estoque": 150},
                {"codigoProduto": 102, "descricaoProduto": "Caderno Universitário", "estoque": 75},
            ],
            "movimentacoes": [],
        }

    def test_entrada_devolve_saldo_final_e_grava_id(self) -> None:
        resultado = movimentar(self.estado, 101, "entrada", 10, "Compra do fornecedor")
        self.assertEqual(resultado.estoque_final, 160)
        self.assertEqual(resultado.id, 1)
        self.assertEqual(resultado.descricao, "Compra do fornecedor")
        self.assertEqual(self.estado["estoque"][0]["estoque"], 160)
        self.assertEqual(self.estado["movimentacoes"][0]["estoqueFinal"], 160)

    def test_saida_devolve_saldo_final(self) -> None:
        resultado = movimentar(self.estado, 102, "saida", 25, "Venda no balcão")
        self.assertEqual(resultado.estoque_final, 50)
        self.assertEqual(self.estado["estoque"][1]["estoque"], 50)

    def test_saida_pode_zerar_o_estoque(self) -> None:
        resultado = movimentar(self.estado, 102, "saida", 75, "Inventário zerou o item")
        self.assertEqual(resultado.estoque_final, 0)

    def test_saida_acima_do_saldo_nao_altera_nada(self) -> None:
        with self.assertRaises(ValueError):
            movimentar(self.estado, 101, "saida", 151, "Ajuste indevido")
        self.assertEqual(self.estado["estoque"][0]["estoque"], 150)
        self.assertEqual(self.estado["movimentacoes"], [])

    def test_ids_unicos_e_crescentes(self) -> None:
        primeira = movimentar(self.estado, 101, "entrada", 1, "Entrada A")
        segunda = movimentar(self.estado, 101, "saida", 1, "Saída B")
        self.assertEqual((primeira.id, segunda.id), (1, 2))
        self.assertEqual(primeira.estoque_final, 151)
        self.assertEqual(segunda.estoque_final, 150)

    def test_rejeita_dados_invalidos(self) -> None:
        casos = [
            (999, "entrada", 1, "Compra"),
            (101, "ajuste", 1, "Ajuste"),
            (101, "entrada", 0, "Compra"),
            (101, "entrada", -5, "Compra"),
            (101, "entrada", 1, "   "),
        ]
        for codigo, tipo, quantidade, descricao in casos:
            with self.subTest(codigo=codigo, tipo=tipo, quantidade=quantidade):
                with self.assertRaises(ValueError):
                    movimentar(self.estado, codigo, tipo, quantidade, descricao)
        self.assertEqual(self.estado["movimentacoes"], [])


class TestPersistencia(unittest.TestCase):
    def test_arquivo_inicial_tem_os_saldos_do_enunciado(self) -> None:
        dados = json.loads((RAIZ / "estoque.json").read_text(encoding="utf-8"))
        saldos = [(item["codigoProduto"], item["estoque"]) for item in dados["estoque"]]
        self.assertEqual(saldos, [(101, 150), (102, 75), (103, 200), (104, 320), (105, 90)])

    def test_registrar_grava_e_a_proxima_leitura_ve_o_saldo(self) -> None:
        with self._copia() as caminho:
            resultado = registrar(caminho, 105, "entrada", 10, "Reposição de marcador")
            self.assertEqual(resultado.estoque_final, 100)
            estado = carregar_estado(caminho)
            marcador = next(item for item in estado["estoque"] if item["codigoProduto"] == 105)
            self.assertEqual(marcador["estoque"], 100)
            self.assertEqual(estado["movimentacoes"][0]["id"], 1)
            self.assertEqual(estado["movimentacoes"][0]["descricao"], "Reposição de marcador")

    def test_saida_recusada_nao_grava_o_arquivo(self) -> None:
        with self._copia() as caminho:
            with self.assertRaises(ValueError):
                registrar(caminho, 103, "saida", 201, "Saída sem saldo")
            dados = json.loads(caminho.read_text(encoding="utf-8"))
            borracha = next(item for item in dados["estoque"] if item["codigoProduto"] == 103)
            self.assertEqual(borracha["estoque"], 200)
            self.assertNotIn("movimentacoes", dados)

    def test_linha_de_comando_devolve_estoque_final(self) -> None:
        with self._copia() as caminho:
            concluido = subprocess.run(
                [
                    sys.executable,
                    str(RAIZ / "estoque.py"),
                    "--arquivo",
                    str(caminho),
                    "saida",
                    "104",
                    "20",
                    "Consumo da produção",
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(concluido.returncode, 0, concluido.stderr)
            self.assertIn("estoque final = 300", concluido.stdout)
            self.assertIn("Movimentação 1", concluido.stdout)
            self.assertIn("Consumo da produção", concluido.stdout)

    def _copia(self):
        return _CopiaTemporaria(RAIZ / "estoque.json")


class _CopiaTemporaria:
    def __init__(self, origem: Path) -> None:
        self.origem = origem
        self.diretorio: Path | None = None

    def __enter__(self) -> Path:
        import tempfile

        self.diretorio = Path(tempfile.mkdtemp())
        destino = self.diretorio / "estoque.json"
        shutil.copy(self.origem, destino)
        return destino

    def __exit__(self, *args: object) -> None:
        if self.diretorio is not None:
            shutil.rmtree(self.diretorio)


if __name__ == "__main__":
    unittest.main()
