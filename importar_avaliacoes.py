"""
Adiciona Rotten Tomatoes, IMDb e Metacritic aos filmes do filmes.json,
usando a OMDb API (https://www.omdbapi.com).

Como usar:
    1. Peça uma chave grátis em https://www.omdbapi.com/apikey.aspx
       (escolha FREE; a chave chega por e-mail e precisa ser ATIVADA
       clicando no link do e-mail).
    2. No seu arquivo .env, acrescente uma linha:
           OMDB_API_KEY=sua_chave_omdb
       (a TMDB_API_KEY continua lá: ela é usada para achar o código IMDb.)
    3. Rode:
           python importar_avaliacoes.py

O plano grátis da OMDb permite 1.000 consultas por dia.
O progresso é salvo aos poucos: se parar no meio, rode de novo que
ele continua de onde parou (filmes já consultados são pulados).
Para consultar TODOS de novo:  python importar_avaliacoes.py --refazer
"""

import json
import os
import re
import sys
import time
from pathlib import Path

import requests


# =========================================================
# CONFIGURAÇÕES
# =========================================================
PASTA_PROJETO = Path(__file__).resolve().parent
CAMINHO_JSON = PASTA_PROJETO / "filmes.json"

URL_TMDB = "https://api.themoviedb.org/3"
URL_OMDB = "https://www.omdbapi.com/"

SALVAR_A_CADA = 25          # grava o filmes.json a cada 25 filmes
PAUSA_ENTRE_FILMES = 0.1    # segundos
TENTATIVAS_MAXIMAS = 3

sessao = requests.Session()


# =========================================================
# CHAVES (lidas do .env ou de qualquer arquivo terminado em .env)
# =========================================================
def listar_arquivos_env():
    arquivos_env = []

    if (PASTA_PROJETO / ".env").is_file():
        arquivos_env.append(PASTA_PROJETO / ".env")

    for caminho in sorted(PASTA_PROJETO.iterdir()):
        nome_minusculo = caminho.name.lower()
        if (
            caminho.is_file()
            and caminho not in arquivos_env
            and nome_minusculo != ".env.example"
            and (nome_minusculo.endswith(".env") or nome_minusculo.endswith(".env.txt"))
        ):
            arquivos_env.append(caminho)

    return arquivos_env


def ler_variavel(nome_variavel):
    """Procura NOME=valor nos arquivos .env e, por último, no ambiente."""
    for caminho in listar_arquivos_env():
        # utf-8-sig remove o caractere invisível que o Bloco de Notas coloca
        with open(caminho, "r", encoding="utf-8-sig") as arquivo:
            for linha in arquivo:
                linha = linha.strip()
                if linha.startswith("#") or "=" not in linha:
                    continue

                nome, valor = linha.split("=", 1)
                if nome.strip().upper() == nome_variavel:
                    valor = valor.strip().strip('"').strip("'").strip()
                    if valor:
                        return valor

    return os.environ.get(nome_variavel)


def exigir_variavel(nome_variavel, como_conseguir):
    valor = ler_variavel(nome_variavel)

    if not valor:
        print(
            f"ERRO: {nome_variavel} não encontrada.\n"
            f"Acrescente no seu arquivo .env a linha:\n"
            f"    {nome_variavel}=sua_chave\n\n"
            f"{como_conseguir}"
        )
        sys.exit(1)

    return valor


# =========================================================
# REQUISIÇÕES
# =========================================================
class LimiteDiarioAtingido(Exception):
    """A OMDb grátis deixa 1.000 consultas por dia; acabou a cota de hoje."""
    pass


def requisitar_json(url, parametros):
    for tentativa in range(1, TENTATIVAS_MAXIMAS + 1):
        try:
            resposta = sessao.get(url, params=parametros, timeout=20)
        except requests.RequestException as erro:
            print(f"  Falha de conexão ({erro}). Tentativa {tentativa}...")
            time.sleep(2 * tentativa)
            continue

        if resposta.status_code == 401:
            # A OMDb usa o código 401 para DUAS coisas: chave inválida e
            # limite diário atingido. A mensagem do corpo diz qual foi.
            try:
                corpo = resposta.json()
            except ValueError:
                corpo = {}
            mensagem = str(corpo.get("Error", ""))
            if "limit" in mensagem.lower():
                raise LimiteDiarioAtingido(mensagem)
            return {"erro_autenticacao": True, "mensagem": mensagem}

        if resposta.status_code == 429 or resposta.status_code >= 500:
            time.sleep(int(resposta.headers.get("Retry-After", 2 * tentativa)))
            continue

        if resposta.status_code == 404:
            return None

        try:
            return resposta.json()
        except ValueError:
            return None

    return None


