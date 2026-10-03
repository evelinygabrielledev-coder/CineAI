"""
Importa filmes do TMDB para o filmes.json do CineAI.

Como usar:
    1. Crie um arquivo chamado .env nesta mesma pasta com a linha:
           TMDB_API_KEY=sua_chave_aqui
    2. Rode:
           python importar_tmdb.py

O que o script faz:
    - Faz uma cópia do filmes.json atual em filmes_manual.json (só na 1ª vez).
    - Busca no TMDB os filmes do catálogo manual, mantendo prêmios,
      indicações e Rotten Tomatoes que você cadastrou à mão.
    - Completa o catálogo com os filmes mais votados do TMDB.
    - Baixa os pôsteres para a pasta posters/.
    - Grava o novo filmes.json.

Pode rodar de novo quando quiser: pôsteres já baixados não são baixados outra vez.
"""

import json
import os
import re
import shutil
import sys
import time
import unicodedata
from pathlib import Path

import requests


# =========================================================
# CONFIGURAÇÕES
# =========================================================
# OPÇÃO 1 (mais simples): cole sua chave entre as aspas abaixo.
#   Ex.: CHAVE_API_MANUAL = "a1b2c3d4e5f6..."
#   Atenção: não compartilhe este arquivo nem suba para o GitHub com a chave.
# OPÇÃO 2 (recomendada): deixe vazio e use o arquivo .env.
CHAVE_API_MANUAL = ""

PASTA_PROJETO = Path(__file__).resolve().parent
CAMINHO_ENV = PASTA_PROJETO / ".env"

# Nomes que o Windows/Bloco de Notas às vezes cria sem querer.
NOMES_ALTERNATIVOS_ENV = [".env", ".env.txt", "arquivo.env", "env", "env.txt"]
CAMINHO_JSON = PASTA_PROJETO / "filmes.json"
CAMINHO_BACKUP_MANUAL = PASTA_PROJETO / "filmes_manual.json"
PASTA_POSTERS = PASTA_PROJETO / "posters"

QUANTIDADE_FILMES = 1500
MAXIMO_ATORES = 6

URL_API = "https://api.themoviedb.org/3"
URL_IMAGENS = "https://image.tmdb.org/t/p/w342"
IDIOMA = "pt-BR"

TENTATIVAS_MAXIMAS = 4
PAUSA_ENTRE_REQUISICOES = 0.05  # segundos (o limite do TMDB é bem maior)


# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================
def normalizar_texto(texto):
    """Remove acentos e converte para minúsculas."""
    texto = unicodedata.normalize("NFD", str(texto))
    texto = "".join(
        caractere
        for caractere in texto
        if unicodedata.category(caractere) != "Mn"
    )
    return texto.lower()


def criar_nome_poster(nome_filme, id_filme):
    """Ex.: ("Interestelar", 157336) -> "interestelar_157336.jpg"."""
    nome = re.sub(r"[^a-z0-9]+", "_", normalizar_texto(nome_filme)).strip("_")
    return f"{nome}_{id_filme}.jpg"


def limpar_valor(valor):
    """Tira espaços e aspas: '  "abc123" ' -> 'abc123'."""
    return valor.strip().strip('"').strip("'").strip()


def parece_chave_v3(texto):
    """A API Key (v3) do TMDB tem 32 caracteres hexadecimais."""
    return re.fullmatch(r"[0-9a-fA-F]{32}", texto) is not None


def extrair_chave_do_arquivo(caminho):
    """
    Aceita:  TMDB_API_KEY=abc...   |   TMDB_API_KEY = "abc..."   |   só abc...
    'utf-8-sig' remove o caractere invisível (BOM) que o Bloco de Notas coloca.
    """
    with open(caminho, "r", encoding="utf-8-sig") as arquivo:
        linhas = arquivo.read().splitlines()

    for linha in linhas:
        linha = linha.strip()

        if linha == "" or linha.startswith("#"):
            continue

        if "=" in linha:
            nome_variavel, valor = linha.split("=", 1)
            if limpar_valor(nome_variavel).upper() == "TMDB_API_KEY":
                return limpar_valor(valor)

        elif parece_chave_v3(limpar_valor(linha)):
            return limpar_valor(linha)  # a pessoa colou só a chave

    return None


