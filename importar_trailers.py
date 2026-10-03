"""
importar_trailers.py — adiciona o trailer do YouTube aos filmes do filmes.json.

Usa a mesma chave do TMDB do importar_tmdb.py (arquivo .env com TMDB_API_KEY=...).
Não mexe em mais nada do catálogo: só preenche o campo "trailer_youtube".

Como usar (na pasta do projeto):
    python importar_trailers.py            -> só os filmes que ainda não foram consultados
    python importar_trailers.py --refazer  -> consulta todos de novo

Filmes sem trailer no TMDB continuam funcionando: o botão ▶ do CineAI
abre uma busca no YouTube pelo nome do filme.
"""
import json
import sys

import importar_tmdb as tmdb

SALVAR_A_CADA = 25  # grava o filmes.json a cada 25 filmes (se fechar no meio, não perde tudo)


def carregar_catalogo():
    if not tmdb.CAMINHO_JSON.exists():
        print(f"ERRO: {tmdb.CAMINHO_JSON.name} não encontrado. Rode o importar_tmdb.py primeiro.")
        sys.exit(1)

    with open(tmdb.CAMINHO_JSON, "r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def salvar_catalogo(catalogo):
    """Grava primeiro num arquivo temporário, para nunca corromper o original."""
    caminho_temporario = tmdb.CAMINHO_JSON.with_suffix(".tmp")
    with open(caminho_temporario, "w", encoding="utf-8") as arquivo:
        json.dump(catalogo, arquivo, ensure_ascii=False, indent=2)
    caminho_temporario.replace(tmdb.CAMINHO_JSON)


def buscar_trailer(id_filme, tipo="filme"):
    """Pede ao TMDB os vídeos do filme ou da série (português, inglês e sem idioma)."""
    caminho = "tv" if tipo == "serie" else "movie"
    videos = tmdb.requisitar(
        f"/{caminho}/{id_filme}/videos",
        {"language": "pt-BR", "include_video_language": "pt,en,null"}
    )
    return tmdb.escolher_trailer(videos)


def importar_trailers(refazer=False):
    tmdb.chave_api = tmdb.ler_chave_api()
    catalogo = carregar_catalogo()

    pendentes = [
        filme for filme in catalogo
        if filme.get("id") is not None
        and (refazer or not filme.get("trailer_consultado"))
    ]

    if not pendentes:
        print("Todos os filmes já foram consultados. Use --refazer para consultar de novo.")
        return

    print(f"Procurando trailers de {len(pendentes)} filmes...\n")

    encontrados = 0
    for posicao, filme in enumerate(pendentes, start=1):
        codigo_video = buscar_trailer(filme["id"], filme.get("tipo", "filme"))

        filme["trailer_youtube"] = codigo_video
        filme["trailer_consultado"] = True

        if codigo_video:
            encontrados += 1
            situacao = "▶ trailer encontrado"
        else:
            situacao = "— sem trailer (o CineAI vai buscar no YouTube)"

        print(f'[{posicao:>3}/{len(pendentes)}] {filme["nome"]}: {situacao}')

        if posicao % SALVAR_A_CADA == 0:
            salvar_catalogo(catalogo)

    salvar_catalogo(catalogo)

    print(
        f"\nPronto! {encontrados} de {len(pendentes)} filmes têm trailer salvo "
        f"em {tmdb.CAMINHO_JSON.name}."
    )


if __name__ == "__main__":
    importar_trailers(refazer="--refazer" in sys.argv)