def buscar_imdb_id(id_tmdb, chave_tmdb, tipo="filme"):
    caminho = "tv" if tipo == "serie" else "movie"  # filmes e séries ficam em lugares diferentes no TMDB
    dados = requisitar_json(
        f"{URL_TMDB}/{caminho}/{id_tmdb}/external_ids",
        {"api_key": chave_tmdb}
    )

    if dados and dados.get("erro_autenticacao"):
        print("ERRO: a chave do TMDB foi recusada. Confira o .env.")
        sys.exit(1)

    if not dados:
        return None

    return dados.get("imdb_id") or None


def consultar_omdb(imdb_id, chave_omdb):
    dados = requisitar_json(URL_OMDB, {"i": imdb_id, "apikey": chave_omdb})

    if dados is None:
        return None

    if dados.get("erro_autenticacao"):
        print(
            "ERRO: a OMDb recusou a chave.\n"
            "Confira se você clicou no link de ATIVAÇÃO que veio no e-mail."
        )
        sys.exit(1)

    if dados.get("Response") == "False":
        mensagem_erro = dados.get("Error", "")

        if "limit" in mensagem_erro.lower():
            raise LimiteDiarioAtingido(mensagem_erro)

        if "invalid api key" in mensagem_erro.lower():
            print(
                "ERRO: a OMDb diz que a chave é inválida.\n"
                "Confira a OMDB_API_KEY no .env e se ela foi ATIVADA pelo e-mail."
            )
            sys.exit(1)

        return None  # filme não encontrado na OMDb

    return dados


# =========================================================
# CONVERSÃO DAS NOTAS
# =========================================================
def numero_ou_none(texto, padrao):
    """'87%' -> 87 | '8.8/10' -> 8.8 | 'N/A' -> None"""
    if not texto or texto == "N/A":
        return None

    encontrado = re.search(padrao, texto.replace(",", "."))
    if not encontrado:
        return None

    valor = float(encontrado.group(1))
    return int(valor) if valor.is_integer() else valor


def extrair_notas(dados_omdb):
    notas = {"rotten": None, "imdb": None, "metacritic": None}

    for avaliacao in dados_omdb.get("Ratings", []):
        fonte = avaliacao.get("Source", "")
        valor = avaliacao.get("Value", "")

        if fonte == "Rotten Tomatoes":
            notas["rotten"] = numero_ou_none(valor, r"(\d+)\s*%")
        elif fonte == "Internet Movie Database":
            notas["imdb"] = numero_ou_none(valor, r"([\d.]+)\s*/\s*10")
        elif fonte == "Metacritic":
            notas["metacritic"] = numero_ou_none(valor, r"(\d+)\s*/\s*100")

    # Campos soltos, caso a lista "Ratings" venha incompleta
    if notas["imdb"] is None:
        notas["imdb"] = numero_ou_none(dados_omdb.get("imdbRating"), r"([\d.]+)")
    if notas["metacritic"] is None:
        notas["metacritic"] = numero_ou_none(dados_omdb.get("Metascore"), r"(\d+)")

    return notas


def aplicar_notas(filme, notas):
    """Grava as notas no filme, sem apagar a nota do público que você cadastrou."""
    if notas["rotten"] is not None:
        rotten_atual = filme.get("rotten_tomatoes")
        publico_manual = None

        if isinstance(rotten_atual, dict) and rotten_atual.get("publico"):
            publico_manual = rotten_atual["publico"]

        filme["rotten_tomatoes"] = {
            "critica": notas["rotten"],
            "publico": publico_manual
        }

    if notas["imdb"] is not None:
        filme["nota_imdb"] = notas["imdb"]

    if notas["metacritic"] is not None:
        filme["metacritic"] = notas["metacritic"]