def listar_arquivos_env():
    """
    Ordem de procura:
      1º os nomes conhecidos (.env, .env.txt, ...);
      2º qualquer outro arquivo terminado em .env ou .env.txt (ex.: kara.env).
    """
    arquivos_encontrados = []

    for nome_arquivo in NOMES_ALTERNATIVOS_ENV:
        if (PASTA_PROJETO / nome_arquivo).is_file():
            arquivos_encontrados.append(nome_arquivo)

    for caminho in sorted(PASTA_PROJETO.iterdir()):
        nome_minusculo = caminho.name.lower()
        termina_com_env = (
            nome_minusculo.endswith(".env")
            or nome_minusculo.endswith(".env.txt")
        )

        if (
            caminho.is_file()
            and termina_com_env
            and caminho.name not in arquivos_encontrados
            and nome_minusculo != ".env.example"
        ):
            arquivos_encontrados.append(caminho.name)

    return arquivos_encontrados


def ler_chave_api():
    """Procura a chave: no código, nos arquivos .env ou no ambiente."""
    if limpar_valor(CHAVE_API_MANUAL):
        return limpar_valor(CHAVE_API_MANUAL)

    for nome_arquivo in listar_arquivos_env():
        caminho = PASTA_PROJETO / nome_arquivo

        chave = extrair_chave_do_arquivo(caminho)

        if chave:
            if nome_arquivo != ".env":
                print(f'Aviso: usei a chave do arquivo "{nome_arquivo}".')
            return chave

        print(f'Aviso: achei "{nome_arquivo}", mas não encontrei a chave dentro dele.')

    chave_ambiente = os.environ.get("TMDB_API_KEY")
    if chave_ambiente:
        return limpar_valor(chave_ambiente)

    # Não achou: mostra o que existe na pasta para ajudar a descobrir o problema.
    arquivos_parecidos = [
        caminho.name
        for caminho in PASTA_PROJETO.iterdir()
        if "env" in caminho.name.lower()
    ]

    print("ERRO: chave do TMDB não encontrada.\n")
    print(f"Pasta onde procurei:\n    {PASTA_PROJETO}\n")

    if arquivos_parecidos:
        print("Arquivos com 'env' no nome nessa pasta:")
        for nome in arquivos_parecidos:
            print(f"    {nome}")
        print()
    else:
        print("Nenhum arquivo com 'env' no nome existe nessa pasta.\n")

    print(
        "Como resolver (escolha um):\n"
        "  1) Abra importar_tmdb.py e cole a chave em CHAVE_API_MANUAL = \"...\"\n"
        "  2) Crie um arquivo .env nessa pasta com a linha:\n"
        "         TMDB_API_KEY=sua_chave_aqui"
    )
    sys.exit(1)


# =========================================================
# ACESSO À API
# =========================================================
sessao = requests.Session()
chave_api = None


def requisitar(caminho, parametros=None):
    """Faz um GET na API do TMDB, tentando de novo em caso de limite ou falha."""
    parametros_completos = {"api_key": chave_api, "language": IDIOMA}
    if parametros:
        parametros_completos.update(parametros)

    for tentativa in range(1, TENTATIVAS_MAXIMAS + 1):
        try:
            resposta = sessao.get(
                URL_API + caminho,
                params=parametros_completos,
                timeout=20
            )
        except requests.RequestException as erro:
            print(f"  Falha de conexão ({erro}). Tentativa {tentativa}...")
            time.sleep(2 * tentativa)
            continue

        if resposta.status_code == 401:
            print("ERRO: a chave do TMDB foi recusada. Confira o arquivo .env.")
            sys.exit(1)

        if resposta.status_code == 404:
            return None

        if resposta.status_code == 429 or resposta.status_code >= 500:
            espera = int(resposta.headers.get("Retry-After", 2 * tentativa))
            time.sleep(espera)
            continue

        resposta.raise_for_status()
        time.sleep(PAUSA_ENTRE_REQUISICOES)
        return resposta.json()

    print(f"  Desisti de {caminho} depois de {TENTATIVAS_MAXIMAS} tentativas.")
    return None


