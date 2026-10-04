"""
importar_onde_assistir.py — descobre em quais streamings do Brasil cada título está.

Usa a mesma chave do TMDB (arquivo .env com TMDB_API_KEY=...). O TMDB recebe esses
dados da JustWatch. Guardamos só os streamings POR ASSINATURA (Netflix, Prime Video,
Max, Disney+...); aluguel e compra ficam de fora, mas anotamos se existem.

Como usar (na pasta do projeto):
    python importadores/importar_onde_assistir.py            -> os que nunca foram consultados
                                                                 ou que foram há mais de 30 dias
    python importadores/importar_onde_assistir.py --refazer  -> consulta todos de novo

Os catálogos dos streamings mudam todo mês: rode de vez em quando para atualizar.
"""
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))  # deixa achar as pastas cineai/ e importadores/
import json
import sys
from datetime import date, timedelta

from cineai import streamings                       # noqa: E402
from importadores import importar_tmdb as tmdb       # noqa: E402

PAIS = "BR"
DIAS_PARA_CONSULTAR_DE_NOVO = 30
SALVAR_A_CADA = 50
TIPOS_DE_ASSINATURA = ("flatrate", "ads")   # assinatura comum e planos com anúncios


def carregar_catalogo():
    if not tmdb.CAMINHO_JSON.exists():
        print(f"ERRO: {tmdb.CAMINHO_JSON} não encontrado. Rode o importadores/importar_tmdb.py primeiro.")
        sys.exit(1)
    with open(tmdb.CAMINHO_JSON, "r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def salvar_catalogo(catalogo):
    """Grava primeiro num arquivo temporário, para nunca corromper o original."""
    caminho_temporario = tmdb.CAMINHO_JSON.with_suffix(".tmp")
    with open(caminho_temporario, "w", encoding="utf-8") as arquivo:
        json.dump(catalogo, arquivo, ensure_ascii=False, indent=2)
    caminho_temporario.replace(tmdb.CAMINHO_JSON)


def precisa_consultar(filme, refazer):
    if filme.get("id") is None:
        return False
    if refazer:
        return True
    registro = filme.get("onde_assistir")
    if not isinstance(registro, dict):
        return True
    try:
        consultado_em = date.fromisoformat(registro.get("consultado_em") or "")
    except ValueError:
        return True
    return date.today() - consultado_em > timedelta(days=DIAS_PARA_CONSULTAR_DE_NOVO)


def buscar_onde_assistir(filme):
    """Pergunta ao TMDB onde o título está no Brasil. None se a consulta falhar."""
    caminho = "tv" if filme.get("tipo") == "serie" else "movie"
    resposta = tmdb.requisitar(f"/{caminho}/{filme['id']}/watch/providers")
    if resposta is None:
        return None

    no_brasil = (resposta.get("results") or {}).get(PAIS) or {}
    nomes = [
        provedor.get("provider_name", "")
        for tipo in TIPOS_DE_ASSINATURA
        for provedor in no_brasil.get(tipo, [])
    ]
    return {
        "assinatura": streamings.padronizar_lista(nomes),
        "aluguel_ou_compra": bool(no_brasil.get("rent") or no_brasil.get("buy")),
        "link": no_brasil.get("link"),
        "consultado_em": date.today().isoformat(),
    }


def importar_onde_assistir(refazer=False):
    tmdb.chave_api = tmdb.ler_chave_api()
    catalogo = carregar_catalogo()
    pendentes = [filme for filme in catalogo if precisa_consultar(filme, refazer)]

    if not pendentes:
        print(
            "Todos os títulos foram consultados nos últimos "
            f"{DIAS_PARA_CONSULTAR_DE_NOVO} dias. Use --refazer para consultar de novo."
        )
        return

    print(f"Procurando onde assistir {len(pendentes)} títulos (streamings do Brasil)...\n")

    em_algum_streaming = 0
    contagem_por_streaming = {}
    for posicao, filme in enumerate(pendentes, start=1):
        registro = buscar_onde_assistir(filme)
        if registro is None:
            print(f'[{posicao:>4}/{len(pendentes)}] {filme["nome"]}: — não encontrado no TMDB')
            continue

        filme["onde_assistir"] = registro
        lista = registro["assinatura"]
        if lista:
            em_algum_streaming += 1
            for nome in lista:
                contagem_por_streaming[nome] = contagem_por_streaming.get(nome, 0) + 1
            situacao = "📺 " + ", ".join(lista)
        else:
            situacao = "— fora dos streamings por assinatura"
        print(f'[{posicao:>4}/{len(pendentes)}] {filme["nome"]}: {situacao}')

        if posicao % SALVAR_A_CADA == 0:
            salvar_catalogo(catalogo)

    salvar_catalogo(catalogo)

    print(f"\nPronto! {em_algum_streaming} de {len(pendentes)} títulos estão em algum streaming por assinatura.")
    for nome, quantidade in sorted(contagem_por_streaming.items(), key=lambda par: -par[1]):
        print(f"   {nome}: {quantidade}")
    print("\nDados de streaming: JustWatch (via TMDB).")


if __name__ == "__main__":
    importar_onde_assistir(refazer="--refazer" in sys.argv)