# =========================================================
# ARQUIVO
# =========================================================
def salvar_catalogo(catalogo):
    caminho_temporario = CAMINHO_JSON.with_suffix(".tmp")
    with open(caminho_temporario, "w", encoding="utf-8") as arquivo:
        json.dump(catalogo, arquivo, ensure_ascii=False, indent=2)
    caminho_temporario.replace(CAMINHO_JSON)


# =========================================================
# PROGRAMA PRINCIPAL
# =========================================================
def importar_avaliacoes(refazer=False):
    chave_tmdb = exigir_variavel(
        "TMDB_API_KEY",
        "É a mesma chave que você usou no importar_tmdb.py."
    )
    chave_omdb = exigir_variavel(
        "OMDB_API_KEY",
        "Peça uma chave grátis em https://www.omdbapi.com/apikey.aspx\n"
        "e ative pelo link que chega no e-mail."
    )

    with open(CAMINHO_JSON, "r", encoding="utf-8") as arquivo:
        catalogo = json.load(arquivo)

    filmes_pendentes = [
        filme for filme in catalogo
        if refazer or not filme.get("omdb_consultado")
    ]

    total_pendente = len(filmes_pendentes)
    print(f"{total_pendente} filmes para consultar (de {len(catalogo)}).\n")

    if total_pendente == 0:
        print("Nada a fazer. Use --refazer para consultar todos de novo.")
        return

    com_rotten = 0
    consultados = 0

    try:
        for posicao, filme in enumerate(filmes_pendentes, start=1):
            prefixo = f'[{posicao:>3}/{total_pendente}] {filme["nome"]} ({filme["ano"]})'

            if not filme.get("imdb_id") and filme.get("id") is not None:
                filme["imdb_id"] = buscar_imdb_id(filme["id"], chave_tmdb, filme.get("tipo", "filme"))

            if not filme.get("imdb_id"):
                print(f"{prefixo}: sem código IMDb, pulei.")
                filme["omdb_consultado"] = True
                continue

            dados_omdb = consultar_omdb(filme["imdb_id"], chave_omdb)
            filme["omdb_consultado"] = True
            consultados += 1

            if dados_omdb is None:
                print(f"{prefixo}: não encontrado na OMDb.")
                continue

            notas = extrair_notas(dados_omdb)
            aplicar_notas(filme, notas)

            partes = []
            if notas["rotten"] is not None:
                partes.append(f'🍅 {notas["rotten"]}%')
                com_rotten += 1
            if notas["imdb"] is not None:
                partes.append(f'IMDb {notas["imdb"]}')
            if notas["metacritic"] is not None:
                partes.append(f'Metacritic {notas["metacritic"]}')

            print(f'{prefixo}: {" | ".join(partes) if partes else "sem notas"}')

            if consultados % SALVAR_A_CADA == 0:
                salvar_catalogo(catalogo)

            time.sleep(PAUSA_ENTRE_FILMES)

    except LimiteDiarioAtingido as erro:
        # Este filme não foi consultado de verdade: desmarca para tentar amanhã.
        filme["omdb_consultado"] = False
        salvar_catalogo(catalogo)
        faltam = sum(1 for item in catalogo if not item.get("omdb_consultado"))
        print(
            f"\nA OMDb avisou: {erro or 'limite diário atingido'}\n"
            f"Isso é o limite de 1.000 consultas por dia do plano grátis (não é a chave).\n"
            f"O progresso foi salvo. Faltam {faltam} títulos: rode de novo amanhã para continuar."
        )
        return

    except SystemExit:
        salvar_catalogo(catalogo)  # nunca perde o que já foi consultado
        raise

    except KeyboardInterrupt:
        salvar_catalogo(catalogo)
        print("\nInterrompido. Progresso salvo; rode de novo para continuar.")
        return

    salvar_catalogo(catalogo)
    print(f"\nPronto! {com_rotten} de {consultados} filmes consultados têm nota no Rotten Tomatoes.")


if __name__ == "__main__":
    importar_avaliacoes(refazer="--refazer" in sys.argv)