def baixar_poster(caminho_tmdb, nome_arquivo):
    """Baixa o pôster se ainda não existir. Retorna o nome do arquivo ou None."""
    if not caminho_tmdb:
        return None

    destino = PASTA_POSTERS / nome_arquivo

    if destino.exists():
        return nome_arquivo

    try:
        resposta = sessao.get(URL_IMAGENS + caminho_tmdb, timeout=30)
        resposta.raise_for_status()
    except requests.RequestException as erro:
        print(f"  Não consegui baixar o pôster ({erro}).")
        return None

    destino.write_bytes(resposta.content)
    return nome_arquivo


# =========================================================
# CONVERSÃO PARA O FORMATO DO CINEAI
# =========================================================
# =========================================================
# TRAILER (YouTube)
# =========================================================
# O trailer dublado/legendado em português vem primeiro; se não tiver, o em inglês.
PRIORIDADE_IDIOMA_TRAILER = {"pt": 0, "en": 1}
PRIORIDADE_TIPO_VIDEO = {"Trailer": 0, "Teaser": 1}


def escolher_trailer(videos):
    """
    Recebe a lista "videos" do TMDB e devolve o código do YouTube do melhor
    trailer (ex.: "zSWdZVtXT7E"), ou None se não houver nenhum.
    """
    if not videos:
        return None

    candidatos = [
        video for video in videos.get("results", [])
        if video.get("site") == "YouTube"
        and video.get("type") in PRIORIDADE_TIPO_VIDEO
        and video.get("key")
    ]
    if not candidatos:
        return None

    candidatos.sort(key=lambda video: (
        PRIORIDADE_TIPO_VIDEO[video["type"]],
        PRIORIDADE_IDIOMA_TRAILER.get(video.get("iso_639_1"), 2),
        0 if video.get("official") else 1,
        -(video.get("size") or 0),  # 1080p antes de 480p
    ))
    return candidatos[0]["key"]


def converter_filme(detalhes):
    """
    Transforma a resposta de /movie/{id} no formato do filmes.json.
    Retorna None se faltar algo essencial (sinopse, ano, diretor ou gênero).
    """
    sinopse = (detalhes.get("overview") or "").strip()
    data_lancamento = detalhes.get("release_date") or ""
    generos = [genero["name"] for genero in detalhes.get("genres", [])]

    creditos = detalhes.get("credits", {})
    diretores = [
        pessoa["name"]
        for pessoa in creditos.get("crew", [])
        if pessoa.get("job") == "Director"
    ]

    elenco_ordenado = sorted(
        creditos.get("cast", []),
        key=lambda pessoa: pessoa.get("order", 999)
    )
    elenco = [pessoa["name"] for pessoa in elenco_ordenado[:MAXIMO_ATORES]]

    if sinopse == "" or len(data_lancamento) < 4 or not diretores or not generos:
        return None

    id_filme = detalhes["id"]
    nome = detalhes.get("title") or detalhes.get("original_title")

    return {
        "tipo": "filme",
        "id": id_filme,
        "nome": nome,
        "titulo_original": detalhes.get("original_title", nome),
        "ano": int(data_lancamento[:4]),
        "genero": ", ".join(generos),
        "diretor": ", ".join(diretores),
        "elenco": elenco,
        "sinopse": sinopse,
        "duracao_minutos": detalhes.get("runtime") or None,
        "nota_tmdb": round(detalhes.get("vote_average", 0), 1),
        "votos_tmdb": detalhes.get("vote_count", 0),
        "poster": None,  # preenchido depois do download
        "caminho_poster_tmdb": detalhes.get("poster_path"),
        "trailer_youtube": escolher_trailer(detalhes.get("videos")),
        "trailer_consultado": True,  # o trailer já veio junto: o importar_trailers.py não precisa repetir
        "premios": [],
        "indicacoes": []
    }


