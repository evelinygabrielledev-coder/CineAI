"""
importar_series.py — adiciona SÉRIES do TMDB ao mesmo catálogo dos filmes.

Usa a mesma chave do TMDB do importar_tmdb.py (arquivo .env com TMDB_API_KEY=...).
As séries entram no filmes.json com "tipo": "serie", ao lado dos filmes.
Os filmes que já estão lá não são alterados.

Como usar (na pasta do projeto):
    python importadores/importar_series.py

Depois, para completar:
    python importadores/importar_avaliacoes.py   -> IMDb / Rotten das séries novas
    python importadores/importar_trailers.py     -> trailers das séries novas

Pode rodar de novo quando quiser: as séries são atualizadas (temporadas,
status...) e as notas que já foram importadas continuam.
"""
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))  # deixa achar as pastas cineai/ e importadores/
import json

from importadores import importar_tmdb as tmdb  # noqa: E402

QUANTIDADE_SERIES = 400
MAXIMO_ATORES = 6

# Programas que não são "séries para assistir" ficam de fora.
GENEROS_EXCLUIDOS = {
    10763,  # Notícias
    10764,  # Reality
    10767,  # Talk show
}

# Na TV, o TMDB junta alguns gêneros ("Action & Adventure"). Separamos para
# ficarem iguais aos dos filmes: assim "uma série de ação" e o seu perfil funcionam.
GENEROS_SEPARADOS = {
    10759: ["Ação", "Aventura"],
    10765: ["Ficção científica", "Fantasia"],
    10768: ["Guerra", "Política"],
    10762: ["Família"],   # Kids
    10766: ["Novela"],    # Soap
}

STATUS_EM_PORTUGUES = {
    "Returning Series": "Em exibição",
    "In Production": "Em produção",
    "Planned": "Planejada",
    "Pilot": "Piloto",
    "Ended": "Finalizada",
    "Canceled": "Cancelada",
}


# =========================================================
# CONVERSÃO PARA O FORMATO DO CINEAI
# =========================================================
def generos_da_serie(detalhes):
    generos = []
    for genero in detalhes.get("genres", []):
        nomes = GENEROS_SEPARADOS.get(genero["id"], [genero["name"]])
        for nome in nomes:
            if nome not in generos:
                generos.append(nome)
    return generos


def elenco_da_serie(detalhes):
    """Os atores que mais aparecem na série (aggregate_credits soma todas as temporadas)."""
    creditos = detalhes.get("aggregate_credits") or detalhes.get("credits") or {}
    elenco = sorted(
        creditos.get("cast", []),
        key=lambda pessoa: (-(pessoa.get("total_episode_count") or 0), pessoa.get("order", 999))
    )
    return [pessoa["name"] for pessoa in elenco[:MAXIMO_ATORES]]


def duracao_do_episodio(detalhes):
    duracoes = [minutos for minutos in detalhes.get("episode_run_time") or [] if minutos]
    if duracoes:
        return int(sum(duracoes) / len(duracoes))

    ultimo_episodio = detalhes.get("last_episode_to_air") or {}
    return ultimo_episodio.get("runtime") or None


def converter_serie(detalhes):
    """
    Transforma a resposta de /tv/{id} no formato do filmes.json.
    Retorna None se faltar algo essencial (sinopse, ano, criador ou gênero).
    """
    sinopse = (detalhes.get("overview") or "").strip()
    data_estreia = detalhes.get("first_air_date") or ""
    data_final = detalhes.get("last_air_date") or ""
    generos = generos_da_serie(detalhes)
    criadores = [pessoa["name"] for pessoa in detalhes.get("created_by", [])]
    ids_dos_generos = {genero["id"] for genero in detalhes.get("genres", [])}

    if sinopse == "" or len(data_estreia) < 4 or not criadores or not generos:
        return None
    if ids_dos_generos & GENEROS_EXCLUIDOS:
        return None

    status_original = detalhes.get("status", "")
    status = STATUS_EM_PORTUGUES.get(status_original, status_original or "—")
    ainda_em_exibicao = status_original in ("Returning Series", "In Production")

    nome = detalhes.get("name") or detalhes.get("original_name")
    externos = detalhes.get("external_ids") or {}

    return {
        "tipo": "serie",
        "id": detalhes["id"],
        "nome": nome,
        "titulo_original": detalhes.get("original_name", nome),
        "ano": int(data_estreia[:4]),
        "ano_final": None if ainda_em_exibicao or len(data_final) < 4 else int(data_final[:4]),
        "genero": ", ".join(generos),
        "diretor": ", ".join(criadores),   # nas séries, quem "dirige" é quem criou
        "elenco": elenco_da_serie(detalhes),
        "sinopse": sinopse,
        "duracao_minutos": duracao_do_episodio(detalhes),  # duração de UM episódio
        "temporadas": detalhes.get("number_of_seasons"),
        "episodios": detalhes.get("number_of_episodes"),
        "episodios_por_temporada": episodios_por_temporada(detalhes),
        "status": status,
        "nota_tmdb": round(detalhes.get("vote_average", 0), 1),
        "votos_tmdb": detalhes.get("vote_count", 0),
        "imdb_id": externos.get("imdb_id") or None,
        "trailer_youtube": tmdb.escolher_trailer(detalhes.get("videos")),
        "trailer_consultado": True,
        "poster": None,  # preenchido depois do download
        "caminho_poster_tmdb": detalhes.get("poster_path"),
        "premios": [],
        "indicacoes": []
    }


