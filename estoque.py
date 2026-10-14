"""Lança entrada ou saída no depósito e devolve o estoque final do produto.

Cada movimentação gravada tem:
- id: número inteiro único, crescente
- descricao: texto que identifica o tipo do lançamento
- tipo: "entrada" soma, "saida" subtrai
- estoqueFinal: saldo do produto depois desta movimentação

A saída que deixaria o saldo negativo é recusada e o arquivo não muda.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

TIPOS = ("entrada", "saida")


@dataclass(frozen=True)
class ResultadoMovimentacao:
    id: int
    descricao: str
    codigo_produto: int
    descricao_produto: str
    tipo: str
    quantidade: int
    estoque_final: int


def carregar_estado(caminho: Path) -> dict:
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    if not isinstance(dados, dict) or not isinstance(dados.get("estoque"), list):
        raise ValueError("JSON deve ter a chave 'estoque' com uma lista")
    movimentacoes = dados.get("movimentacoes", [])
    if not isinstance(movimentacoes, list):
        raise ValueError("'movimentacoes' deve ser uma lista")
    return {"estoque": dados["estoque"], "movimentacoes": movimentacoes}


def salvar_estado(caminho: Path, estado: dict) -> None:
    # Grava num arquivo temporário e troca o nome: se o processo cair no meio,
    # o JSON anterior continua íntegro.
    temporario = caminho.with_suffix(caminho.suffix + ".tmp")
    texto = json.dumps(estado, ensure_ascii=False, indent=2) + "\n"
    temporario.write_text(texto, encoding="utf-8")
    temporario.replace(caminho)


def _inteiro(valor: object, nome: str) -> int:
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise ValueError(f"{nome} deve ser um número inteiro")
    return valor


def _buscar_produto(estoque: list[dict], codigo: int) -> dict:
    for produto in estoque:
        if isinstance(produto, dict) and produto.get("codigoProduto") == codigo:
            return produto
    raise ValueError(f"produto {codigo} não encontrado")


def _proximo_id(movimentacoes: list[dict]) -> int:
    ids = [
        item["id"]
        for item in movimentacoes
        if isinstance(item, dict) and isinstance(item.get("id"), int) and not isinstance(item.get("id"), bool)
    ]
    return max(ids, default=0) + 1


def movimentar(
    estado: dict,
    codigo_produto: int,
    tipo: str,
    quantidade: int,
    descricao: str,
) -> ResultadoMovimentacao:
    codigo = _inteiro(codigo_produto, "código do produto")
    qtd = _inteiro(quantidade, "quantidade")
    if qtd <= 0:
        raise ValueError("quantidade deve ser maior que zero")
    if tipo not in TIPOS:
        raise ValueError("tipo deve ser 'entrada' ou 'saida'")
    if not isinstance(descricao, str) or not descricao.strip():
        raise ValueError("descrição da movimentação é obrigatória")

    produto = _buscar_produto(estado["estoque"], codigo)
    saldo = _inteiro(produto.get("estoque"), f"estoque do produto {codigo}")
    if saldo < 0:
        raise ValueError(f"estoque do produto {codigo} está inválido")

    if tipo == "entrada":
        novo_saldo = saldo + qtd
    else:
        if qtd > saldo:
            raise ValueError(
                f"saída de {qtd} maior que o estoque atual ({saldo}) "
                f"de {produto.get('descricaoProduto', codigo)}"
            )
        novo_saldo = saldo - qtd

    produto["estoque"] = novo_saldo
    movimento = {
        "id": _proximo_id(estado["movimentacoes"]),
        "descricao": descricao.strip(),
        "codigoProduto": codigo,
        "tipo": tipo,
        "quantidade": qtd,
        "estoqueFinal": novo_saldo,
    }
    estado["movimentacoes"].append(movimento)
    nome = produto.get("descricaoProduto")
    return ResultadoMovimentacao(
        id=movimento["id"],
        descricao=movimento["descricao"],
        codigo_produto=codigo,
        descricao_produto=nome if isinstance(nome, str) else str(codigo),
        tipo=tipo,
        quantidade=qtd,
        estoque_final=novo_saldo,
    )


def registrar(
    caminho: Path,
    codigo_produto: int,
    tipo: str,
    quantidade: int,
    descricao: str,
) -> ResultadoMovimentacao:
    estado = carregar_estado(caminho)
    resultado = movimentar(estado, codigo_produto, tipo, quantidade, descricao)
    salvar_estado(caminho, estado)
    return resultado


def formatar_estoque(estado: dict) -> str:
    linhas = [f"{'Código':>6}  {'Produto':<32} {'Estoque':>8}"]
    for produto in estado["estoque"]:
        linhas.append(
            f"{produto['codigoProduto']:>6}  "
            f"{produto['descricaoProduto']:<32} "
            f"{produto['estoque']:>8}"
        )
    return "\n".join(linhas)


def formatar_historico(estado: dict) -> str:
    if not estado["movimentacoes"]:
        return "Nenhuma movimentação lançada."
    linhas = [f"{'Id':>4}  {'Tipo':<8} {'Código':>6} {'Qtd':>6} {'Final':>6}  Descrição"]
    for item in estado["movimentacoes"]:
        linhas.append(
            f"{item['id']:>4}  {item['tipo']:<8} {item['codigoProduto']:>6} "
            f"{item['quantidade']:>6} {item['estoqueFinal']:>6}  {item['descricao']}"
        )
    return "\n".join(linhas)


def formatar_resultado(resultado: ResultadoMovimentacao) -> str:
    sentido = "Entrada" if resultado.tipo == "entrada" else "Saída"
    return (
        f"Movimentação {resultado.id} — {sentido}\n"
        f"Descrição: {resultado.descricao}\n"
        f"{resultado.descricao_produto} ({resultado.codigo_produto}): "
        f"estoque final = {resultado.estoque_final}"
    )


def _caminho_e_comando(argv: list[str]) -> tuple[Path, list[str]]:
    caminho = Path(__file__).with_name("estoque.json")
    args = list(argv)
    if args and args[0] == "--arquivo":
        if len(args) < 2:
            raise ValueError("informe o caminho depois de --arquivo")
        caminho = Path(args[1])
        args = args[2:]
    return caminho, args


def _lancar_linha_de_comando(caminho: Path, tipo: str, args: list[str]) -> int:
    if len(args) < 3:
        raise ValueError(f"uso: {tipo} CODIGO QUANTIDADE DESCRICAO")
    try:
        codigo = int(args[0])
        quantidade = int(args[1])
    except ValueError as erro:
        raise ValueError("código e quantidade devem ser números inteiros") from erro
    descricao = " ".join(args[2:])
    resultado = registrar(caminho, codigo, tipo, quantidade, descricao)
    print(formatar_resultado(resultado))
    return 0


def _perguntar(rotulo: str) -> str:
    return input(f"{rotulo}: ").strip()


def _lancar_interativo(caminho: Path, tipo: str) -> None:
    try:
        codigo = int(_perguntar("Código do produto"))
        quantidade = int(_perguntar("Quantidade"))
    except ValueError:
        print("Código e quantidade devem ser números inteiros.")
        return
    descricao = _perguntar("Descrição da movimentação")
    try:
        resultado = registrar(caminho, codigo, tipo, quantidade, descricao)
    except ValueError as erro:
        print(erro)
        return
    print(formatar_resultado(resultado))


def menu(caminho: Path) -> int:
    while True:
        print()
        print("Depósito")
        print("1) Listar estoque")
        print("2) Dar entrada")
        print("3) Dar saída")
        print("4) Ver movimentações")
        print("0) Sair")
        opcao = _perguntar("Opção")
        if opcao == "0":
            return 0
        if opcao == "1":
            print(formatar_estoque(carregar_estado(caminho)))
        elif opcao == "2":
            _lancar_interativo(caminho, "entrada")
        elif opcao == "3":
            _lancar_interativo(caminho, "saida")
        elif opcao == "4":
            print(formatar_historico(carregar_estado(caminho)))
        else:
            print("Opção inválida.")


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    try:
        caminho, args = _caminho_e_comando(list(sys.argv[1:] if argv is None else argv))
        if not args:
            return menu(caminho)
        comando = args[0].lower()
        if comando == "listar":
            print(formatar_estoque(carregar_estado(caminho)))
            return 0
        if comando == "historico":
            print(formatar_historico(carregar_estado(caminho)))
            return 0
        if comando in TIPOS:
            return _lancar_linha_de_comando(caminho, comando, args[1:])
        raise ValueError(
            "comandos: listar | historico | entrada CODIGO QTD DESCRICAO | saida CODIGO QTD DESCRICAO"
        )
    except (ValueError, OSError, json.JSONDecodeError) as erro:
        print(erro, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