def buscar_e_converter(id_filme):
    detalhes = requisitar(
        f"/movie/{id_filme}",
        {"append_to_response": "credits,videos", "include_video_language": "pt,en,null"}
    )
    if detalhes is None or detalhes.get("adult"):
        return None
    return converter_filme(detalhes)


# =========================================================
# CATÁLOGO MANUAL (os filmes que você já tinha)
# =========================================================
def carregar_catalogo_manual():
    """Na 1ª execução, guarda o filmes.json atual como filmes_manual.json."""
    if not CAMINHO_BACKUP_MANUAL.exists():
        if not CAMINHO_JSON.exists():
            return []
        shutil.copy(CAMINHO_JSON, CAMINHO_BACKUP_MANUAL)
        print(f"Backup do catálogo manual salvo em {CAMINHO_BACKUP_MANUAL.name}")

    with open(CAMINHO_BACKUP_MANUAL, "r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def procurar_id_no_tmdb(filme_manual):
    """Procura o filme manual no TMDB pelo nome e ano."""
    resultado = requisitar(
        "/search/movie",
        {"query": filme_manual["nome"], "year": filme_manual.get("ano")}
    )

    if not resultado or not resultado.get("results"):
        # Tenta sem o ano (às vezes o ano de lançamento difere)
        resultado = requisitar("/search/movie", {"query": filme_manual["nome"]})

    if not resultado or not resultado.get("results"):
        return None

    return resultado["results"][0]["id"]


def copiar_dados_manuais(filme_novo, filme_manual):
    """Mantém o que só existe no seu cadastro manual."""
    for campo in ["premios", "indicacoes", "rotten_tomatoes"]:
        if filme_manual.get(campo):
            filme_novo[campo] = filme_manual[campo]


# Campos preenchidos pelo importar_avaliacoes.py. Se você reimportar o
# catálogo, eles são copiados do filmes.json atual para não se perderem.
CAMPOS_DE_AVALIACAO = [
    "imdb_id", "nota_imdb", "metacritic", "rotten_tomatoes", "omdb_consultado"
]


def carregar_avaliacoes_existentes():
    """{id_tmdb: filme} do filmes.json atual (só filmes que já têm id)."""
    if not CAMINHO_JSON.exists():
        return {}

    with open(CAMINHO_JSON, "r", encoding="utf-8") as arquivo:
        catalogo_atual = json.load(arquivo)

    return {
        filme["id"]: filme
        for filme in catalogo_atual
        if filme.get("id") is not None and filme.get("tipo", "filme") != "serie"
    }


def carregar_series_existentes():
    """As séries (importar_series.py) continuam no catálogo quando os filmes são reimportados."""
    if not CAMINHO_JSON.exists():
        return []

    with open(CAMINHO_JSON, "r", encoding="utf-8") as arquivo:
        catalogo_atual = json.load(arquivo)

    return [item for item in catalogo_atual if item.get("tipo") == "serie"]


def preservar_avaliacoes(filme_novo, avaliacoes_existentes):
    filme_existente = avaliacoes_existentes.get(filme_novo["id"])
    if filme_existente is None:
        return

    for campo in CAMPOS_DE_AVALIACAO:
        if campo in filme_existente:
            filme_novo[campo] = filme_existente[campo]

    # Trailer salvo antes pelo importar_trailers.py continua, se agora não veio nenhum.
    if not filme_novo.get("trailer_youtube") and filme_existente.get("trailer_youtube"):
        filme_novo["trailer_youtube"] = filme_existente["trailer_youtube"]


# =========================================================
# PROGRAMA PRINCIPAL
# =========================================================
def adicionar_ao_catalogo(catalogo, ids_no_catalogo, filme):
    nome_poster = criar_nome_poster(filme["nome"], filme["id"])
    filme["poster"] = baixar_poster(filme.pop("caminho_poster_tmdb"), nome_poster)

    catalogo.append(filme)
    ids_no_catalogo.add(filme["id"])

    print(f'[{len(catalogo):>3}/{QUANTIDADE_FILMES}] {filme["nome"]} ({filme["ano"]})')


def importar():
    global chave_api
    chave_api = ler_chave_api()

    PASTA_POSTERS.mkdir(exist_ok=True)

    catalogo = []
    ids_no_catalogo = set()

    # 1) Filmes do catálogo manual primeiro
    catalogo_manual = carregar_catalogo_manual()
    avaliacoes_existentes = carregar_avaliacoes_existentes()
    print(f"\nProcurando os {len(catalogo_manual)} filmes do catálogo manual...")

    for filme_manual in catalogo_manual:
        id_filme = procurar_id_no_tmdb(filme_manual)

        if id_filme is None:
            print(f'  Não encontrei "{filme_manual["nome"]}" no TMDB, ficou de fora.')
            continue

        if id_filme in ids_no_catalogo:
            continue  # o mesmo filme apareceu duas vezes no catálogo manual

        filme_novo = buscar_e_converter(id_filme)
        if filme_novo is None:
            print(f'  "{filme_manual["nome"]}" está incompleto no TMDB, ficou de fora.')
            continue

        copiar_dados_manuais(filme_novo, filme_manual)
        preservar_avaliacoes(filme_novo, avaliacoes_existentes)
        adicionar_ao_catalogo(catalogo, ids_no_catalogo, filme_novo)

    # 2) Completa com os filmes mais votados
    print("\nCompletando com os filmes mais votados do TMDB...")
    pagina = 1
    total_paginas = 1

    while len(catalogo) < QUANTIDADE_FILMES and pagina <= total_paginas:
        lista = requisitar(
            "/discover/movie",
            {
                "sort_by": "vote_count.desc",
                "include_adult": "false",
                "page": pagina
            }
        )

        if lista is None:
            break

        total_paginas = min(lista.get("total_pages", 1), 500)

        for resumo in lista.get("results", []):
            if len(catalogo) >= QUANTIDADE_FILMES:
                break

            if resumo["id"] in ids_no_catalogo:
                continue

            filme_novo = buscar_e_converter(resumo["id"])
            if filme_novo is not None:
                preservar_avaliacoes(filme_novo, avaliacoes_existentes)
                adicionar_ao_catalogo(catalogo, ids_no_catalogo, filme_novo)

        pagina += 1

    # 3) As séries que já existiam continuam no catálogo
    series_existentes = carregar_series_existentes()
    if series_existentes:
        print(f"\nMantendo as {len(series_existentes)} séries que já estavam no catálogo.")
    catalogo_com_series = catalogo + series_existentes

    # 4) Grava (primeiro num arquivo temporário, para não corromper o original)
    caminho_temporario = CAMINHO_JSON.with_suffix(".tmp")
    with open(caminho_temporario, "w", encoding="utf-8") as arquivo:
        json.dump(catalogo_com_series, arquivo, ensure_ascii=False, indent=2)
    caminho_temporario.replace(CAMINHO_JSON)

    sem_poster = sum(1 for filme in catalogo if filme["poster"] is None)
    print(
        f"\nPronto! {len(catalogo)} filmes salvos em {CAMINHO_JSON.name} "
        f"({sem_poster} sem pôster)."
    )


if __name__ == "__main__":
    importar()