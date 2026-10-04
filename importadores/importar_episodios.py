"""
importar_episodios.py — descobre quantos episódios tem cada temporada das séries do catálogo.

O CineAI usa isso no "onde eu parei" das séries (S02E05): para saber que depois do
último episódio da temporada 1 vem o S02E01, e quando você terminou a série.
Sem isso ele funciona do mesmo jeito, só não sabe onde cada temporada acaba.

Como usar (na pasta do projeto; usa a chave do TMDB do .env):
    python importadores/importar_episodios.py            -> só as séries que ainda não têm
    python importadores/importar_episodios.py --refazer  -> todas de novo (séries em exibição ganham temporadas)
"""
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))  # deixa achar as pastas cineai/ e importadores/
import json
import sys

from importadores import importar_tmdb as tmdb           # noqa: E402
from importadores.importar_series import episodios_por_temporada  # noqa: E402

SALVAR_A_CADA = 25


def salvar_catalogo(catalogo):
    temporario = tmdb.CAMINHO_JSON.with_suffix(".tmp")
    with open(temporario, "w", encoding="utf-8") as arquivo:
        json.dump(catalogo, arquivo, ensure_ascii=False, indent=2)
    temporario.replace(tmdb.CAMINHO_JSON)


def importar_episodios(refazer=False):
    tmdb.chave_api = tmdb.ler_chave_api()
    with open(tmdb.CAMINHO_JSON, "r", encoding="utf-8") as arquivo:
        catalogo = json.load(arquivo)

    series = [
        titulo for titulo in catalogo
        if titulo.get("tipo") == "serie" and titulo.get("id") is not None
        and (refazer or not titulo.get("episodios_por_temporada"))
    ]
    if not series:
        print("Todas as séries já sabem os episódios de cada temporada. Use --refazer para atualizar.")
        return

    print(f"Buscando os episódios de {len(series)} séries...\n")
    for posicao, serie in enumerate(series, start=1):
        detalhes = tmdb.requisitar(f"/tv/{serie['id']}")
        if detalhes is None:
            print(f"[{posicao:>3}/{len(series)}] {serie['nome']}: não encontrada no TMDB")
            continue
        serie["episodios_por_temporada"] = episodios_por_temporada(detalhes)
        serie["temporadas"] = detalhes.get("number_of_seasons") or serie.get("temporadas")
        serie["episodios"] = detalhes.get("number_of_episodes") or serie.get("episodios")
        print(f"[{posicao:>3}/{len(series)}] {serie['nome']}: {serie['episodios_por_temporada']}")
        if posicao % SALVAR_A_CADA == 0:
            salvar_catalogo(catalogo)

    salvar_catalogo(catalogo)
    print("\nPronto!")


if __name__ == "__main__":
    importar_episodios(refazer="--refazer" in sys.argv)