def episodios_por_temporada(detalhes):
    """[7, 13, 13, 13, 16]: quantos episódios tem cada temporada (sem os "especiais", temporada 0)."""
    temporadas = sorted(
        (temporada for temporada in detalhes.get("seasons", []) if (temporada.get("season_number") or 0) >= 1),
        key=lambda temporada: temporada["season_number"]
    )
    return [temporada.get("episode_count") or 0 for temporada in temporadas]


def buscar_e_converter_serie(id_serie):
    detalhes = tmdb.requisitar(
        f"/tv/{id_serie}",
        {
            "append_to_response": "aggregate_credits,videos,external_ids",
            "include_video_language": "pt,en,null"
        }
    )
    if detalhes is None or detalhes.get("adult"):
        return None
    return converter_serie(detalhes)


# =========================================================
# CATÁLOGO
# =========================================================
CAMPOS_PRESERVADOS = [
    "nota_imdb", "metacritic", "rotten_tomatoes", "omdb_consultado",
    "premios", "indicacoes"
]


def carregar_catalogo():
    if not tmdb.CAMINHO_JSON.exists():
        return []
    with open(tmdb.CAMINHO_JSON, "r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def salvar_catalogo(catalogo):
    caminho_temporario = tmdb.CAMINHO_JSON.with_suffix(".tmp")
    with open(caminho_temporario, "w", encoding="utf-8") as arquivo:
        json.dump(catalogo, arquivo, ensure_ascii=False, indent=2)
    caminho_temporario.replace(tmdb.CAMINHO_JSON)


def importar_series():
    tmdb.chave_api = tmdb.ler_chave_api()
    tmdb.PASTA_POSTERS.mkdir(parents=True, exist_ok=True)

    catalogo = carregar_catalogo()
    filmes_do_catalogo = [item for item in catalogo if item.get("tipo", "filme") != "serie"]
    series_antigas = {
        item["id"]: item for item in catalogo
        if item.get("tipo") == "serie" and item.get("id") is not None
    }

    print(f"Catálogo atual: {len(filmes_do_catalogo)} filmes e {len(series_antigas)} séries.")
    print(f"Buscando as {QUANTIDADE_SERIES} séries mais votadas do TMDB...\n")

    series_novas = []
    ids_usados = set()
    pagina = 1
    total_paginas = 1

    while len(series_novas) < QUANTIDADE_SERIES and pagina <= total_paginas:
        lista = tmdb.requisitar(
            "/discover/tv",
            {"sort_by": "vote_count.desc", "include_adult": "false", "page": pagina}
        )
        if lista is None:
            break

        total_paginas = min(lista.get("total_pages", 1), 500)

        for resumo in lista.get("results", []):
            if len(series_novas) >= QUANTIDADE_SERIES:
                break
            if resumo["id"] in ids_usados:
                continue
            if set(resumo.get("genre_ids", [])) & GENEROS_EXCLUIDOS:
                continue

            serie = buscar_e_converter_serie(resumo["id"])
            if serie is None:
                continue

            # Notas que o importar_avaliacoes.py já tinha trazido continuam.
            antiga = series_antigas.get(serie["id"])
            if antiga is not None:
                for campo in CAMPOS_PRESERVADOS:
                    if campo in antiga:
                        serie[campo] = antiga[campo]

            nome_poster = "serie_" + tmdb.criar_nome_poster(serie["nome"], serie["id"])
            serie["poster"] = tmdb.baixar_poster(serie.pop("caminho_poster_tmdb"), nome_poster)

            series_novas.append(serie)
            ids_usados.add(serie["id"])

            temporadas = serie["temporadas"] or 0
            print(
                f'[{len(series_novas):>3}/{QUANTIDADE_SERIES}] {serie["nome"]} ({serie["ano"]}) '
                f'• {temporadas} temporada{"s" if temporadas != 1 else ""} • {serie["status"]}'
            )

            if len(series_novas) % 25 == 0:
                salvar_catalogo(filmes_do_catalogo + series_novas)

        pagina += 1

    salvar_catalogo(filmes_do_catalogo + series_novas)

    print(
        f"\nPronto! {len(series_novas)} séries + {len(filmes_do_catalogo)} filmes "
        f"em {tmdb.CAMINHO_JSON.name}.\n"
        "Agora rode:  python importadores/importar_avaliacoes.py   (notas IMDb/Rotten das séries)"
    )


if __name__ == "__main__":
    importar_series()
