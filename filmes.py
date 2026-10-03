"""
CineAI — o "cérebro" do assistente de filmes.

Fluxo de uma mensagem (processar_mensagem):
    saudação?            -> responde "olá"
    pedido de "outro"?   -> próximo filme dos mesmos critérios
    pergunta sobre o filme atual?  -> responde sobre ele
    senão                -> nova busca (filtros exatos + busca por significado)
"""

import hashlib
import json
import os
import pickle
import random
import difflib
import re
import time
from functools import lru_cache
import unicodedata
from urllib.parse import quote_plus
from datetime import date
from pathlib import Path

import numpy as np
import ollama
from sentence_transformers import SentenceTransformer

import perfil
import usuario
from rastreio import rastro


# =========================================================
# CONFIGURAÇÃO
# =========================================================
PASTA_PROJETO = Path(__file__).parent

# Os testes automáticos podem trocar o catálogo e o cache por versões de teste.
CAMINHO_JSON = Path(os.environ.get("CINEAI_CATALOGO", PASTA_PROJETO / "filmes.json"))
CAMINHO_CACHE_EMBEDDINGS = Path(os.environ.get("CINEAI_CACHE", PASTA_PROJETO / "embeddings_cache.pkl"))

MODELO_LLM = "qwen3:1.7b"
LIMITE_SIMILARIDADE = 0.25

# Busca híbrida: quanto vale ter as palavras da busca na sinopse.
# Ex.: busca "ogro resgata princesa" e a sinopse tem as 3 palavras -> +0.20
PESO_BONUS_PALAVRAS = 0.20

modelo = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

with open(CAMINHO_JSON, "r", encoding="utf-8") as arquivo:
    filmes = json.load(arquivo)


# =========================================================
# TEXTO
# =========================================================
def normalizar_texto(texto):
    """Remove acentos e converte para minúsculas: 'Comédia' -> 'comedia'."""
    texto = unicodedata.normalize("NFD", str(texto))
    texto = "".join(
        caractere
        for caractere in texto
        if unicodedata.category(caractere) != "Mn"
    )
    return texto.lower()


def extrair_palavras(texto):
    """'Quem dirigiu ELE?' -> ['quem', 'dirigiu', 'ele']"""
    return re.findall(r"[a-z0-9]+", normalizar_texto(texto))


def contem_alguma_palavra(texto, palavras_procuradas):
    """
    Verifica se alguma das palavras aparece no texto como palavra INTEIRA,
    ignorando acentos e maiúsculas.

    contem_alguma_palavra("De que ano ele é?", ["ano"])       -> True
    contem_alguma_palavra("Qual é o plano dele?", ["ano"])    -> False
    """
    palavras_do_texto = set(extrair_palavras(texto))

    for palavra in palavras_procuradas:
        if normalizar_texto(palavra) in palavras_do_texto:
            return True

    return False


def contem_expressao(texto, expressao):
    """
    Verifica se uma expressão de uma ou mais palavras aparece inteira.
    contem_expressao("filme com eddie murphy", "Eddie Murphy") -> True
    contem_expressao("filme sobre romances", "romance")        -> False
    """
    texto_espacado = " " + " ".join(extrair_palavras(texto)) + " "
    expressao_espacada = " " + " ".join(extrair_palavras(expressao)) + " "
    return expressao_espacada.strip() != "" and expressao_espacada in texto_espacado


# =========================================================
# CONVERSA COM O MODELO DE LINGUAGEM (OLLAMA)
# =========================================================
def perguntar_ao_modelo(prompt):
    """
    Envia o prompt ao Ollama e devolve só a resposta final.

    O qwen3 "pensa" antes de responder. Desligar isso (think=False) deixa
    a resposta bem mais rápida. Versões antigas da biblioteca não aceitam
    esse parâmetro, então tentamos sem ele se der erro. Também removemos
    qualquer bloco <think>...</think> que venha junto no texto.
    """
    mensagens = [{"role": "user", "content": prompt}]
    inicio = time.perf_counter()

    try:
        resposta = ollama.chat(model=MODELO_LLM, messages=mensagens, think=False)
    except TypeError:
        resposta = ollama.chat(model=MODELO_LLM, messages=mensagens)

    texto = resposta.message.content or ""
    texto = re.sub(r"<think>.*?</think>", "", texto, flags=re.DOTALL).strip()

    rastro.chamada_ia(
        finalidade_do_prompt(prompt),
        prompt,
        texto,
        (time.perf_counter() - inicio) * 1000
    )
    return texto


def finalidade_do_prompt(prompt):
    """Nome curto da tarefa, para o Painel do RAG."""
    if "Classifique a mensagem" in prompt:
        return "classificar intenção"
    if "Extraia apenas o assunto" in prompt:
        return "extrair assunto"
    return "responder pergunta"


# =========================================================
# EMBEDDINGS (com cache em arquivo)
# =========================================================
def montar_texto_completo(filme):
    elenco_texto = ", ".join(filme.get("elenco", []))

    return f"""
    Nome: {filme["nome"]}
    Gênero: {filme["genero"]}
    Ano: {filme["ano"]}
    Diretor: {filme["diretor"]}
    Elenco: {elenco_texto}
    Sinopse: {filme["sinopse"]}
    """


def chave_do_filme(filme):
    """Usa o id do TMDB quando existir; senão, o nome."""
    if filme.get("id") is not None:
        prefixo = "serie" if filme.get("tipo") == "serie" else "id"
        return f'{prefixo}:{filme["id"]}'
    return f'nome:{filme["nome"]}'


def assinatura_do_filme(texto_completo, sinopse):
    """Muda sempre que o texto do filme muda, invalidando o cache."""
    conteudo = (texto_completo + "||" + sinopse).encode("utf-8")
    return hashlib.md5(conteudo).hexdigest()


def carregar_cache_embeddings():
    if not CAMINHO_CACHE_EMBEDDINGS.exists():
        return {}

    try:
        with open(CAMINHO_CACHE_EMBEDDINGS, "rb") as arquivo:
            return pickle.load(arquivo)
    except Exception as erro:
        print(f"Cache de embeddings ignorado ({erro}). Recalculando...")
        return {}


def salvar_cache_embeddings(cache):
    caminho_temporario = CAMINHO_CACHE_EMBEDDINGS.with_suffix(".tmp")

    with open(caminho_temporario, "wb") as arquivo:
        pickle.dump(cache, arquivo)

    caminho_temporario.replace(CAMINHO_CACHE_EMBEDDINGS)


def normalizar_vetor(vetor):
    """Deixa o vetor com tamanho 1: assim, similaridade = produto escalar."""
    vetor = np.asarray(vetor, dtype=np.float32)
    tamanho = np.linalg.norm(vetor)

    if tamanho == 0:
        return vetor

    return vetor / tamanho


def preparar_embeddings():
    cache = carregar_cache_embeddings()
    filmes_pendentes = []

    for filme in filmes:
        texto_completo = montar_texto_completo(filme)
        assinatura = assinatura_do_filme(texto_completo, filme["sinopse"])
        item_cache = cache.get(chave_do_filme(filme))

        if item_cache is not None and item_cache["assinatura"] == assinatura:
            filme["embedding"] = item_cache["embedding"]
            filme["embedding_sinopse"] = item_cache["embedding_sinopse"]
        else:
            filmes_pendentes.append((filme, texto_completo, assinatura))

    if len(filmes_pendentes) > 0:
        print(
            f"Calculando embeddings de {len(filmes_pendentes)} filmes "
            "(só acontece uma vez)..."
        )

        embeddings_completos = modelo.encode(
            [texto for _, texto, _ in filmes_pendentes],
            batch_size=32,
            show_progress_bar=True
        )

        embeddings_sinopses = modelo.encode(
            [filme["sinopse"] for filme, _, _ in filmes_pendentes],
            batch_size=32,
            show_progress_bar=True
        )

        for posicao, (filme, _, assinatura) in enumerate(filmes_pendentes):
            filme["embedding"] = embeddings_completos[posicao]
            filme["embedding_sinopse"] = embeddings_sinopses[posicao]

            cache[chave_do_filme(filme)] = {
                "assinatura": assinatura,
                "embedding": embeddings_completos[posicao],
                "embedding_sinopse": embeddings_sinopses[posicao]
            }

        salvar_cache_embeddings(cache)

    # Vetores prontos para a busca (calculados uma vez, aqui).
    for filme in filmes:
        filme["vetor_sinopse"] = normalizar_vetor(filme["embedding_sinopse"])


preparar_embeddings()


# =========================================================
# ÍNDICES (montados uma vez, ao abrir o programa)
# =========================================================
# Palavras comuns que também são sobrenomes de atores/diretores.
# Sem esta lista, "filme de rock" viraria "filme com Chris Rock".
SOBRENOMES_AMBIGUOS = {
    "rock", "stone", "king", "black", "white", "love", "young", "wood",
    "bell", "hill", "long", "little", "rose", "cruz", "rosa", "costa",
    "lima", "silva", "santos", "ramos", "leal", "paz", "luz", "mar",
    "sol", "lobo", "pena", "neve", "ford", "park", "page", "fox", "west",
    "north", "hall", "lane", "ball", "bale", "pine", "gray", "grey",
    "hunt", "wolf", "rain", "moon", "star", "freeman", "lee"
}

TAMANHO_MINIMO_SOBRENOME = 4


def criar_indice_pessoas(nomes_por_filme):
    """
    Recebe a lista de nomes de cada filme e devolve:
      nomes_completos: {"christopher nolan": "Christopher Nolan", ...}
      sobrenomes:      {"nolan": ["Christopher Nolan"], "murphy": [...], ...}
      quantidade_filmes: {"Christopher Nolan": 8, ...}
    """
    nomes_completos = {}
    sobrenomes = {}
    quantidade_filmes = {}

    for nomes_do_filme in nomes_por_filme:
        for nome in nomes_do_filme:
            nome = nome.strip()
            if nome == "":
                continue

            quantidade_filmes[nome] = quantidade_filmes.get(nome, 0) + 1
            nomes_completos[" ".join(extrair_palavras(nome))] = nome

            palavras_nome = extrair_palavras(nome)
            if len(palavras_nome) >= 2:
                sobrenome = palavras_nome[-1]
                sobrenomes.setdefault(sobrenome, [])
                if nome not in sobrenomes[sobrenome]:
                    sobrenomes[sobrenome].append(nome)

    return nomes_completos, sobrenomes, quantidade_filmes


(
    diretores_por_nome,
    diretores_por_sobrenome,
    filmes_por_diretor
) = criar_indice_pessoas(
    [filme["diretor"].split(",") for filme in filmes]
)

(
    atores_por_nome,
    atores_por_sobrenome,
    filmes_por_ator
) = criar_indice_pessoas(
    [filme.get("elenco", []) for filme in filmes]
)


def encontrar_nome_completo(cliente, nomes_completos):
    """Procura um nome inteiro na mensagem ("Christopher Nolan")."""
    texto_normalizado = " " + " ".join(extrair_palavras(cliente)) + " "

    # Nomes mais longos primeiro: "Michael B. Jordan" antes de "Michael Jordan".
    for nome_normalizado in sorted(nomes_completos, key=len, reverse=True):
        if " " + nome_normalizado + " " in texto_normalizado:
            return nomes_completos[nome_normalizado]

    return None


SEMELHANCA_MINIMA_NOME = 0.84  # "simon becker" ≈ "simon baker" (0,87)


def encontrar_nome_parecido(cliente, nomes_completos):
    """
    Nome completo escrito com um errinho: "Simon Becker" -> "Simon Baker",
    "Leonardo Di Caprio" -> "Leonardo DiCaprio".
    Compara pedaços de 2 ou 3 palavras seguidas da mensagem com os nomes do
    catálogo (só os que começam com as mesmas letras, para ser rápido).
    """
    palavras = extrair_palavras(cliente)
    melhor_nome, melhor_semelhanca = None, SEMELHANCA_MINIMA_NOME

    for tamanho in (3, 2):
        for inicio in range(len(palavras) - tamanho + 1):
            pedaco = palavras[inicio:inicio + tamanho]
            if any(len(palavra) < 2 for palavra in pedaco):
                continue
            texto_pedaco = " ".join(pedaco)

            for nome_normalizado, nome in nomes_completos.items():
                # Filtro rápido: começa com as mesmas letras e tem tamanho parecido
                if nome_normalizado[:2] != texto_pedaco[:2]:
                    continue
                if abs(len(nome_normalizado) - len(texto_pedaco)) > 4:
                    continue
                semelhanca = difflib.SequenceMatcher(None, texto_pedaco, nome_normalizado).ratio()
                if semelhanca > melhor_semelhanca:
                    melhor_nome, melhor_semelhanca = nome, semelhanca

    return melhor_nome


def encontrar_por_sobrenome(cliente, sobrenomes, quantidade_filmes, palavras_usadas):
    """
    Procura só o sobrenome ("Nolan", "DiCaprio").
    Retorna (nome, sobrenome_usado) ou (None, None).
    Se o sobrenome for de várias pessoas, escolhe a com mais filmes.
    """
    for palavra in extrair_palavras(cliente):
        if palavra in palavras_usadas:
            continue  # já faz parte de um nome completo encontrado
        if len(palavra) < TAMANHO_MINIMO_SOBRENOME:
            continue
        if palavra in SOBRENOMES_AMBIGUOS:
            continue
        if palavra in sobrenomes:
            nome_escolhido = max(
                sobrenomes[palavra],
                key=lambda nome: quantidade_filmes[nome]
            )
            return nome_escolhido, palavra

    return None, None


PALAVRAS_ANTES_DE_DIRETOR = {"do", "da", "dirigido", "dirigida", "diretor", "diretora", "por"}
PALAVRAS_ANTES_DE_ATOR = {"com", "ator", "atriz", "estrelado", "estrelando", "protagonizado"}


def palavras_do_trecho_parecido(cliente, nome):
    """Palavras da mensagem que começam com as mesmas letras das do nome ("simon", "becker")."""
    iniciais = {palavra[:2] for palavra in extrair_palavras(nome)}
    return {palavra for palavra in extrair_palavras(cliente) if palavra[:2] in iniciais}


def palavra_anterior_de_nome(cliente, nome):
    """Palavra antes do primeiro nome da pessoa ("com" em "série com o simon becker")."""
    if not nome:
        return None
    palavras = extrair_palavras(cliente)
    primeiro = extrair_palavras(nome)[0][:3]
    for posicao in range(1, len(palavras)):
        if palavras[posicao][:3] == primeiro:
            anterior = palavras[posicao - 1]
            if anterior in {"o", "a"} and posicao >= 2:
                anterior = palavras[posicao - 2]  # "com o Simon"
            return anterior
    return None


def palavra_anterior(cliente, palavra_procurada):
    palavras = extrair_palavras(cliente)
    for posicao in range(1, len(palavras)):
        if palavras[posicao] == palavra_procurada:
            return palavras[posicao - 1]
    return None


@lru_cache(maxsize=256)  # a mesma mensagem é analisada várias vezes por resposta
def detectar_diretor_e_ator(cliente):
    """
    Devolve (diretor, ator) mencionados na mensagem.

    Ordem:
      1º nomes completos (diretor e ator);
      2º nomes completos com um errinho ("Simon Becker" -> Simon Baker);
      3º sobrenomes, sem reaproveitar palavras de um nome já encontrado
         ("com Eddie Murphy" não faz "Murphy" casar com um diretor Murphy).
    """
    diretor = encontrar_nome_completo(cliente, diretores_por_nome)
    ator = encontrar_nome_completo(cliente, atores_por_nome)

    # O pedaço da mensagem que casou com um nome parecido também fica "usado".
    palavras_usadas = set()

    if diretor is None and ator is None:
        ator_parecido = encontrar_nome_parecido(cliente, atores_por_nome)
        diretor_parecido = encontrar_nome_parecido(cliente, diretores_por_nome)
        anterior_ator = palavra_anterior_de_nome(cliente, ator_parecido)
        if ator_parecido and (diretor_parecido is None or anterior_ator in PALAVRAS_ANTES_DE_ATOR):
            ator = ator_parecido
        elif diretor_parecido:
            diretor = diretor_parecido
        for nome_parecido in (ator_parecido, diretor_parecido):
            if nome_parecido:
                palavras_usadas.update(palavras_do_trecho_parecido(cliente, nome_parecido))

    for nome in (diretor, ator):
        if nome is not None:
            palavras_usadas.update(extrair_palavras(nome))

    sobrenome_diretor = None
    sobrenome_ator = None

    if diretor is None:
        diretor, sobrenome_diretor = encontrar_por_sobrenome(
            cliente, diretores_por_sobrenome, filmes_por_diretor, palavras_usadas
        )

    if ator is None:
        ator, sobrenome_ator = encontrar_por_sobrenome(
            cliente, atores_por_sobrenome, filmes_por_ator, palavras_usadas
        )

    # A mesma pessoa como diretor e ator ("filme do Clint Eastwood"): fica diretor.
    if diretor is not None and diretor == ator:
        return diretor, None

    # O mesmo sobrenome casou um diretor E um ator diferentes: a palavra
    # anterior decide ("do Nolan" = diretor, "com Nolan" = ator).
    if sobrenome_diretor is not None and sobrenome_diretor == sobrenome_ator:
        anterior = palavra_anterior(cliente, sobrenome_diretor)

        if anterior in PALAVRAS_ANTES_DE_ATOR:
            return None, ator
        if anterior in PALAVRAS_ANTES_DE_DIRETOR:
            return diretor, None

        # Sem pista: fica com quem tem mais filmes no catálogo.
        if filmes_por_diretor[diretor] >= filmes_por_ator[ator]:
            return diretor, None
        return None, ator

    return diretor, ator


def detectar_diretor(cliente):
    return detectar_diretor_e_ator(cliente)[0]


def detectar_ator(cliente):
    return detectar_diretor_e_ator(cliente)[1]


PADRAO_DECADA = re.compile(r"\b(?:anos|decada de|decada dos|decada)\s+(\d{2}|\d{4})\b")


def detectar_decada(cliente):
    """
    "anos 2000" -> (2000, 2009) | "anos 90" -> (1990, 1999) | "década de 80" -> (1980, 1989)
    "anos 20" -> (2020, 2029). Sem década -> None.
    """
    encontrado = PADRAO_DECADA.search(" ".join(extrair_palavras(cliente)))
    if not encontrado:
        return None

    numero = int(encontrado.group(1))
    if numero < 100:
        numero += 2000 if numero <= 29 else 1900
    if numero % 10 != 0 or not 1880 <= numero <= 2100:
        return None
    return numero, numero + 9


def detectar_ano(cliente):
    if detectar_decada(cliente) is not None:
        return None  # "anos 2000" é a década inteira, não o ano 2000
    for ano_texto in re.findall(r"\b\d{4}\b", cliente):
        ano = int(ano_texto)
        if 1880 <= ano <= 2100:
            return ano
    return None


# ---------------- Gêneros ----------------
generos_conhecidos = set()

for filme in filmes:
    for genero in filme["genero"].split(","):
        if genero.strip():
            generos_conhecidos.add(" ".join(extrair_palavras(genero)))

# Outras formas de pedir um gênero -> nome do gênero no catálogo (sem acento).
SINONIMOS_GENERO = {
    "comedias": "comedia",
    "animacoes": "animacao",
    "desenho": "animacao",
    "desenhos": "animacao",
    "horror": "terror",
    "ficcao": "ficcao cientifica",
    "scifi": "ficcao cientifica",
    "romances": "romance",
    "romantico": "romance",
    "romantica": "romance",
    "dramas": "drama",
    "aventuras": "aventura",
    "suspense": "thriller",
    "policial": "crime",
    "documentarios": "documentario",
    "musical": "musica",
    "musicais": "musica",
    "faroeste": "faroeste",
    "western": "faroeste",
    "infantil": "familia",
    "guerras": "guerra",
}


def detectar_genero(cliente):
    """Devolve o gênero SEM acento ('comedia', 'ficcao cientifica') ou None."""

    # Gêneros de várias palavras primeiro ("ficcao cientifica" antes de "ficcao").
    for genero in sorted(generos_conhecidos, key=len, reverse=True):
        if contem_expressao(cliente, genero):
            return genero

    for palavra in extrair_palavras(cliente):
        genero_sinonimo = SINONIMOS_GENERO.get(palavra)
        if genero_sinonimo in generos_conhecidos:
            return genero_sinonimo

    if contem_expressao(cliente, "sci fi"):
        if "ficcao cientifica" in generos_conhecidos:
            return "ficcao cientifica"

    return None


def filme_tem_genero(filme, genero_normalizado):
    generos_filme = [
        " ".join(extrair_palavras(genero))
        for genero in filme["genero"].split(",")
    ]
    return genero_normalizado in generos_filme


def filme_tem_pessoa(lista_nomes, nome_procurado):
    nome_procurado = normalizar_texto(nome_procurado.strip())
    return any(
        normalizar_texto(nome.strip()) == nome_procurado
        for nome in lista_nomes
    )


# =========================================================
# QUALIDADE ("que a crítica amou", "bem avaliado"...)
# =========================================================
PALAVRAS_POSITIVAS = {
    "amou", "amaram", "ama", "adora", "adoram", "adorou", "adoraram",
    "gostou", "gostaram", "gosta", "elogiado", "elogiada", "elogiados",
    "elogiou", "elogiaram", "aclamado", "aclamada", "aclamados",
    "aprovou", "aprovado", "aprovada", "bem", "melhor", "melhores",
    "alta", "alto", "altas", "boa", "bom", "boas", "otima", "otimo",
    "excelente", "favorito", "favoritos"
}

PALAVRAS_DE_CRITICA = {"critica", "criticas", "critico", "criticos", "rotten", "tomatometro"}
PALAVRAS_DE_PUBLICO = {"publico", "espectadores", "audiencia", "pessoas", "galera", "fas"}

EXPRESSOES_DE_QUALIDADE_GERAL = [
    "bem avaliado", "bem avaliada", "bem avaliados", "bem avaliadas",
    "nota alta", "notas altas", "aclamado", "aclamada", "aclamados", "aclamadas",
    "obra prima", "obras primas", "melhores filmes", "melhor filme",
    "imperdivel", "imperdiveis"
]

# "Clássico" = bem avaliado E antigo.
PALAVRAS_DE_CLASSICO = {"classico", "classica", "classicos", "classicas"}
IDADE_MINIMA_CLASSICO = 20  # anos desde o lançamento

# Todas as palavras de qualidade: não podem virar "assunto" da busca.
# (montada a partir das listas acima, para nenhuma ficar de fora)
PALAVRAS_DE_QUALIDADE = (
    PALAVRAS_POSITIVAS | PALAVRAS_DE_CRITICA | PALAVRAS_DE_PUBLICO
    | PALAVRAS_DE_CLASSICO
    | {"nota", "notas"}
    | {
        palavra
        for expressao in EXPRESSOES_DE_QUALIDADE_GERAL
        for palavra in expressao.split()
    }
)

# Nota mínima (de 0 a 100) para cada tipo de pedido.
NOTA_MINIMA = {"critica": 90, "publico": 80, "geral": 80, "classico": 80}


DISTANCIA_MAXIMA_QUALIDADE = 3


def palavras_proximas(palavras, grupo_a, grupo_b):
    """
    True se uma palavra do grupo_a e uma do grupo_b estão a até
    DISTANCIA_MAXIMA_QUALIDADE palavras uma da outra.

    "que as pessoas amaram"                     -> True  (distância 1)
    "pessoas que buscam uma vida melhor"        -> False (distância 5)
    """
    posicoes_a = [posicao for posicao, palavra in enumerate(palavras) if palavra in grupo_a]
    posicoes_b = [posicao for posicao, palavra in enumerate(palavras) if palavra in grupo_b]

    for posicao_a in posicoes_a:
        for posicao_b in posicoes_b:
            if abs(posicao_a - posicao_b) <= DISTANCIA_MAXIMA_QUALIDADE:
                return True

    return False


def detectar_qualidade(cliente):
    """
    "que a crítica amou"      -> "critica"
    "que o público adorou"    -> "publico"
    "uma comédia bem avaliada" -> "geral"
    sem pedido de qualidade   -> None
    """
    palavras = extrair_palavras(cliente)

    if palavras_proximas(palavras, PALAVRAS_DE_CRITICA, PALAVRAS_POSITIVAS):
        return "critica"

    if palavras_proximas(palavras, PALAVRAS_DE_PUBLICO, PALAVRAS_POSITIVAS):
        return "publico"

    if set(palavras) & PALAVRAS_DE_CLASSICO:
        return "classico"

    for expressao in EXPRESSOES_DE_QUALIDADE_GERAL:
        if contem_expressao(cliente, expressao):
            return "geral"

    return None


def nota_da_critica(filme):
    rotten = filme.get("rotten_tomatoes")
    if isinstance(rotten, dict) and rotten.get("critica"):
        return rotten["critica"]
    return None


def nota_do_publico(filme):
    """Rotten do público (manual) ou, na falta, IMDb convertido para 0-100."""
    rotten = filme.get("rotten_tomatoes")
    if isinstance(rotten, dict) and rotten.get("publico"):
        return rotten["publico"]
    if filme.get("nota_imdb"):
        return filme["nota_imdb"] * 10
    return None


def nota_geral(filme):
    """Média das notas que existirem, todas em 0-100."""
    notas = []

    if nota_da_critica(filme) is not None:
        notas.append(nota_da_critica(filme))
    if filme.get("nota_imdb"):
        notas.append(filme["nota_imdb"] * 10)
    if filme.get("metacritic"):
        notas.append(filme["metacritic"])

    if len(notas) == 0 and filme.get("nota_tmdb"):
        notas.append(filme["nota_tmdb"] * 10)

    if len(notas) == 0:
        return None

    return sum(notas) / len(notas)


FUNCAO_DE_NOTA = {
    "critica": nota_da_critica,
    "publico": nota_do_publico,
    "geral": nota_geral,
    "classico": nota_geral
}


def filtrar_por_qualidade(candidatos, tipo_qualidade):
    """Mantém só os filmes acima da nota mínima, do melhor para o pior."""
    calcular_nota = FUNCAO_DE_NOTA[tipo_qualidade]
    nota_minima = NOTA_MINIMA[tipo_qualidade]

    aprovados = [
        filme for filme in candidatos
        if calcular_nota(filme) is not None and calcular_nota(filme) >= nota_minima
    ]

    if tipo_qualidade == "classico":
        ano_limite = date.today().year - IDADE_MINIMA_CLASSICO
        aprovados = [filme for filme in aprovados if filme["ano"] <= ano_limite]

    # Empate na nota: o mais conhecido primeiro.
    aprovados.sort(
        key=lambda filme: (calcular_nota(filme), popularidade(filme)),
        reverse=True
    )
    return aprovados


# =========================================================
# FILME OU SÉRIE?
# =========================================================
TIPO_FILME = "filme"
TIPO_SERIE = "serie"

PALAVRAS_DE_SERIE = {"serie", "series", "seriado", "seriados"}
PALAVRAS_DE_FILME = {"filme", "filmes", "longa", "longas"}
# Palavras de série que não podem virar "assunto" da busca semântica
PALAVRAS_DO_MUNDO_DAS_SERIES = PALAVRAS_DE_SERIE | {
    "temporada", "temporadas", "episodio", "episodios"
}


def tipo_do_item(filme):
    """Itens antigos do catálogo não têm "tipo": são filmes."""
    return filme.get("tipo") or TIPO_FILME


def eh_serie(filme):
    return tipo_do_item(filme) == TIPO_SERIE


def detectar_tipo(cliente):
    """
    "Quero uma série de comédia"   -> "serie"
    "Quero um filme do Nolan"      -> "filme"
    "Filme ou série, tanto faz"    -> None (os dois)
    "Me recomenda algo"            -> None (os dois)
    """
    palavras = set(extrair_palavras(cliente))
    quer_serie = bool(palavras & PALAVRAS_DE_SERIE)
    quer_filme = bool(palavras & PALAVRAS_DE_FILME)

    if quer_serie and not quer_filme:
        return TIPO_SERIE
    if quer_filme and not quer_serie:
        return TIPO_FILME
    return None


EXPRESSOES_DOS_DOIS_TIPOS = ["tanto faz se", "filme ou serie", "serie ou filme", "qualquer tipo"]


def pede_os_dois_tipos(cliente):
    """'Filme ou série', 'tanto faz se é filme ou série' -> True."""
    palavras = set(extrair_palavras(cliente))
    if palavras & PALAVRAS_DE_SERIE and palavras & PALAVRAS_DE_FILME:
        return True
    return any(contem_expressao(cliente, expressao) for expressao in EXPRESSOES_DOS_DOIS_TIPOS)


def filtrar_por_tipo(lista, tipo):
    if tipo is None:
        return list(lista)
    return [filme for filme in lista if tipo_do_item(filme) == tipo]


def periodo_de_exibicao(filme):
    """Filme: "2014". Série: "2008–2013" (acabou) ou "2016–" (ainda em exibição)."""
    if not eh_serie(filme):
        return str(filme.get("ano", ""))

    ano_final = filme.get("ano_final")
    if ano_final is None:
        return f'{filme["ano"]}–'
    if ano_final == filme["ano"]:
        return str(ano_final)
    return f'{filme["ano"]}–{ano_final}'


def tempo_total_em_minutos(filme):
    """Filme: a duração. Série: episódios × duração do episódio (para "Mais curtos")."""
    duracao = filme.get("duracao_minutos")
    if not duracao:
        return None
    if eh_serie(filme):
        return duracao * (filme.get("episodios") or 1)
    return duracao


def resumo_das_temporadas(serie):
    """"5 temporadas • 62 episódios • Finalizada"."""
    partes = []
    temporadas = serie.get("temporadas")
    episodios = serie.get("episodios")
    if temporadas:
        partes.append(f'{temporadas} temporada{"s" if temporadas != 1 else ""}')
    if episodios:
        partes.append(f'{episodios} episódio{"s" if episodios != 1 else ""}')
    if serie.get("status"):
        partes.append(serie["status"])
    return " • ".join(partes)


# =========================================================
# FILTROS EXATOS
# =========================================================
def popularidade(filme):
    """Mais votos no TMDB = mais conhecido. Filmes sem nota vão para o fim."""
    return filme.get("votos_tmdb", 0)


def filtrar_filmes(cliente):
    """
    Aplica os filtros encontrados na mensagem.
    Retorna a lista (do mais popular ao menos popular) ou None se não houver filtro.
    """
    diretor, ator = detectar_diretor_e_ator(cliente)
    ano = detectar_ano(cliente)
    decada = detectar_decada(cliente)
    genero = detectar_genero(cliente)
    qualidade = detectar_qualidade(cliente)
    tipo = detectar_tipo(cliente)

    if (
        diretor is None and ator is None and ano is None and decada is None
        and genero is None and qualidade is None
    ):
        texto_tipo = f" • só {'séries' if tipo == TIPO_SERIE else 'filmes'}" if tipo else ""
        rastro.etapa(
            "🧩", "Filtros exatos",
            f"nenhum filtro na mensagem (gênero, ano, ator, diretor, qualidade){texto_tipo}"
        )
        return None

    candidatos = filtrar_por_tipo(filmes, tipo)

    if diretor is not None:
        candidatos = [
            filme for filme in candidatos
            if filme_tem_pessoa(filme["diretor"].split(","), diretor)
        ]

    if ator is not None:
        candidatos = [
            filme for filme in candidatos
            if filme_tem_pessoa(filme.get("elenco", []), ator)
        ]

    if ano is not None:
        candidatos = [filme for filme in candidatos if filme["ano"] == ano]

    if decada is not None:
        candidatos = [filme for filme in candidatos if decada[0] <= filme["ano"] <= decada[1]]

    if genero is not None:
        candidatos = [
            filme for filme in candidatos
            if filme_tem_genero(filme, genero)
        ]

    # Com pedido de qualidade: os mais bem avaliados primeiro.
    if qualidade is not None:
        candidatos = filtrar_por_qualidade(candidatos, qualidade)
        ordem = "da maior nota para a menor"
    else:
        # Sem pedido de qualidade: os mais populares primeiro.
        candidatos.sort(key=popularidade, reverse=True)
        ordem = "do mais popular (votos no TMDB) ao menos popular"

    filtros_usados = [
        texto for texto in [
            f"tipo = {tipo}" if tipo else None,
            f"gênero = {genero}" if genero else None,
            f"diretor = {diretor}" if diretor else None,
            f"ator = {ator}" if ator else None,
            f"ano = {ano}" if ano else None,
            f"anos {decada[0]}–{decada[1]}" if decada else None,
            f"qualidade = {qualidade}" if qualidade else None,
        ] if texto
    ]
    rastro.etapa(
        "🧩", "Filtros exatos",
        f"{' • '.join(filtros_usados)}\n{len(candidatos)} filmes passaram, ordenados {ordem}"
    )
    return candidatos


# =========================================================
# BUSCA HÍBRIDA (significado + palavras em comum)
# =========================================================
PALAVRAS_IGNORADAS_NA_BUSCA = {
    "filme", "filmes", "sobre", "quero", "queria", "gostaria", "para",
    "como", "onde", "quem", "qual", "quais", "uma", "umas", "uns", "que",
    "pela", "pelo", "pelos", "pelas", "muito", "muita", "mais", "algum",
    "alguma", "historia", "tipo", "tenha", "onde", "seja", "sobre", "esta",
    "esse", "essa", "isso", "dele", "dela", "deles", "delas", "entre",
    "serie", "series", "seriado", "seriados", "temporada", "temporadas",
    "episodio", "episodios"
}


def raiz_da_palavra(palavra):
    """Aproximação simples de radical: 'resgata' e 'resgatarem' -> 'resga'."""
    return palavra[:5]


def raizes_importantes(texto):
    return {
        raiz_da_palavra(palavra)
        for palavra in extrair_palavras(texto)
        if len(palavra) >= 4 and palavra not in PALAVRAS_IGNORADAS_NA_BUSCA
    }


for filme in filmes:
    filme["raizes_texto"] = raizes_importantes(
        filme["nome"] + " " + filme["sinopse"]
    )


def ranquear_por_busca(busca, candidatos, filmes_excluidos=None):
    """
    Devolve [(pontuacao, filme), ...] do melhor para o pior.

    pontuacao = similaridade de significado (0 a 1)
              + bônus pela fração das palavras da busca presentes na sinopse
    """
    vetor_busca = normalizar_vetor(modelo.encode(busca))
    raizes_busca = raizes_importantes(busca)

    # Compara pela chave (id do TMDB), que é mais rápido e seguro
    # do que comparar os dicionários inteiros.
    chaves_excluidas = set()
    if filmes_excluidos:
        chaves_excluidas = {usuario.chave_filme(filme) for filme in filmes_excluidos}

    resultados = []

    for filme in candidatos:
        if usuario.chave_filme(filme) in chaves_excluidas:
            continue

        similaridade = float(np.dot(vetor_busca, filme["vetor_sinopse"]))

        bonus = 0.0
        if len(raizes_busca) > 0:
            raizes_em_comum = raizes_busca & filme["raizes_texto"]
            bonus = PESO_BONUS_PALAVRAS * len(raizes_em_comum) / len(raizes_busca)

        resultados.append((similaridade + bonus, filme, similaridade, bonus))

    resultados.sort(key=lambda resultado: resultado[0], reverse=True)

    maior = resultados[0][0] if resultados and resultados[0][0] > 0 else 1.0
    rastro.tabela(
        "📊", "Busca semântica (embeddings)",
        ["significado", "palavras", "total"],
        [
            (filme["nome"], [f"{sim:.3f}", f"+{bonus:.3f}", f"{total:.3f}"], max(total, 0) / maior)
            for total, filme, sim, bonus in resultados
        ],
        detalhe=(
            f'busca: "{busca}" • {len(resultados)} filmes comparados\n'
            f"total = cosseno(busca, sinopse) + {PESO_BONUS_PALAVRAS} × fração de palavras em comum"
        )
    )

    return [(total, filme) for total, filme, _, _ in resultados]


def buscar_filme_semantico(busca, candidatos=None, filmes_excluidos=None, tipo=None):
    """
    Sem candidatos: procura no catálogo todo (só filmes ou só séries, se
    o pedido disser) e exige pontuação mínima.
    Com candidatos (já filtrados): devolve o melhor entre eles.
    """
    filmes_para_buscar = filtrar_por_tipo(filmes, tipo) if candidatos is None else candidatos
    resultados = ranquear_por_busca(busca, filmes_para_buscar, filmes_excluidos)

    if len(resultados) == 0:
        return None

    melhor_pontuacao, melhor_filme = resultados[0]

    if candidatos is not None or melhor_pontuacao >= LIMITE_SIMILARIDADE:
        if candidatos is None:
            rastro.etapa(
                "🎯", "Limite de similaridade",
                f"{melhor_pontuacao:.3f} ≥ {LIMITE_SIMILARIDADE}: aceito {melhor_filme['nome']}"
            )
        return melhor_filme

    rastro.etapa(
        "🚫", "Limite de similaridade",
        f"melhor pontuação {melhor_pontuacao:.3f} < {LIMITE_SIMILARIDADE}: nenhum filme é parecido o bastante"
    )
    return None


# =========================================================
# GERAR TEXTO DA RECOMENDAÇÃO
# =========================================================
def formatar_nota(valor):
    """8.0 -> '8' | 8.5 -> '8,5' (vírgula, como no Brasil)."""
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    return str(valor).replace(".", ",")


def linhas_de_avaliacao(filme):
    """
    Monta as notas que existirem para o filme, por exemplo:
      ['🍅 Rotten Tomatoes: 88% (crítica) | 90% (público)',
       '⭐ IMDb: 7,9/10', 'Ⓜ️ Metacritic: 84/100', '🎬 TMDB: 7,7/10']
    """
    linhas = []

    rotten = filme.get("rotten_tomatoes")
    if isinstance(rotten, dict):
        partes_rotten = []
        if rotten.get("critica"):
            partes_rotten.append(f'{rotten["critica"]}% (crítica)')
        if rotten.get("publico"):
            partes_rotten.append(f'{rotten["publico"]}% (público)')
        if partes_rotten:
            linhas.append("🍅 Rotten Tomatoes: " + " | ".join(partes_rotten))

    if filme.get("nota_imdb"):
        linhas.append(f'⭐ IMDb: {formatar_nota(filme["nota_imdb"])}/10')

    if filme.get("metacritic"):
        linhas.append(f'Ⓜ️ Metacritic: {filme["metacritic"]}/100')

    if filme.get("nota_tmdb"):
        linhas.append(f'🎬 TMDB: {formatar_nota(round(filme["nota_tmdb"], 1))}/10')

    return linhas


def escolher_nota_para_exibir(filme, qualidade=None):
    """
    Na recomendação mostramos só uma nota, a que combina com o pedido:
      "o público adorou" -> nota do público (ou IMDb)
      outros pedidos     -> a primeira disponível (Rotten Tomatoes, se houver)
    """
    notas = linhas_de_avaliacao(filme)

    if len(notas) == 0:
        return None

    if qualidade == "publico":
        rotten = filme.get("rotten_tomatoes")
        tem_publico_rotten = isinstance(rotten, dict) and rotten.get("publico")

        if not tem_publico_rotten:
            for linha in notas:
                if linha.startswith("⭐ IMDb"):
                    return linha

    return notas[0]


def gerar_resposta(melhor_filme, qualidade=None):
    if eh_serie(melhor_filme):
        informacoes = (
            f'{melhor_filme["nome"]} ({periodo_de_exibicao(melhor_filme)}) '
            f'é uma série de {melhor_filme["genero"]}, '
            f'criada por {melhor_filme["diretor"]}.'
        )
        resumo = resumo_das_temporadas(melhor_filme)
        if resumo:
            informacoes += f"\n📺 {resumo}"
    else:
        informacoes = (
            f'{melhor_filme["nome"]} ({melhor_filme["ano"]}) '
            f'é um filme de {melhor_filme["genero"]}, '
            f'dirigido por {melhor_filme["diretor"]}.'
        )

    texto = f'{informacoes}\n\n{melhor_filme["sinopse"]}'

    # Na recomendação, mostra só a nota principal (para não poluir o chat).
    nota = escolher_nota_para_exibir(melhor_filme, qualidade)
    if nota:
        texto += f"\n\n{nota}"

    return texto


# =========================================================
# SAUDAÇÃO
# =========================================================
PALAVRAS_SAUDACAO = {
    "oi", "oie", "ola", "opa", "eai", "e", "ai", "hey", "hello", "hi",
    "bom", "boa", "dia", "tarde", "noite", "tudo", "bem", "beleza",
    "cineai", "salve"
}


def eh_saudacao(cliente):
    palavras = extrair_palavras(cliente)
    return len(palavras) > 0 and all(palavra in PALAVRAS_SAUDACAO for palavra in palavras)


# =========================================================
# IDENTIFICAR INTENÇÃO
# =========================================================
# Se a mensagem tem uma destas, a pessoa está PEDINDO um filme.
PALAVRAS_DE_PEDIDO = {
    "quero", "queria", "gostaria", "recomenda", "recomende", "recomendar",
    "indica", "indique", "indicar", "sugere", "sugira", "sugerir",
    "mostra", "mostre", "procuro", "busco", "assistir"
}

# Se a mensagem fala "ele/ela/esse filme", está falando do filme atual.
# ("esta" ficou de fora: sem acento ele se confunde com o verbo "está".)
PALAVRAS_SOBRE_FILME_ATUAL = {
    "ele", "ela", "dele", "dela", "nele", "nela",
    "esse", "essa", "desse", "dessa", "nesse", "nessa",
    "este", "deste", "desta", "isso"
}

# "Tem ALGUM filme com...?" é busca, mesmo sem "quero".
PALAVRAS_DE_BUSCA_GENERICA = {"algum", "alguma", "algo", "alguns", "algumas"}

# Assuntos que responder_sobre_filme() sabe responder direto.
PALAVRAS_DE_DETALHE = {
    "diretor", "diretora", "dirigiu", "dirigido", "direcao",
    "elenco", "ator", "atores", "atriz", "atrizes", "protagonista",
    "ano", "lancado", "lancamento", "genero", "generos",
    "premio", "premios", "indicacao", "indicacoes",
    "rotten", "tomatoes", "imdb", "metacritic", "sinopse",
    "nota", "notas", "avaliacao", "avaliacoes",
    # séries
    "temporada", "temporadas", "episodio", "episodios", "criou", "criador",
    "criadora", "acabou", "terminou", "cancelada", "cancelaram", "renovada",
    "status", "estreou", "dura", "duracao"
}


def classificar_por_regras(cliente):
    """
    Regras rápidas e confiáveis, antes de chamar a IA.
    Devolve "PERGUNTA", "BUSCA" ou None (quando as regras não sabem dizer).
    """
    palavras = set(extrair_palavras(cliente))

    if palavras & PALAVRAS_DE_PEDIDO:
        return "BUSCA"

    if palavras & PALAVRAS_SOBRE_FILME_ATUAL:
        return "PERGUNTA"

    if palavras & PALAVRAS_DE_BUSCA_GENERICA:
        return "BUSCA"

    if palavras & PALAVRAS_DE_DETALHE:
        return "PERGUNTA"

    return None


def eh_pergunta_com_palavras_do_filme(cliente, filme_da_conversa):
    """
    "Qual é o plano do ogro?" com Shrek na conversa: é pergunta e usa uma
    palavra da sinopse ("ogro"). Então é sobre o filme, sem precisar da IA.
    """
    if filme_da_conversa is None:
        return False

    texto_normalizado = " ".join(extrair_palavras(cliente))
    eh_pergunta = "?" in cliente or texto_normalizado.startswith(INICIOS_DE_PERGUNTA)

    return eh_pergunta and bool(
        raizes_importantes(cliente) & filme_da_conversa["raizes_texto"]
    )


def identificar_intencao(cliente, filme_da_conversa=None):
    intencao_por_regra = classificar_por_regras(cliente)
    if intencao_por_regra is not None:
        rastro.etapa("🧭", "Intenção", f"{intencao_por_regra} (decidido pelas regras, sem IA)")
        return intencao_por_regra

    if eh_pergunta_com_palavras_do_filme(cliente, filme_da_conversa):
        rastro.etapa("🧭", "Intenção", "PERGUNTA (usa palavras da sinopse do filme atual)")
        return "PERGUNTA"

    prompt = f"""
    Classifique a mensagem em apenas uma categoria:

    BUSCA = usuário quer encontrar ou receber uma recomendação de filme.

    PERGUNTA = usuário está perguntando alguma coisa sobre o filme
    que já está sendo discutido.

    FORA = a mensagem não tem nada a ver com filmes
    (perguntas gerais, contas, notícias, tarefas).

    Exemplos:

    "Quero uma comédia" = BUSCA
    "Quero um filme de 2014" = BUSCA
    "Quero um filme com Anne Hathaway" = BUSCA
    "Tem algum filme sobre astronautas?" = BUSCA

    "Quem dirigiu ele?" = PERGUNTA
    "De que ano ele é?" = PERGUNTA
    "Ele é humano?" = PERGUNTA
    "Como termina?" = PERGUNTA
    "Me fale mais sobre esse filme" = PERGUNTA

    "Qual é a capital do Japão?" = FORA
    "Quanto é 15 vezes 3?" = FORA
    "Me ajuda com meu trabalho de física" = FORA

    Mensagem:
    {cliente}

    Responda somente:
    BUSCA
    ou
    PERGUNTA
    ou
    FORA
    """

    resposta = perguntar_ao_modelo(prompt).upper()

    if "FORA" in resposta:
        intencao = "FORA"
    elif "PERGUNTA" in resposta:
        intencao = "PERGUNTA"
    else:
        intencao = "BUSCA"

    rastro.etapa("🧭", "Intenção", f"{intencao} (decidido pela IA)")
    return intencao


# =========================================================
# EXTRAIR BUSCA SEMÂNTICA
# =========================================================
PALAVRAS_DE_LIGACAO_NO_INICIO = {"de", "da", "do", "das", "dos", "sobre", "um", "uma", "com", "e"}


def limpar_tipo_do_assunto(busca):
    """
    "serie de investigação policial" -> "investigação policial"
    (a IA às vezes devolve "série"/"filme" junto do assunto).
    """
    palavras = [
        palavra for palavra in busca.split()
        if " ".join(extrair_palavras(palavra)) not in (PALAVRAS_DE_SERIE | PALAVRAS_DE_FILME)
    ]
    while palavras and " ".join(extrair_palavras(palavras[0])) in PALAVRAS_DE_LIGACAO_NO_INICIO:
        palavras.pop(0)
    return " ".join(palavras)


def extrair_busca_semantica(cliente):
    prompt = f"""
    Extraia apenas o assunto, tema ou característica narrativa
    que deve ser usada para procurar um filme pela sinopse.

    Remova informações estruturadas como:
    - gênero
    - ano
    - nome de ator
    - nome de diretor
    - opinião ou nota (bem avaliado, a crítica amou, clássico)
    - se é filme ou série

    Não invente informações.
    Não explique sua resposta.

    Se não existir assunto, tema ou característica narrativa,
    responda somente NENHUMA.

    Exemplos:

    Mensagem: Quero uma comédia sobre o mundo da moda
    Resposta: mundo da moda

    Mensagem: Quero uma ficção científica sobre astronautas procurando outro planeta
    Resposta: astronautas procurando outro planeta

    Mensagem: Quero uma animação de 2001 com Eddie Murphy
    Resposta: NENHUMA

    Mensagem: Quero um filme de 1993 sobre dinossauros
    Resposta: dinossauros

    Mensagem: Quero uma comédia que a crítica amou
    Resposta: NENHUMA

    Mensagem: Quero um filme bem avaliado sobre viagem no tempo
    Resposta: viagem no tempo

    Mensagem: Quero uma série sobre um professor que vira traficante
    Resposta: professor que vira traficante

    Mensagem:
    {cliente}

    Resposta:
    """

    busca = perguntar_ao_modelo(prompt)

    # Às vezes o modelo repete o rótulo: "Resposta: dinossauros"
    busca = re.sub(r"^\s*resposta\s*:\s*", "", busca, flags=re.IGNORECASE)
    busca = busca.strip().strip('"').strip("'").rstrip(".").strip()
    busca = limpar_tipo_do_assunto(busca)

    busca_normalizada = " ".join(extrair_palavras(busca))

    if busca_normalizada == "" or "nenhuma" in busca_normalizada.split():
        return "NENHUMA"

    # Se o que sobrou são só pedaços dos filtros ("DiCaprio", "1999",
    # "comédia"), não existe assunto de verdade.
    diretor, ator = detectar_diretor_e_ator(cliente)
    filtros_encontrados = [
        detectar_genero(cliente),
        ator,
        diretor,
        detectar_ano(cliente)
    ]

    palavras_dos_filtros = {"anos", "decada"}
    for filtro in filtros_encontrados + list(detectar_decada(cliente) or []):
        if filtro is not None:
            palavras_dos_filtros.update(extrair_palavras(str(filtro)))

    palavras_de_assunto = [
        palavra
        for palavra in busca_normalizada.split()
        if palavra not in palavras_dos_filtros
        and palavra not in PALAVRAS_IGNORADAS_NA_BUSCA
        and palavra not in SINONIMOS_GENERO
        and palavra not in PALAVRAS_DE_QUALIDADE
        and palavra not in PALAVRAS_DE_PERSONALIZACAO
        and len(palavra) >= 3
    ]

    if len(palavras_de_assunto) == 0:
        rastro.etapa("🔎", "Assunto da busca", f'"{busca}" era só pedaço dos filtros: sem assunto')
        return "NENHUMA"

    rastro.etapa("🔎", "Assunto da busca", f'"{busca}"')
    return busca


# =========================================================
# FILMES JÁ ASSISTIDOS
# =========================================================
# O CineAI não recomenda o que você já viu... a não ser que você
# cite o filme pelo nome ("quero rever Shrek").
TAMANHO_MINIMO_TITULO = 5  # letras; evita que "Up" ou "Ela" casem com qualquer frase


def titulos_para_busca(filme):
    """
    "Toy Story: Um Mundo de Aventuras" -> {"toy story um mundo de aventuras", "toy story"}
    Inclui o título original e a parte antes de ":" ou " - ".
    """
    titulos = set()

    for titulo in (filme.get("nome", ""), filme.get("titulo_original", "")):
        if not titulo:
            continue

        titulos.add(" ".join(extrair_palavras(titulo)))

        titulo_curto = re.split(r":| - ", titulo)[0]
        titulos.add(" ".join(extrair_palavras(titulo_curto)))

    return {
        titulo for titulo in titulos
        if len(titulo.replace(" ", "")) >= TAMANHO_MINIMO_TITULO
    }


TAMANHO_MINIMO_TITULO_CURTO = 3  # "Dark", "Lost", "Her" (só com maiúscula, ver abaixo)


def titulos_curtos(filme):
    """
    Títulos de 3 ou 4 letras ("Dark", "Lost"). Eles só contam quando você
    escreve com a primeira letra maiúscula no meio da frase
    ("parecido com Dark"), para "dark" ou "lost" comuns não virarem filme.
    """
    curtos = set()
    for titulo in (filme.get("nome", ""), filme.get("titulo_original", "")):
        titulo = (titulo or "").strip()
        letras = titulo.replace(" ", "")
        if (
            TAMANHO_MINIMO_TITULO_CURTO <= len(letras) < TAMANHO_MINIMO_TITULO
            and titulo[:1].isupper()
        ):
            curtos.add(titulo)
    return curtos


def posicao_titulo_curto(cliente, titulo):
    """Posição do título curto escrito com maiúscula (não no começo da frase), ou None."""
    for encontrado in re.finditer(rf"\b{re.escape(titulo)}\b", cliente):
        if encontrado.start() > 0:
            return encontrado
    return None


for filme in filmes:
    filme["titulos_busca"] = titulos_para_busca(filme)
    filme["titulos_curtos"] = titulos_curtos(filme)


def filme_citado_pelo_nome(filme, cliente):
    if any(
        contem_expressao(cliente, titulo)
        for titulo in filme.get("titulos_busca", set())
    ):
        return True
    return any(
        posicao_titulo_curto(cliente, titulo) is not None
        for titulo in filme.get("titulos_curtos", set())
    )


def deve_pular(filme, cliente, chaves_assistidas):
    """Já assistido e não citado pelo nome na mensagem."""
    return (
        usuario.chave_filme(filme) in chaves_assistidas
        and not filme_citado_pelo_nome(filme, cliente)
    )


ultimos_assistidos_pulados = []  # para o aviso "você já assistiu a O Mentalista"


def remover_assistidos(lista_filmes, cliente):
    """Devolve (filmes_restantes, quantidade_pulada)."""
    chaves_assistidas = usuario.chaves_assistidas()

    if len(chaves_assistidas) == 0:
        return lista_filmes, 0

    restantes = [
        filme for filme in lista_filmes
        if not deve_pular(filme, cliente, chaves_assistidas)
    ]
    quantidade_pulada = len(lista_filmes) - len(restantes)
    chaves_restantes = {usuario.chave_filme(filme) for filme in restantes}
    ultimos_assistidos_pulados[:] = [
        filme for filme in lista_filmes if usuario.chave_filme(filme) not in chaves_restantes
    ]
    if quantidade_pulada:
        rastro.etapa("👁", "Já assistidos", f"{quantidade_pulada} filmes pulados • sobraram {len(restantes)}")
    return restantes, quantidade_pulada


def assistidos_para_excluir(cliente):
    """Lista de filmes assistidos que NÃO foram citados pelo nome."""
    chaves_assistidas = usuario.chaves_assistidas()

    if len(chaves_assistidas) == 0:
        return []

    return [
        filme for filme in filmes
        if deve_pular(filme, cliente, chaves_assistidas)
    ]


# =========================================================
# BUSCAR FILME
# =========================================================
# =========================================================
# PEDIDO PERSONALIZADO ("Me recomenda algo", "um filme pra mim")
# =========================================================
EXPRESSOES_PERSONALIZADAS = [
    "pra mim", "para mim", "meu gosto", "meu estilo", "meu perfil",
    "meus favoritos", "eu vou gostar", "eu vou curtir", "eu goste", "eu curta",
    "me surpreenda", "me surpreende", "deveria assistir", "deveria ver",
    "devo assistir", "devo ver", "o que assistir", "o que ver",
    "combine comigo", "combina comigo", "a minha cara", "minha cara",
    "escolhe por mim", "escolha por mim", "sorteia", "sortear", "sorteie",
    "aleatorio", "aleatoria", "tanto faz", "qualquer um"
]

# Palavras de personalização: nunca viram "assunto" da busca.
PALAVRAS_DE_PERSONALIZACAO = {
    "mim", "gosto", "estilo", "perfil", "favoritos", "parecido", "parecidos",
    "surpreenda", "surpreende", "combine", "combina", "comigo", "deveria",
    "devo", "cara", "goste", "curta", "gostar", "curtir",
    "sorteia", "sortear", "sorteie", "aleatorio", "aleatoria", "surpresa", "surpreender"
}

# Palavras que sozinhas não dizem o que buscar ("Quero um filme bom pra hoje").
PALAVRAS_GENERICAS_DE_PEDIDO = {
    "para", "pra", "mim", "eu", "hoje", "agora", "noite", "bom", "boa", "bons",
    "legal", "legais", "interessante", "dica", "dicas", "sugestao", "recomendacao",
    "assistir", "ver", "quero", "algo", "alguma", "coisa", "novo", "nova",
    "serie", "series", "seriado", "seriados", "maratonar", "maratona"
}


def eh_pedido_personalizado(cliente):
    """
    True para pedidos sem critério ("Me recomenda algo", "Quero um filme")
    ou que pedem explicitamente o seu gosto ("uma comédia pra mim").
    """
    for expressao in EXPRESSOES_PERSONALIZADAS:
        if contem_expressao(cliente, expressao):
            return True

    palavras = extrair_palavras(cliente)
    palavras_com_conteudo = [
        palavra for palavra in palavras
        if palavra not in PALAVRAS_DE_PREENCHIMENTO
        and palavra not in PALAVRAS_GENERICAS_DE_PEDIDO
    ]

    return len(palavras) > 0 and len(palavras_com_conteudo) == 0


# ---------------- Surpreenda-me ----------------
EXPRESSOES_SURPRESA = [
    "surpreenda", "surpreende", "me surpreenda", "sorteia", "sortear", "sorteie",
    "aleatorio", "aleatoria", "qualquer um", "tanto faz", "escolhe por mim", "escolha por mim"
]
QUANTIDADE_SORTEIO = 12  # sorteia entre os 12 que mais combinam com você


def eh_pedido_surpresa(cliente):
    return any(contem_expressao(cliente, expressao) for expressao in EXPRESSOES_SURPRESA)


def sortear_entre_os_melhores(ordenados):
    """
    Põe na frente um filme sorteado entre os melhores; o resto mantém a ordem.
    Evita repetir um filme que já apareceu nesta conversa.
    """
    if len(ordenados) <= 1:
        return ordenados

    ja_recomendados = {usuario.chave_filme(filme) for filme in historico_recomendacoes}
    novos = [filme for filme in ordenados if usuario.chave_filme(filme) not in ja_recomendados]
    sorteaveis = (novos or ordenados)[:QUANTIDADE_SORTEIO]

    escolhido = random.choice(sorteaveis)
    return [escolhido] + [filme for filme in ordenados if filme is not escolhido]


def registrar_ranking_do_perfil(ordenados, perfil_atual, titulo="Ranking pelo seu perfil"):
    """Mostra no Painel do RAG as partes da pontuação dos 5 primeiros."""
    linhas = []
    for filme in ordenados[:5]:
        pontuacao, partes = perfil.pontuar_filme(filme, perfil_atual)
        linhas.append((
            filme["nome"],
            [f"{partes['generos']:+.2f}", f"{partes['gosto']:+.2f}", f"{pontuacao:.3f}"],
            max(pontuacao, 0)
        ))

    maior = max((linha[2] for linha in linhas), default=1) or 1
    linhas = [(nome, valores, barra / maior) for nome, valores, barra in linhas]

    rastro.tabela(
        "👤", titulo, ["gêneros", "sinopse", "total"], linhas,
        detalhe=(
            f"{len(ordenados)} candidatos • total = {perfil.PESO_GENEROS}×gêneros "
            f"+ {perfil.PESO_GOSTO}×sinopses que você curtiu + diretores, atores, "
            "popularidade e notas"
        )
    )


def ordenar_sem_perfil(candidatos):
    """Quando ainda não conhecemos você: populares e bem avaliados primeiro."""
    return sorted(
        candidatos,
        key=lambda filme: (
            perfil.popularidade_normalizada(filme)
            + 0.5 * perfil.qualidade_normalizada(filme)
        ),
        reverse=True
    )


def buscar_filme(cliente, perfil_atual=None, pedido_personalizado=False):
    """
    Retorna (melhor_filme, candidatos_ou_None, quantidade_assistidos_pulados, usou_perfil).
    """
    global ultima_busca_semantica
    ultima_busca_semantica = None

    candidatos = filtrar_filmes(cliente)
    tipo_pedido = detectar_tipo(cliente)
    perfil_valido = perfil_atual is not None and perfil_atual["suficiente"]

    # ---------- Pedido personalizado: o seu gosto decide ----------
    if pedido_personalizado:
        base = candidatos if candidatos is not None else filtrar_por_tipo(filmes, tipo_pedido)
        base, quantidade_pulada = remover_assistidos(base, cliente)

        if len(base) == 0:
            return None, base, quantidade_pulada, False

        if perfil_valido:
            ordenados = perfil.ordenar_por_afinidade(base, perfil_atual)
            registrar_ranking_do_perfil(ordenados, perfil_atual)
        elif candidatos is not None:
            ordenados = base  # já vem na ordem dos filtros (popularidade/qualidade)
        else:
            ordenados = ordenar_sem_perfil(base)

        if eh_pedido_surpresa(cliente):
            ordenados = sortear_entre_os_melhores(ordenados)
            rastro.etapa(
                "🎲", "Sorteio",
                f"sorteado entre os {QUANTIDADE_SORTEIO} primeiros: {ordenados[0]['nome']}"
            )

        return ordenados[0], ordenados, quantidade_pulada, perfil_valido

    busca_semantica = extrair_busca_semantica(cliente)
    tem_assunto = busca_semantica != "NENHUMA"
    ultima_busca_semantica = busca_semantica if tem_assunto else None

    # ---------- Existem filtros ----------
    if candidatos is not None:

        candidatos, quantidade_pulada = remover_assistidos(candidatos, cliente)

        if len(candidatos) == 0:
            return None, candidatos, quantidade_pulada, False

        if len(candidatos) == 1:
            return candidatos[0], candidatos, quantidade_pulada, False

        if not tem_assunto:
            # Pedido de qualidade ("bem avaliado") já vem ordenado pela nota.
            # Nos outros casos, a popularidade manda, com desempate pelo seu gosto.
            if perfil_valido and detectar_qualidade(cliente) is None:
                candidatos = perfil.ordenar_com_desempate(candidatos, perfil_atual)
                return candidatos[0], candidatos, quantidade_pulada, True

            return candidatos[0], candidatos, quantidade_pulada, False

        # Filtros + assunto: reordena os candidatos pelo assunto,
        # para o "Quero outro" seguir essa mesma ordem.
        candidatos_ordenados = [
            filme for _, filme in ranquear_por_busca(busca_semantica, candidatos)
        ]
        return candidatos_ordenados[0], candidatos_ordenados, quantidade_pulada, False

    # ---------- Busca somente pelo assunto ----------
    if not tem_assunto:
        return None, None, 0, False

    filmes_pulados = assistidos_para_excluir(cliente)
    melhor_filme = buscar_filme_semantico(
        busca_semantica,
        filmes_excluidos=filmes_pulados,
        tipo=tipo_pedido
    )

    # Não achou nada novo: confere se era porque você já tinha visto o melhor.
    if melhor_filme is None and filmes_pulados:
        filme_ja_visto = buscar_filme_semantico(busca_semantica, tipo=tipo_pedido)
        if filme_ja_visto is not None:
            ultimos_assistidos_pulados[:] = [filme_ja_visto]
            return None, None, 1, False

    return melhor_filme, None, 0, False


# =========================================================
# PEDIDO DE OUTRO
# =========================================================
# Palavras que indicam pedido de outra opção.
PALAVRAS_DE_OUTRO = {
    "outro", "outra", "outros", "outras",
    "diferente", "diferentes",
    "proximo", "proxima"
}

# Palavras que podem aparecer junto do pedido sem trazer assunto novo.
PALAVRAS_DE_PREENCHIMENTO = {
    # pedido
    "quero", "queria", "gostaria", "pode", "poderia", "me", "mim",
    "mostra", "mostre", "mostrar", "manda", "mande", "mandar",
    "sugere", "sugira", "sugerir", "recomenda", "recomende", "recomendar",
    "indica", "indique", "indicar", "tem", "teria", "ver", "assistir",
    # artigos e ligações
    "um", "uma", "uns", "umas", "o", "a", "os", "as", "e", "de", "da", "do",
    "algum", "alguma", "qualquer", "entao", "agora", "ai", "ja",
    # objeto do pedido
    "filme", "filmes", "opcao", "opcoes", "sugestao", "sugestoes",
    "recomendacao", "recomendacoes", "indicacao", "algo", "coisa",
    # reação ao filme anterior
    "nao", "gostei", "curti", "esse", "este", "isso", "desse", "deste",
    "ok", "beleza", "sim", "vi", "assisti",
    # cortesia
    "por", "favor", "pfv", "pf", "obrigado", "obrigada", "voce", "vc"
}


def eh_pedido_de_outro_filme(cliente):
    """
    Só é pedido de outro quando a mensagem tem "outro/outra/diferente"
    como palavra inteira E não traz nenhum assunto novo.

    "Quero outro"                         -> True
    "Não gostei desse, quero outro"       -> True
    "Filme sobre astronautas procurando
     outro planeta"                       -> False (é uma busca nova)
    """
    tem_palavra_de_outro = False
    palavras_de_conteudo = []

    for palavra in extrair_palavras(cliente):
        if palavra in PALAVRAS_DE_OUTRO:
            tem_palavra_de_outro = True
        elif palavra not in PALAVRAS_DE_PREENCHIMENTO:
            palavras_de_conteudo.append(palavra)

    return tem_palavra_de_outro and len(palavras_de_conteudo) == 0


def buscar_outro_filme(candidatos_anteriores, filmes_recomendados, pedido_anterior):
    """
    Próximo da lista de candidatos que ainda não foi recomendado.
    Também pula filmes marcados como assistidos no meio da conversa.
    """
    chaves_recomendadas = {usuario.chave_filme(filme) for filme in filmes_recomendados}
    chaves_assistidas = usuario.chaves_assistidas()

    for filme in candidatos_anteriores:
        if usuario.chave_filme(filme) in chaves_recomendadas:
            continue
        if deve_pular(filme, pedido_anterior, chaves_assistidas):
            continue
        return filme

    return None


def buscar_outro_semantico(pedido_anterior, filmes_recomendados):
    """Próximo filme mais parecido com o pedido, sem repetir e sem os já vistos."""
    busca_semantica = extrair_busca_semantica(pedido_anterior)

    if busca_semantica == "NENHUMA":
        busca_semantica = pedido_anterior

    resultados = ranquear_por_busca(
        busca_semantica,
        filtrar_por_tipo(filmes, detectar_tipo(pedido_anterior)),
        filmes_excluidos=filmes_recomendados + assistidos_para_excluir(pedido_anterior)
    )

    if len(resultados) == 0:
        return None

    melhor_pontuacao, melhor_filme = resultados[0]

    if melhor_pontuacao >= LIMITE_SIMILARIDADE:
        return melhor_filme

    return None


# =========================================================
# PERGUNTAS SOBRE O FILME ATUAL
# =========================================================
def frase_do_status(serie):
    """
    "Ela já acabou?" respondido como gente:
      Em exibição -> "Ainda não acabou: está no ar desde 2013 (10 temporadas até agora)."
      Finalizada  -> "Sim, já acabou: foi exibida de 2008 a 2013 (Finalizada, 5 temporadas)."
      Cancelada   -> "Foi cancelada: ficou no ar de 2015 a 2017 (2 temporadas)."
    """
    nome = serie["nome"]
    status = serie.get("status") or "Não informado"
    temporadas = serie.get("temporadas")
    texto_temporadas = f'{temporadas} temporada{"s" if temporadas != 1 else ""}' if temporadas else ""
    ano_final = serie.get("ano_final")
    periodo = f'de {serie["ano"]} a {ano_final}' if ano_final and ano_final != serie["ano"] else f'em {serie["ano"]}'

    if status in ("Em exibição", "Em produção"):
        extra = f" ({texto_temporadas} até agora)" if texto_temporadas else ""
        return f'Ainda não acabou: {nome} está no ar desde {serie["ano"]}{extra}. Status: {status}.'

    if status == "Cancelada":
        extra = f" ({texto_temporadas})" if texto_temporadas else ""
        return f"{nome} foi cancelada: ficou no ar {periodo}{extra}."

    if status == "Finalizada":
        extra = f", {texto_temporadas}" if texto_temporadas else ""
        return f"Sim, já acabou: {nome} foi exibida {periodo} (Finalizada{extra})."

    return f"Status de {nome}: {status} (exibida em {periodo_de_exibicao(serie)})."


PALAVRAS_DE_STATUS = [
    "acabou", "terminou", "terminada", "finalizada", "finalizou", "encerrada",
    "encerrou", "cancelada", "cancelaram", "cancelou", "renovada", "renovaram",
    "renovou", "status", "exibicao", "continua", "lancando"
]
PALAVRAS_DE_CRIADOR = ["criou", "criador", "criadora", "criadores", "criada", "criado", "showrunner"]
PALAVRAS_DE_DURACAO = ["dura", "duracao", "minutos", "horas", "comprido", "longo", "longa"]


def pessoa_citada_na_lista(cliente, nomes):
    """
    Procura na pergunta alguém de uma lista de nomes, pelo nome completo ou
    pelo sobrenome ("A Robin Tunney está...?", "O Tunney está...?").
    """
    texto = " " + " ".join(extrair_palavras(cliente)) + " "
    for nome in nomes:
        palavras_nome = extrair_palavras(nome)
        if not palavras_nome:
            continue
        if " " + " ".join(palavras_nome) + " " in texto:
            return nome
        sobrenome = palavras_nome[-1]
        if len(palavras_nome) >= 2 and len(sobrenome) >= TAMANHO_MINIMO_SOBRENOME and f" {sobrenome} " in texto:
            return nome
    return None


def responder_sim_ou_nao_sobre_pessoa(filme_atual, cliente, nomes, papel):
    """
    "A Robin Tunney está no elenco?" -> "Sim! Robin Tunney está no elenco de O Mentalista."
    "O Tom Hanks está no elenco?"    -> "Não, Tom Hanks não está no elenco de O Mentalista."
    Sem nome de pessoa na pergunta   -> None (aí mostra a lista inteira).
    """
    pessoa = pessoa_citada_na_lista(cliente, nomes)
    if pessoa is not None:
        return f'Sim! {pessoa} {papel["sim"]} {filme_atual["nome"]}.'

    diretor, ator = detectar_diretor_e_ator(cliente)
    outra_pessoa = ator or diretor
    if outra_pessoa is not None:
        return (
            f'Não, {outra_pessoa} {papel["nao"]} {filme_atual["nome"]}. '
            f'{papel["rotulo"]}: {", ".join(nomes)}.'
        )
    return None


PAPEL_ELENCO = {"sim": "está no elenco de", "nao": "não está no elenco de", "rotulo": "Elenco"}


def responder_sobre_filme(filme_atual, cliente):

    # Usa .get() para não quebrar se algum campo faltar
    # (o catálogo do TMDB, por exemplo, não traz prêmios).
    elenco = filme_atual.get("elenco", [])
    premios = filme_atual.get("premios", [])
    indicacoes = filme_atual.get("indicacoes", [])

    # Prêmios
    if contem_alguma_palavra(cliente, ["premio", "premios", "premiado", "premiacao"]):
        if len(premios) == 0:
            return "Não tenho informações sobre prêmios."
        return f"Prêmios: {', '.join(premios)}"

    # Indicações
    if contem_alguma_palavra(cliente, ["indicacao", "indicacoes", "indicado", "indicada"]):
        if len(indicacoes) == 0:
            return "Não tenho informações sobre indicações."
        return f"Indicações: {', '.join(indicacoes)}"

    # Elenco
    if contem_alguma_palavra(
        cliente,
        ["elenco", "ator", "atores", "atriz", "atrizes", "protagonista", "protagonistas"]
    ):
        if len(elenco) == 0:
            return "Não tenho informações sobre o elenco."
        resposta_pessoa = responder_sim_ou_nao_sobre_pessoa(filme_atual, cliente, elenco, PAPEL_ELENCO)
        if resposta_pessoa is not None:
            return resposta_pessoa
        return f"Elenco: {', '.join(elenco)}"

    serie = eh_serie(filme_atual)

    # Duração ("Quanto tempo dura cada episódio?" vem antes das temporadas)
    if contem_alguma_palavra(cliente, PALAVRAS_DE_DURACAO):
        duracao = formatar_duracao_curta(filme_atual.get("duracao_minutos"))
        if serie:
            texto = f"Cada episódio tem cerca de {duracao}."
            if filme_atual.get("episodios") and filme_atual.get("duracao_minutos"):
                horas = round(tempo_total_em_minutos(filme_atual) / 60)
                texto += f' São {filme_atual["episodios"]} episódios: umas {horas} horas para maratonar.'
            return texto
        return f"Duração: {duracao}."

    # Temporadas e episódios
    if contem_alguma_palavra(cliente, ["temporada", "temporadas", "episodio", "episodios"]):
        if not serie:
            return (
                f'{filme_atual["nome"]} é um filme, não tem temporadas. '
                f'Duração: {formatar_duracao_curta(filme_atual.get("duracao_minutos"))}.'
            )
        return f'{filme_atual["nome"]}: {resumo_das_temporadas(filme_atual)}.'

    # Status da série: "Ela já acabou?", "Foi cancelada?"
    if serie and contem_alguma_palavra(cliente, PALAVRAS_DE_STATUS):
        return frase_do_status(filme_atual)

    # Criador da série
    if contem_alguma_palavra(cliente, PALAVRAS_DE_CRIADOR):
        rotulo = "Criação" if serie else "Direção"
        return f'{rotulo}: {filme_atual.get("diretor", "Não informado")}'

    # Diretor
    if contem_alguma_palavra(
        cliente,
        ["diretor", "diretora", "diretores", "dirigiu", "dirigido", "direcao"]
    ):
        rotulo = "Criação" if serie else "Diretor"
        diretores = perfil.diretores_do_filme(filme_atual)
        papel = {
            "sim": "criou" if serie else "dirigiu",
            "nao": "não criou" if serie else "não dirigiu",
            "rotulo": rotulo,
        }
        resposta_pessoa = responder_sim_ou_nao_sobre_pessoa(filme_atual, cliente, diretores, papel)
        if resposta_pessoa is not None:
            return resposta_pessoa
        return f'{rotulo}: {filme_atual.get("diretor", "Não informado")}'

    # Ano
    if contem_alguma_palavra(cliente, ["ano", "lancado", "lancamento", "lancou", "estreou", "estreia"]):
        if serie:
            return f'Estreou em {filme_atual["ano"]} (exibida em {periodo_de_exibicao(filme_atual)}).'
        return f'Ano: {filme_atual.get("ano", "Não informado")}'

    # Gênero
    if contem_alguma_palavra(cliente, ["genero", "generos"]):
        return f'Gênero: {filme_atual.get("genero", "Não informado")}'

    # Notas (Rotten Tomatoes, IMDb, Metacritic, TMDB)
    if contem_alguma_palavra(
        cliente,
        ["nota", "notas", "avaliacao", "avaliacoes", "rotten", "tomatoes",
         "imdb", "metacritic", "critica", "criticas"]
    ):
        notas = linhas_de_avaliacao(filme_atual)

        if len(notas) == 0:
            return "Ainda não tenho notas para esse filme."

        return "\n".join(notas)

    # Perguntas abertas: a IA responde só com base na sinopse
    prompt = f"""
    Sinopse:

    {filme_atual["sinopse"]}

    Pergunta:

    {cliente}

    Responda usando exclusivamente a sinopse fornecida.

    Regras:
    - Responda sempre em português do Brasil.
    - Não use conhecimento externo.
    - Não acrescente fatos.
    - Não faça interpretações.
    - Se a informação não estiver na sinopse,
      responda apenas:
      "Não tenho essa informação."
    - Responda de forma curta.
    """

    return perguntar_ao_modelo(prompt)


# =========================================================
# PERGUNTAS E NOTAS SOBRE VOCÊ (favoritos, assistidos, estrelas)
# =========================================================
# Exemplos que esta parte entende:
#   "Dou 5 estrelas para Shrek"        -> salva a nota
#   "Dei 4 estrelas pra esse"          -> salva a nota do filme atual
#   "Qual nota eu dei para Shrek?"     -> consulta a nota
#   "Quais filmes eu dei 5 estrelas?"  -> lista por nota
#   "Quais filmes eu avaliei?"         -> lista todos avaliados
#   "Quais são meus favoritos?"        -> lista favoritos
#   "Quais filmes eu já assisti?"      -> lista assistidos

NUMEROS_POR_EXTENSO = {
    "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5
}

PALAVRAS_DE_PERGUNTA = {"qual", "quais", "quanto", "quanta", "quantos", "quantas"}
PALAVRAS_DE_LISTAR = {"lista", "liste", "listar", "mostra", "mostre", "mostrar"}

VERBOS_DE_DAR_NOTA = {
    "dou", "dei", "darei", "daria", "dar", "avalio", "avaliei", "avaliar",
    "merece", "mereceu", "coloca", "coloque", "coloquei", "bota", "bote", "botei"
}

VERBOS_DE_NOTA_DADA = {"dei", "avaliei", "coloquei", "botei"}

LIMITE_ITENS_LISTA = 15


def numero_de_estrelas(palavra):
    if palavra.isdigit():
        return int(palavra)
    return NUMEROS_POR_EXTENSO.get(palavra)


def detectar_quantidade_estrelas(cliente):
    """
    Número de 1 a 5 colado em "estrela(s)" ou "nota":
    "5 estrelas", "cinco estrelas", "nota 4", "uma estrela" -> 5, 5, 4, 1
    """
    palavras = extrair_palavras(cliente)

    for posicao, palavra in enumerate(palavras):
        if palavra not in ("estrela", "estrelas", "nota"):
            continue

        vizinhas = []
        if posicao > 0:
            vizinhas.append(palavras[posicao - 1])  # "5 estrelas"
        if posicao + 1 < len(palavras):
            vizinhas.append(palavras[posicao + 1])  # "nota 5"

        for vizinha in vizinhas:
            quantidade = numero_de_estrelas(vizinha)
            if quantidade is not None and usuario.NOTA_MINIMA <= quantidade <= usuario.NOTA_MAXIMA:
                return quantidade

    return None


def encontrar_filme_citado(cliente):
    """
    Procura um filme citado pelo nome na mensagem.
    Se mais de um casar (ex.: os dois "O Rei Leão"), prefere o que você já
    assistiu e, depois, o mais popular. Títulos mais longos ganham dos curtos.
    """
    filmes_citados = [filme for filme in filmes if filme_citado_pelo_nome(filme, cliente)]

    if len(filmes_citados) == 0:
        return None

    def tamanho_titulo_citado(filme):
        return max(
            (
                len(titulo)
                for titulo in filme["titulos_busca"]
                if contem_expressao(cliente, titulo)
            ),
            default=len(min(filme.get("titulos_curtos") or {""}, key=len))
        )

    return max(
        filmes_citados,
        key=lambda filme: (
            tamanho_titulo_citado(filme),
            usuario.foi_assistido(filme),
            popularidade(filme)
        )
    )


def encontrar_filmes_citados(cliente):
    """
    TODOS os filmes citados pelo nome, na ordem em que aparecem na frase.
    "Interestelar ou Matrix?" -> [Interestelar, Matrix]

    Títulos que se sobrepõem disputam o mesmo trecho: em "Shrek 2 ou Toy Story",
    "Shrek 2" ganha de "Shrek" (título mais longo). Para o mesmo título
    (os dois "O Rei Leão"), vale a mesma regra do encontrar_filme_citado.
    """
    texto = " ".join(extrair_palavras(cliente))
    trechos = []  # (inicio, fim, filme, tamanho_titulo)

    for filme in filmes:
        for titulo in filme.get("titulos_busca", set()):
            for encontrado in re.finditer(rf"\b{re.escape(titulo)}\b", texto):
                trechos.append((encontrado.start(), encontrado.end(), filme, len(titulo)))

        # Títulos curtos com maiúscula ("Dark ou Stranger Things?"): a posição é
        # medida no texto original; convertemos para o texto sem acentos pela
        # quantidade de palavras antes dele.
        for titulo in filme.get("titulos_curtos", set()):
            encontrado = posicao_titulo_curto(cliente, titulo)
            if encontrado is not None:
                palavras_antes = len(extrair_palavras(cliente[:encontrado.start()]))
                inicio = len(" ".join(texto.split()[:palavras_antes])) + (1 if palavras_antes else 0)
                trechos.append((inicio, inicio + len(normalizar_texto(titulo)), filme, len(titulo)))

    # Os maiores títulos escolhem primeiro; empate: já assistido, depois o mais popular.
    trechos.sort(
        key=lambda trecho: (trecho[3], usuario.foi_assistido(trecho[2]), popularidade(trecho[2])),
        reverse=True
    )

    escolhidos = []
    for inicio, fim, filme, _ in trechos:
        sobrepoe = any(inicio < fim_usado and inicio_usado < fim for inicio_usado, fim_usado, _ in escolhidos)
        repetido = any(filme is filme_usado for _, _, filme_usado in escolhidos)
        if not sobrepoe and not repetido:
            escolhidos.append((inicio, fim, filme))

    escolhidos.sort(key=lambda trecho: trecho[0])
    return [filme for _, _, filme in escolhidos]


def descrever_filme_curto(filme):
    if eh_serie(filme):
        return f'{filme["nome"]} ({periodo_de_exibicao(filme)}, série)'
    return f'{filme["nome"]} ({filme["ano"]})'


def montar_lista(titulo, lista_filmes, mostrar_nota=False):
    linhas = [titulo]

    for filme in lista_filmes[:LIMITE_ITENS_LISTA]:
        linha = f"• {descrever_filme_curto(filme)}"
        if mostrar_nota and usuario.obter_nota(filme) is not None:
            linha += f"  {usuario.texto_estrelas(usuario.obter_nota(filme))}"
        linhas.append(linha)

    quantidade_restante = len(lista_filmes) - LIMITE_ITENS_LISTA
    if quantidade_restante > 0:
        linhas.append(f"… e mais {quantidade_restante}. Veja todos em ♥ Meus filmes.")

    return "\n".join(linhas)


def responder_sobre_usuario(cliente):
    """
    Trata mensagens sobre os SEUS dados. Retorna um resultado pronto
    ou None (quando a mensagem não é sobre você e deve seguir o fluxo normal).
    """
    palavras = set(extrair_palavras(cliente))

    # "que" sozinho não conta ("um filme QUE eu vi na infância" não é pergunta),
    # mas "QUE FILMES eu vi?" e qualquer frase com "?" contam.
    eh_pergunta = (
        bool(palavras & PALAVRAS_DE_PERGUNTA)
        or bool(palavras & PALAVRAS_DE_LISTAR)
        or contem_expressao(cliente, "que filmes")
        or contem_expressao(cliente, "que nota")
        or "?" in cliente
    )
    quantidade_estrelas = detectar_quantidade_estrelas(cliente)
    fala_de_nota = bool(palavras & {"nota", "notas", "estrela", "estrelas"})
    cita_filme_atual = bool(palavras & PALAVRAS_SOBRE_FILME_ATUAL)

    # ---------- Dar nota: "Dou 5 estrelas para Shrek" ----------
    comeca_com_nota = extrair_palavras(cliente)[:1] == ["nota"]

    if (
        quantidade_estrelas is not None
        and not eh_pergunta
        and (palavras & VERBOS_DE_DAR_NOTA or comeca_com_nota)
    ):
        filme_alvo = encontrar_filme_citado(cliente) or filme_atual

        if filme_alvo is None:
            return criar_resultado(
                "Para qual filme é essa nota? Diga o nome, por exemplo: "
                f'"Dou {quantidade_estrelas} estrelas para Shrek".'
            )

        ja_tinha_assistido = usuario.foi_assistido(filme_alvo)
        usuario.definir_nota(filme_alvo, quantidade_estrelas)

        texto = (
            f"Anotado! {usuario.texto_estrelas(quantidade_estrelas)} "
            f"para {descrever_filme_curto(filme_alvo)}."
        )
        if not ja_tinha_assistido:
            texto += " ✅ Também marquei como assistido."

        return criar_resultado(texto, tipo="usuario_atualizado")

    # ---------- Consultar uma nota: "Qual nota eu dei para Shrek?" ----------
    perguntou_nota_dada = fala_de_nota and bool(palavras & VERBOS_DE_NOTA_DADA)
    perguntou_minha_nota = contem_expressao(cliente, "minha nota")

    if eh_pergunta and (perguntou_nota_dada or perguntou_minha_nota) and quantidade_estrelas is None:
        filme_alvo = encontrar_filme_citado(cliente)

        if filme_alvo is None and cita_filme_atual:
            filme_alvo = filme_atual

        if filme_alvo is not None:
            nota = usuario.obter_nota(filme_alvo)
            if nota is None:
                return criar_resultado(
                    f"Você ainda não deu nota para {descrever_filme_curto(filme_alvo)}. "
                    'É só dizer, por exemplo: "Dou 4 estrelas".'
                )
            return criar_resultado(
                f"Você deu {usuario.texto_estrelas(nota)} ({nota} de "
                f"{usuario.NOTA_MAXIMA}) para {descrever_filme_curto(filme_alvo)}."
            )

    # ---------- Listar por nota: "Quais filmes eu dei 5 estrelas?" ----------
    falou_de_avaliacoes = bool(palavras & {"avaliei", "avaliados", "avaliadas", "notas"})
    falou_de_si = bool(palavras & {"meus", "minhas", "eu", "meu", "minha"})

    quer_lista_avaliados = (
        perguntou_nota_dada
        or perguntou_minha_nota
        or (falou_de_avaliacoes and falou_de_si)
    )

    if eh_pergunta and quer_lista_avaliados:
        avaliados = usuario.filmes_avaliados(filmes, quantidade_estrelas)

        if quantidade_estrelas is not None:
            if len(avaliados) == 0:
                return criar_resultado(
                    f"Você ainda não deu {usuario.texto_estrelas(quantidade_estrelas)} "
                    "para nenhum filme."
                )
            return criar_resultado(montar_lista(
                f"Filmes que você deu {usuario.texto_estrelas(quantidade_estrelas)} ({len(avaliados)}):",
                avaliados
            ))

        if len(avaliados) == 0:
            return criar_resultado(
                "Você ainda não avaliou nenhum filme. Abra um filme e clique "
                'nas estrelas, ou me diga: "Dou 5 estrelas para Shrek".'
            )
        return criar_resultado(montar_lista(
            f"Seus filmes avaliados ({len(avaliados)}):",
            avaliados,
            mostrar_nota=True
        ))

    # ---------- Perfil: "Qual é o meu gênero favorito?" ----------
    expressoes_de_perfil = [
        "genero favorito", "generos favoritos", "genero preferido", "generos preferidos",
        "diretor favorito", "diretores favoritos", "ator favorito", "atores favoritos",
        "do que eu gosto", "o que eu gosto", "meu gosto", "meu perfil"
    ]
    perguntou_perfil = any(contem_expressao(cliente, expressao) for expressao in expressoes_de_perfil)

    if eh_pergunta and (perguntou_perfil or ("perfil" in palavras and falou_de_si)):
        return criar_resultado(perfil.resumo_do_perfil(perfil.calcular_perfil(filmes)))

    # ---------- Favoritos: "Quais são meus favoritos?" ----------
    # "meus favoritos" sozinho também vale; "um filme parecido com meus
    # favoritos" não (isso é pedido de recomendação, para a próxima etapa).
    so_pediu_favoritos = palavras <= {"meus", "favoritos", "ver", "os", "me", "mostra", "quero"}

    if palavras & {"favoritos", "favoritei", "favorito"} and (eh_pergunta or so_pediu_favoritos):
        favoritos = usuario.filmes_da_lista("favoritos", filmes)
        if len(favoritos) == 0:
            return criar_resultado("Você ainda não tem favoritos. Abra um filme e clique em 🤍 Favoritar.")
        return criar_resultado(montar_lista(f"Seus favoritos ❤️ ({len(favoritos)}):", favoritos, mostrar_nota=True))

    # ---------- Assistidos: "Quais filmes eu já assisti?" ----------
    if (
        eh_pergunta
        and palavras & {"assisti", "vi"}
        and palavras & {"eu", "ja"}
        and "nao" not in palavras  # "um filme que eu ainda não assisti" é busca
    ):
        assistidos = usuario.filmes_da_lista("assistidos", filmes)
        if len(assistidos) == 0:
            return criar_resultado("Você ainda não marcou nenhum filme como assistido.")
        return criar_resultado(montar_lista(f"Filmes que você já assistiu ✅ ({len(assistidos)}):", assistidos, mostrar_nota=True))

    return None


# =========================================================
# PEDIDOS RELATIVOS ("parecido com esse", "um mais recente"...)
# =========================================================
# O filme de referência é o citado pelo nome ("parecido com Shrek")
# ou, se nenhum for citado, o filme atual da conversa.

PEDIDOS_RELATIVOS = {
    "mesmo_diretor": [
        "mesmo diretor", "mesma diretora", "mesma direcao", "dirigido pelo mesmo",
        "dirigida pela mesma", "do mesmo cara", "outro do diretor", "outro filme do diretor"
    ],
    "mesmo_ator": [
        "mesmo ator", "mesma atriz", "mesmo elenco", "mesmos atores",
        "mesmo protagonista", "mesma protagonista", "com o mesmo ator", "com a mesma atriz"
    ],
    "mais_recente": [
        "mais recente", "mais recentes", "mais novo", "mais nova", "mais novos",
        "mais atual", "mais moderno", "mais moderna", "lancado depois"
    ],
    "mais_antigo": [
        "mais antigo", "mais antiga", "mais antigos", "mais velho", "mais velha",
        "lancado antes"
    ],
    "mais_curto": ["mais curto", "mais curta", "menos longo", "mais rapido de ver", "menor duracao"],
    "mais_longo": ["mais longo", "mais longa", "mais comprido", "maior duracao"],
    "mais_leve": [
        "mais leve", "mais leves", "mais tranquilo", "mais tranquila", "mais divertido",
        "mais divertida", "mais engracado", "mais engracada", "menos pesado", "menos tenso",
        "menos sombrio", "algo leve", "filme leve", "bem leve", "levinho", "algo tranquilo"
    ],
    "mais_pesado": [
        "mais pesado", "mais pesada", "mais tenso", "mais tensa", "mais sombrio",
        "mais sombria", "mais intenso", "mais intensa", "mais serio", "mais seria",
        "mais dark", "menos leve", "algo pesado", "algo tenso", "filme pesado", "algo sombrio"
    ],
    "parecido": [
        "parecido", "parecida", "parecidos", "parecidas", "similar", "similares",
        "semelhante", "semelhantes", "nessa linha", "nesse estilo", "do mesmo estilo",
        "mesma vibe", "nessa vibe", "tipo esse", "tipo ele", "igual a esse",
        "como esse", "no estilo de", "na linha de"
    ],
}

# Ordem de prioridade: "um mais recente parecido com esse" é "mais_recente".
ORDEM_PEDIDOS_RELATIVOS = [
    "mesmo_diretor", "mesmo_ator", "mais_recente", "mais_antigo",
    "mais_curto", "mais_longo", "mais_leve", "mais_pesado", "parecido"
]

# Quanto cada gênero deixa um filme mais leve (+) ou mais pesado (-).
PESO_LEVEZA_GENERO = {
    "comedia": 2, "animacao": 2, "familia": 2,
    "musica": 1, "romance": 1, "aventura": 1, "fantasia": 1,
    "terror": -2, "guerra": -2,
    "crime": -1, "thriller": -1, "drama": -1, "misterio": -1, "historia": -1,
}
LEVEZA_MINIMA_ABSOLUTA = 1.0   # "algo leve" sem filme de referência (média >= 1)
PESO_MAXIMO_ABSOLUTO_TENSO = -0.5  # "algo tenso" sem referência (média <= -0.5)
DIFERENCA_MINIMA_LEVEZA = 0.5   # "mais leve que X" precisa ser leve de verdade a mais
PESO_LEVEZA_NA_ORDEM = 0.35     # "algo leve": quanto a leveza pesa junto com o seu gosto


def leveza(filme):
    """
    Média dos pesos dos gêneros (de -2 a +2).
    Shrek (Animação, Comédia, Família...) ≈ 1,6  |  Dunkirk (Guerra, Ação, Drama) = -1.
    É média (e não soma) para um filme com muitos gêneros não parecer mais leve só por isso.
    """
    generos = perfil.generos_do_filme(filme)
    if not generos:
        return 0.0
    return sum(
        PESO_LEVEZA_GENERO.get(" ".join(extrair_palavras(genero)), 0)
        for genero in generos
    ) / len(generos)


def generos_com_sinal(filme, positivos):
    """Gêneros do filme que puxam para leve (positivos=True) ou pesado."""
    resultado = []
    for genero in perfil.generos_do_filme(filme):
        peso = PESO_LEVEZA_GENERO.get(" ".join(extrair_palavras(genero)), 0)
        if (positivos and peso > 0) or (not positivos and peso < 0):
            resultado.append(genero)
    return resultado

PESO_GENERO_NA_SEMELHANCA = 0.15


def detectar_pedido_relativo(cliente):
    # "parecido com meus favoritos" é pedido personalizado, não relativo.
    if contem_expressao(cliente, "meus favoritos") or contem_expressao(cliente, "meu gosto"):
        return None

    for tipo in ORDEM_PEDIDOS_RELATIVOS:
        for expressao in PEDIDOS_RELATIVOS[tipo]:
            if contem_expressao(cliente, expressao):
                return tipo

    return None


def semelhanca_entre_filmes(filme_referencia, outro_filme):
    """Significado da sinopse + bônus pelos gêneros em comum (0 a 1)."""
    similaridade = float(np.dot(filme_referencia["vetor_sinopse"], outro_filme["vetor_sinopse"]))

    generos_referencia = set(perfil.generos_do_filme(filme_referencia))
    generos_outro = set(perfil.generos_do_filme(outro_filme))
    generos_juntos = generos_referencia | generos_outro

    if generos_juntos:
        jaccard = len(generos_referencia & generos_outro) / len(generos_juntos)
        similaridade += PESO_GENERO_NA_SEMELHANCA * jaccard

    return similaridade


def ordenar_por_semelhanca(filme_referencia, candidatos):
    return sorted(
        candidatos,
        key=lambda filme: semelhanca_entre_filmes(filme_referencia, filme),
        reverse=True
    )


def filtrar_relativo(tipo, filme_referencia, candidatos):
    """Aplica a regra do pedido sobre a lista de candidatos."""
    if tipo == "mesmo_diretor":
        diretores = {normalizar_texto(nome) for nome in perfil.diretores_do_filme(filme_referencia)}
        return [
            filme for filme in candidatos
            if diretores & {normalizar_texto(nome) for nome in perfil.diretores_do_filme(filme)}
        ]

    if tipo == "mesmo_ator":
        atores = {normalizar_texto(nome) for nome in perfil.atores_principais(filme_referencia)}
        return [
            filme for filme in candidatos
            if atores & {normalizar_texto(nome) for nome in filme.get("elenco", [])}
        ]

    if tipo == "mais_recente":
        return [filme for filme in candidatos if filme["ano"] > filme_referencia["ano"]]

    if tipo == "mais_antigo":
        return [filme for filme in candidatos if filme["ano"] < filme_referencia["ano"]]

    duracao_referencia = filme_referencia.get("duracao_minutos")

    if tipo in ("mais_curto", "mais_longo"):
        if not duracao_referencia:
            return []
        if tipo == "mais_curto":
            return [
                filme for filme in candidatos
                if filme.get("duracao_minutos") and filme["duracao_minutos"] < duracao_referencia
            ]
        return [
            filme for filme in candidatos
            if filme.get("duracao_minutos") and filme["duracao_minutos"] > duracao_referencia
        ]

    if tipo == "mais_leve":
        limite = leveza(filme_referencia) + DIFERENCA_MINIMA_LEVEZA
        return [filme for filme in candidatos if leveza(filme) >= limite]

    if tipo == "mais_pesado":
        limite = leveza(filme_referencia) - DIFERENCA_MINIMA_LEVEZA
        return [filme for filme in candidatos if leveza(filme) <= limite]

    return list(candidatos)  # "parecido": só ordena


def explicar_relativo(tipo, filme_referencia, filme):
    # "Quero algo leve" sem filme de referência
    if filme_referencia is None:
        if tipo == "mais_leve":
            leves = generos_com_sinal(filme, positivos=True) or perfil.generos_do_filme(filme)
            return f"☀️ Um filme leve: {', '.join(leves)}."
        pesados = generos_com_sinal(filme, positivos=False) or perfil.generos_do_filme(filme)
        return f"🌑 Um filme mais tenso: {', '.join(pesados)}."

    nome_referencia = filme_referencia["nome"]

    if tipo == "mesmo_diretor":
        diretores_comuns = [
            nome for nome in perfil.diretores_do_filme(filme)
            if normalizar_texto(nome) in {normalizar_texto(d) for d in perfil.diretores_do_filme(filme_referencia)}
        ]
        verbo = "criado" if eh_serie(filme) else "dirigido"
        return f"🎬 Também {verbo} por {', '.join(diretores_comuns)}, como {nome_referencia}."

    if tipo == "mesmo_ator":
        atores_referencia = {normalizar_texto(nome) for nome in perfil.atores_principais(filme_referencia)}
        atores_comuns = [nome for nome in filme.get("elenco", []) if normalizar_texto(nome) in atores_referencia]
        return f"⭐ Também com {', '.join(atores_comuns)}, de {nome_referencia}."

    if tipo == "mais_recente":
        return f"📅 Mais recente que {nome_referencia} ({filme_referencia['ano']}) e no mesmo estilo."

    if tipo == "mais_antigo":
        return f"📅 Mais antigo que {nome_referencia} ({filme_referencia['ano']}) e no mesmo estilo."

    if tipo == "mais_leve":
        leves = generos_com_sinal(filme, positivos=True) or perfil.generos_do_filme(filme)
        return f"☀️ Mais leve que {nome_referencia}: {', '.join(leves)}."

    if tipo == "mais_pesado":
        pesados = generos_com_sinal(filme, positivos=False) or perfil.generos_do_filme(filme)
        return f"🌑 Mais tenso que {nome_referencia}: {', '.join(pesados)}."

    if tipo in ("mais_curto", "mais_longo"):
        palavra = "Mais curto" if tipo == "mais_curto" else "Mais longo"
        return (
            f"⏱️ {palavra} que {nome_referencia}: {filme['duracao_minutos']} min "
            f"(contra {filme_referencia['duracao_minutos']} min)."
        )

    generos_comuns = [
        genero for genero in perfil.generos_do_filme(filme)
        if genero in perfil.generos_do_filme(filme_referencia)
    ]
    if generos_comuns:
        return f"🔗 Parecido com {nome_referencia}: {', '.join(generos_comuns)}, com uma história na mesma linha."
    return f"🔗 Tem uma história parecida com a de {nome_referencia}."


def pontuar_leveza(filme, leve):
    """De -1 a 1: quanto o filme atende ao pedido ("leve" ou "tenso")."""
    valor = leveza(filme) / 2  # leveza vai de -2 a 2
    return valor if leve else -valor


def ordenar_por_leveza(candidatos, perfil_atual, leve):
    """
    "Algo leve": o filme precisa combinar com você E ser leve de verdade.
    Assim Shrek ganha de um filme que só passou raspando no mínimo de leveza.
    """
    tipo = "mais_leve" if leve else "mais_pesado"

    if perfil_atual["suficiente"]:
        def pontuacao(filme):
            # O seu gosto conta só pelos gêneros que combinam com o pedido:
            # amar Drama não pode puxar um "filme leve" que é meio drama.
            contrarios = set(generos_contrarios(filme, tipo))
            generos_a_favor = [
                genero for genero in perfil.generos_do_filme(filme) if genero not in contrarios
            ]
            filme_para_pontuar = dict(filme, genero=", ".join(generos_a_favor))
            return (
                perfil.pontuar_filme(filme_para_pontuar, perfil_atual)[0]
                + PESO_LEVEZA_NA_ORDEM * pontuar_leveza(filme, leve)
            )
    else:
        def pontuacao(filme):
            return (
                perfil.popularidade_normalizada(filme)
                + 0.5 * perfil.qualidade_normalizada(filme)
                + PESO_LEVEZA_NA_ORDEM * pontuar_leveza(filme, leve)
            )

    return sorted(candidatos, key=pontuacao, reverse=True)


def generos_contrarios(filme, tipo_relativo):
    """Gêneros que vão contra o pedido: "Crime" num pedido leve, "Comédia" num tenso."""
    if tipo_relativo == "mais_leve":
        return generos_com_sinal(filme, positivos=False)
    if tipo_relativo == "mais_pesado":
        return generos_com_sinal(filme, positivos=True)
    return []


def filmes_mais_leves_ou_pesados(leve):
    """"Algo leve" sem filme de referência: filmes claramente leves (ou tensos)."""
    if leve:
        return [filme for filme in filmes if leveza(filme) >= LEVEZA_MINIMA_ABSOLUTA]
    return [filme for filme in filmes if leveza(filme) <= PESO_MAXIMO_ABSOLUTO_TENSO]


# =========================================================
# FILMES SEMELHANTES (tela de detalhes)
# =========================================================
QUANTIDADE_SEMELHANTES = 6


def filmes_semelhantes(filme_referencia, quantidade=QUANTIDADE_SEMELHANTES):
    """Os filmes do catálogo mais parecidos (sinopse + gêneros) com o filme escolhido."""
    chave_referencia = usuario.chave_filme(filme_referencia)
    outros = [filme for filme in filmes if usuario.chave_filme(filme) != chave_referencia]
    return ordenar_por_semelhanca(filme_referencia, outros)[:quantidade]


# =========================================================
# TRAILER
# =========================================================
def url_trailer(filme):
    """
    Trailer do YouTube salvo pelo importar_trailers.py; se não tiver,
    abre uma busca no YouTube pelo trailer do filme.
    """
    codigo_video = filme.get("trailer_youtube")
    if codigo_video:
        return f"https://www.youtube.com/watch?v={codigo_video}"

    busca = f"{filme['nome']} {filme.get('ano', '')} trailer oficial"
    return f"https://www.youtube.com/results?search_query={quote_plus(busca)}"


def tem_trailer_salvo(filme):
    return bool(filme.get("trailer_youtube"))


# =========================================================
# POR QUE ESSE FILME? (explicação da busca)
# =========================================================
NOMES_DA_QUALIDADE = {
    "critica": "a crítica amou",
    "publico": "o público adorou",
    "geral": "bem avaliado",
    "classico": "clássico",
}
MAXIMO_PALAVRAS_EM_COMUM = 4


def palavras_em_comum(busca, filme):
    """Palavras da busca que também aparecem no título ou na sinopse do filme."""
    encontradas = []
    for palavra in extrair_palavras(busca):
        if len(palavra) < 4 or palavra in PALAVRAS_IGNORADAS_NA_BUSCA:
            continue
        if raiz_da_palavra(palavra) in filme["raizes_texto"] and palavra not in encontradas:
            encontradas.append(palavra)
    return encontradas[:MAXIMO_PALAVRAS_EM_COMUM]


def explicar_busca(cliente, filme, busca_semantica=None):
    """
    "💡 Por que esse? Você pediu: comédia · com Jack Black · sobre
     'banda de rock na escola' (palavras em comum: banda, escola)."
    Devolve "" quando não há nada para explicar.
    """
    motivos = []

    tipo = detectar_tipo(cliente)
    if tipo == TIPO_SERIE:
        motivos.append("série")

    genero = detectar_genero(cliente)
    if genero:
        generos_do_filme = [
            nome for nome in perfil.generos_do_filme(filme)
            if " ".join(extrair_palavras(nome)) == genero
        ]
        motivos.append((generos_do_filme[0] if generos_do_filme else genero).lower())

    diretor, ator = detectar_diretor_e_ator(cliente)
    if diretor:
        motivos.append(f"{'criada' if eh_serie(filme) else 'dirigido'} por {diretor}")
    if ator:
        motivos.append(f"com {ator}")

    ano = detectar_ano(cliente)
    if ano:
        motivos.append(f"de {ano}")
    decada = detectar_decada(cliente)
    if decada:
        motivos.append(f"dos anos {decada[0]}")

    qualidade = detectar_qualidade(cliente)
    if qualidade:
        motivos.append(NOMES_DA_QUALIDADE[qualidade])

    if busca_semantica:
        texto_assunto = f'sobre "{busca_semantica}"'
        comuns = palavras_em_comum(busca_semantica, filme)
        if comuns:
            texto_assunto += f" (palavras em comum: {', '.join(comuns)})"
        else:
            texto_assunto += " (história com o mesmo sentido)"
        motivos.append(texto_assunto)

    if not motivos:
        return ""

    return "💡 Por que esse? Você pediu: " + " · ".join(motivos) + "."


MENSAGEM_SEM_RELATIVO = {
    "mesmo_diretor": "Não encontrei outro filme do mesmo diretor de {nome} no catálogo.",
    "mesmo_ator": "Não encontrei outro filme com o elenco principal de {nome} no catálogo.",
    "mais_recente": "Não encontrei um filme mais recente parecido com {nome}.",
    "mais_antigo": "Não encontrei um filme mais antigo parecido com {nome}.",
    "mais_curto": "Não encontrei um filme mais curto parecido com {nome}.",
    "mais_longo": "Não encontrei um filme mais longo parecido com {nome}.",
    "mais_leve": "Não encontrei um filme mais leve parecido com {nome}.",
    "mais_pesado": "Não encontrei um filme mais tenso parecido com {nome}.",
    "parecido": "Não encontrei outro filme parecido com {nome}.",
}


# =========================================================
# COMPARAR TÍTULOS ("Interestelar ou Matrix?")
# =========================================================
PALAVRAS_DE_COMPARACAO = {
    "compara", "comparar", "compare", "comparacao", "versus", "vs", "x",
    "diferenca", "diferencas", "melhor"
}
PALAVRAS_DO_FILME_ATUAL = {"esse", "este", "ele", "desse", "deste", "atual"}


def formatar_duracao_curta(minutos):
    if not minutos:
        return "—"
    horas, resto = divmod(int(minutos), 60)
    if horas == 0:
        return f"{resto}min"
    return f"{horas}h {resto:02d}min" if resto else f"{horas}h"


def detectar_comparacao(cliente):
    """
    Devolve (filme_a, filme_b) ou None.

    "Interestelar ou Matrix?"           -> dois filmes + "ou"
    "Compare Shrek e Toy Story"          -> dois filmes + "compare"
    "Esse ou Matrix?" / "Compare com Matrix" (com filme na conversa)
    "Parecido com Shrek ou Toy Story"   -> NÃO (é pedido relativo)
    """
    palavras = set(extrair_palavras(cliente))
    tem_ou = "ou" in palavras
    tem_palavra_de_comparar = bool(palavras & PALAVRAS_DE_COMPARACAO)

    if not (tem_ou or tem_palavra_de_comparar):
        return None

    if detectar_pedido_relativo(cliente) is not None:
        return None

    citados = encontrar_filmes_citados(cliente)

    if len(citados) >= 2:
        return citados[0], citados[1]

    if len(citados) == 1 and filme_atual is not None and citados[0] is not filme_atual:
        fala_do_atual = bool(palavras & PALAVRAS_DO_FILME_ATUAL)
        if tem_palavra_de_comparar or (tem_ou and fala_do_atual):
            return filme_atual, citados[0]

    return None


def linha_comparacao(rotulo, valor_a, valor_b, numero_a=None, numero_b=None, maior_vence=True):
    """
    Uma linha da tabela. Se houver números, marca o vencedor (0 = A, 1 = B).
    """
    vencedor = None
    if numero_a is not None and numero_b is not None and numero_a != numero_b:
        a_ganha = numero_a > numero_b if maior_vence else numero_a < numero_b
        vencedor = 0 if a_ganha else 1
    return {"rotulo": rotulo, "valores": [valor_a, valor_b], "vencedor": vencedor}


def comparar_filmes(filme_a, filme_b):
    """
    Monta a comparação completa (usada pelo chat e pela janela lado a lado):
    linhas da tabela, o que os dois têm em comum e os veredictos.
    """
    linhas = []
    dupla = (filme_a, filme_b)

    tem_serie = any(eh_serie(filme) for filme in dupla)
    mesmo_tipo = tipo_do_item(filme_a) == tipo_do_item(filme_b)

    if not mesmo_tipo:
        linhas.append(linha_comparacao("Tipo", *["Série" if eh_serie(f) else "Filme" for f in dupla]))

    linhas.append(linha_comparacao("Ano", *[periodo_de_exibicao(filme) for filme in dupla]))
    linhas.append(linha_comparacao("Gênero", *[filme.get("genero", "—") for filme in dupla]))
    rotulo_direcao = "Direção / Criação" if tem_serie and not all(eh_serie(f) for f in dupla) else (
        "Criação" if tem_serie else "Direção"
    )
    linhas.append(linha_comparacao(rotulo_direcao, *[filme.get("diretor", "—") for filme in dupla]))
    linhas.append(linha_comparacao(
        "Elenco", *[", ".join(perfil.atores_principais(filme)) or "—" for filme in dupla]
    ))

    if tem_serie:
        linhas.append(linha_comparacao(
            "Temporadas",
            *[resumo_das_temporadas(filme) if eh_serie(filme) else "—" for filme in dupla]
        ))

    duracoes = [filme.get("duracao_minutos") for filme in dupla]
    textos_duracao = [
        formatar_duracao_curta(duracao) + (" / episódio" if eh_serie(filme) and duracao else "")
        for filme, duracao in zip(dupla, duracoes)
    ]
    if mesmo_tipo:
        linhas.append(linha_comparacao("Duração", *textos_duracao, *duracoes, maior_vence=False))
    else:
        linhas.append(linha_comparacao("Duração", *textos_duracao))  # filme × episódio não se compara

    criticas = [nota_da_critica(filme) for filme in dupla]
    linhas.append(linha_comparacao(
        "Rotten (crítica)", *[f"{nota}%" if nota else "—" for nota in criticas], *criticas
    ))

    imdbs = [filme.get("nota_imdb") for filme in dupla]
    linhas.append(linha_comparacao(
        "IMDb", *[f"{formatar_nota(nota)}/10" if nota else "—" for nota in imdbs], *imdbs
    ))

    metas = [filme.get("metacritic") for filme in dupla]
    linhas.append(linha_comparacao(
        "Metacritic", *[f"{nota}/100" if nota else "—" for nota in metas], *metas
    ))

    perfil_atual = perfil.calcular_perfil(filmes)
    pontos_gosto = None
    if perfil_atual["suficiente"]:
        pontos_gosto = [perfil.pontuar_filme(filme, perfil_atual)[0] for filme in dupla]
        linhas.append(linha_comparacao(
            "Combina com você",
            *[f"{max(0, min(100, round(ponto * 100)))}%" for ponto in pontos_gosto],
            *pontos_gosto
        ))

    notas_suas = [usuario.obter_nota(filme) for filme in dupla]
    if any(nota is not None for nota in notas_suas):
        linhas.append(linha_comparacao(
            "Sua nota",
            *[usuario.texto_estrelas(nota) if nota else "—" for nota in notas_suas],
            *[nota or 0 for nota in notas_suas]
        ))

    # ---------- em comum ----------
    em_comum = []
    generos_comuns = [g for g in perfil.generos_do_filme(filme_a) if g in perfil.generos_do_filme(filme_b)]
    if generos_comuns:
        em_comum.append(f"🎭 Gêneros: {', '.join(generos_comuns)}")

    diretores_b = {normalizar_texto(nome) for nome in perfil.diretores_do_filme(filme_b)}
    diretores_comuns = [n for n in perfil.diretores_do_filme(filme_a) if normalizar_texto(n) in diretores_b]
    if diretores_comuns:
        rotulo_direcao = "Mesma criação" if tem_serie else "Mesma direção"
        em_comum.append(f"🎬 {rotulo_direcao}: {', '.join(diretores_comuns)}")

    elenco_b = {normalizar_texto(nome) for nome in filme_b.get("elenco", [])}
    atores_comuns = [n for n in filme_a.get("elenco", []) if normalizar_texto(n) in elenco_b]
    if atores_comuns:
        em_comum.append(f"⭐ No elenco dos dois: {', '.join(atores_comuns[:3])}")

    semelhanca = max(0, min(100, round(semelhanca_entre_filmes(filme_a, filme_b) * 100)))
    em_comum.append(f"🔗 Semelhança da história: {semelhanca}%")

    # ---------- veredictos ----------
    veredictos = []
    nomes = [filme["nome"] for filme in dupla]

    def vencedor_da_linha(rotulo):
        for linha in linhas:
            if linha["rotulo"] == rotulo:
                return linha
        return None

    for rotulo, frase in [
        ("Rotten (crítica)", "🍅 A crítica prefere {nome} ({valores})."),
        ("IMDb", "⭐ O público do IMDb prefere {nome} ({valores})."),
        ("Duração", "⏱️ {nome} é mais rápido de ver ({valores})."),
        ("Combina com você", "💡 Pelo seu gosto, {nome} combina mais com você ({valores})."),
    ]:
        linha = vencedor_da_linha(rotulo)
        if linha is not None and linha["vencedor"] is not None:
            vencedor = linha["vencedor"]
            valores = f'{linha["valores"][vencedor]} × {linha["valores"][1 - vencedor]}'
            veredictos.append(frase.format(nome=nomes[vencedor], valores=valores))

    return {
        "filmes": [filme_a, filme_b],
        "linhas": linhas,
        "em_comum": em_comum,
        "veredictos": veredictos,
        "semelhanca": semelhanca,
    }


def texto_da_comparacao(comparacao):
    filme_a, filme_b = comparacao["filmes"]
    partes = [f"⚖️ {descrever_filme_curto(filme_a)}  ×  {descrever_filme_curto(filme_b)}"]

    linhas_chat = []
    for linha in comparacao["linhas"]:
        if linha["rotulo"] in ("Elenco",):
            continue  # o elenco fica só na janela lado a lado
        valor_a, valor_b = linha["valores"]
        marca_a = " ★" if linha["vencedor"] == 0 else ""
        marca_b = " ★" if linha["vencedor"] == 1 else ""
        linhas_chat.append(f'• {linha["rotulo"]}: {valor_a}{marca_a}  |  {valor_b}{marca_b}')
    partes.append("\n".join(linhas_chat))

    partes.append("Em comum:\n" + "\n".join(comparacao["em_comum"]))

    if comparacao["veredictos"]:
        partes.append("\n".join(comparacao["veredictos"]))

    partes.append("Abri os dois lado a lado no diário. ✦")
    return "\n\n".join(partes)


# =========================================================
# BUSCA AVANÇADA DO CATÁLOGO (filtros clicáveis)
# =========================================================
TODOS = "Todos"
TIPOS_DO_CATALOGO = {"Todos": None, "Filmes": "filme", "Séries": "serie"}

ORDENS_DO_CATALOGO = [
    "Mais populares",
    "Crítica (Rotten)",
    "Público (IMDb)",
    "Combina comigo",
    "Mais recentes",
    "Mais antigos",
    "Mais curtos",
    "A–Z",
]

NOTAS_MINIMAS_DO_CATALOGO = {
    "Qualquer nota": None,
    "Rotten 70%+": 70,
    "Rotten 80%+": 80,
    "Rotten 90%+": 90,
}

ANO_DOS_CLASSICOS = 1980  # tudo antes disso fica junto em "Antes de 1980"


def generos_do_catalogo():
    """Nomes dos gêneros como aparecem no catálogo, em ordem alfabética."""
    nomes = {}
    for filme in filmes:
        for genero in perfil.generos_do_filme(filme):
            nomes.setdefault(normalizar_texto(genero), genero)
    return [nomes[chave] for chave in sorted(nomes)]


def decada_do_filme(filme):
    ano = filme.get("ano") or 0
    if ano < ANO_DOS_CLASSICOS:
        return f"Antes de {ANO_DOS_CLASSICOS}"
    return f"Anos {ano // 10 * 10}"


def decadas_do_catalogo():
    """'Anos 2020', 'Anos 2010', ..., 'Antes de 1980' (só as que existem)."""
    decadas = {decada_do_filme(filme) for filme in filmes}
    recentes = sorted((d for d in decadas if d.startswith("Anos")), reverse=True)
    antigas = [d for d in decadas if not d.startswith("Anos")]
    return recentes + antigas


def texto_pesquisavel(filme):
    """Nome, título original, ano, gêneros, direção e elenco, sem acentos."""
    if "texto_pesquisavel" not in filme:
        elenco = filme.get("elenco", [])
        if not isinstance(elenco, list):
            elenco = [str(elenco)]
        filme["texto_pesquisavel"] = normalizar_texto(" ".join([
            str(filme.get("nome", "")),
            str(filme.get("titulo_original", "")),
            str(filme.get("ano", "")),
            str(filme.get("genero", "")),
            str(filme.get("diretor", "")),
            " ".join(elenco),
            "serie" if eh_serie(filme) else "filme",
        ]))
    return filme["texto_pesquisavel"]


def filme_combina_com_texto(filme, pesquisa):
    """TODAS as palavras precisam aparecer: 'nolan 2010' acha A Origem."""
    palavras = normalizar_texto(pesquisa).split()
    texto = texto_pesquisavel(filme)
    return all(palavra in texto for palavra in palavras)


def chave_de_ordem(ordem, perfil_atual=None):
    """Função de ordenação para cada opção do menu "Ordem"."""
    # Filmes sem a informação vão para o fim (por isso as tuplas com "tem valor").
    if ordem == "Crítica (Rotten)":
        return lambda f: (nota_da_critica(f) is not None, nota_da_critica(f) or 0, popularidade(f))
    if ordem == "Público (IMDb)":
        return lambda f: (bool(f.get("nota_imdb")), f.get("nota_imdb") or 0, popularidade(f))
    if ordem == "Mais recentes":
        return lambda f: (f.get("ano") or 0, popularidade(f))
    if ordem == "Combina comigo" and perfil_atual is not None and perfil_atual["suficiente"]:
        return lambda f: perfil.pontuar_filme(f, perfil_atual)[0]
    return lambda f: popularidade(f)  # "Mais populares" (e "Combina comigo" sem perfil)


def filtrar_catalogo(texto="", genero=TODOS, decada=TODOS, nota_minima=None,
                     ordem="Mais populares", esconder_assistidos=False, tipo=None):
    """
    Busca avançada do Catálogo: aplica todos os filtros juntos e ordena.

    tipo        -> "filme", "serie" ou None (os dois)
    texto       -> nome, ano, gênero, diretor ou ator (todas as palavras)
    genero      -> "Comédia" (ou "Todos")
    decada      -> "Anos 2010", "Antes de 1980" (ou "Todos")
    nota_minima -> 90 = Rotten (crítica) 90%+ (ou None)
    """
    resultado = filtrar_por_tipo(filmes, tipo)

    if texto.strip():
        resultado = [f for f in resultado if filme_combina_com_texto(f, texto)]

    if genero and genero != TODOS:
        genero_normalizado = " ".join(extrair_palavras(genero))
        resultado = [f for f in resultado if filme_tem_genero(f, genero_normalizado)]

    if decada and decada != TODOS:
        resultado = [f for f in resultado if decada_do_filme(f) == decada]

    if nota_minima is not None:
        resultado = [
            f for f in resultado
            if nota_da_critica(f) is not None and nota_da_critica(f) >= nota_minima
        ]

    if esconder_assistidos:
        chaves_vistas = usuario.chaves_assistidas()
        resultado = [f for f in resultado if usuario.chave_filme(f) not in chaves_vistas]

    # ---------- ordem ----------
    if ordem == "Mais antigos":
        resultado.sort(key=lambda f: (f.get("ano") or 9999, -popularidade(f)))
    elif ordem == "Mais curtos":
        # Série conta o tempo para ver tudo: The Office (201 × 22min) não é "curta".
        resultado.sort(key=lambda f: (tempo_total_em_minutos(f) is None, tempo_total_em_minutos(f) or 0))
    elif ordem == "A–Z":
        resultado.sort(key=lambda f: normalizar_texto(f["nome"]))
    else:
        perfil_atual = perfil.calcular_perfil(filmes) if ordem == "Combina comigo" else None
        resultado.sort(key=chave_de_ordem(ordem, perfil_atual), reverse=True)

    return resultado


# =========================================================
# FORA DO ESCOPO ("Qual é a capital do Japão?")
# =========================================================
MENSAGEM_FORA_DO_ESCOPO = (
    "🎬 Eu só entendo de filmes! Posso recomendar algo, responder sobre o "
    "filme da nossa conversa ou falar das suas notas e favoritos.\n\n"
    'Experimente: "Me recomenda algo" ou "Quero uma comédia bem avaliada".'
)

PALAVRAS_DE_CINEMA = {
    "filme", "filmes", "cinema", "assistir", "ver", "vi", "assisti", "ator", "atriz",
    "atores", "elenco", "diretor", "diretora", "direcao", "genero", "sinopse",
    "personagem", "personagens", "cena", "cenas", "final", "vilao", "heroi",
    "protagonista", "roteiro", "trilha", "sequencia", "franquia", "nota", "notas",
    "estrela", "estrelas", "oscar", "premio", "premios", "serie", "animacao",
    "series", "seriado", "seriados", "temporada", "temporadas", "episodio", "episodios"
}

INICIOS_DE_PERGUNTA = (
    "qual", "quais", "quem", "quando", "onde", "como", "por que", "porque",
    "o que", "quanto", "quantos", "quantas", "voce sabe", "me explica", "me diz"
)


PALAVRAS_DE_CINEMA_EXTRAS = {
    "dirigiu", "dirigido", "lancado", "lancamento", "dura", "duracao",
    "termina", "acaba", "comeca", "acontece", "historia", "enredo", "spoiler"
}


def parece_fora_do_escopo(cliente, filme_da_conversa=None):
    """
    Pergunta que não fala de cinema e não cita nenhum filme, gênero, ator,
    diretor ou ano do catálogo: "Qual é a capital do Japão?", "Quanto é 2+2?".

    Se existe um filme na conversa, perguntas que usam palavras da sinopse
    dele ("Por que o Woody tem ciúmes?") NÃO são fora do escopo.
    """
    texto_normalizado = " ".join(extrair_palavras(cliente))
    palavras = set(texto_normalizado.split())

    eh_pergunta = "?" in cliente or texto_normalizado.startswith(INICIOS_DE_PERGUNTA)
    if not eh_pergunta:
        return False

    if palavras & (PALAVRAS_DE_CINEMA | PALAVRAS_DE_CINEMA_EXTRAS | PALAVRAS_DE_DETALHE):
        return False

    if filme_da_conversa is not None:
        if palavras & PALAVRAS_SOBRE_FILME_ATUAL:
            return False  # "ele", "esse"... fala do filme atual
        if raizes_importantes(cliente) & filme_da_conversa["raizes_texto"]:
            return False  # usa palavras da sinopse (nomes de personagens etc.)

    diretor, ator = detectar_diretor_e_ator(cliente)
    if diretor or ator or detectar_genero(cliente) or detectar_ano(cliente):
        return False

    if encontrar_filme_citado(cliente) is not None:
        return False

    return True


# =========================================================
# MEMÓRIA DA CONVERSA
# =========================================================
filme_atual = None
pedido_anterior = None
candidatos_anteriores = None
filmes_recomendados = []
qualidade_pedida = None   # "critica", "publico", "geral", "classico" ou None
busca_usou_perfil = False  # a última busca foi ordenada pelo seu gosto?
contexto_relativo = None   # (tipo, filme_referencia) do último "parecido com esse"
historico_recomendacoes = []  # TODOS os filmes recomendados nesta conversa, em ordem
ultima_busca_semantica = None  # assunto entendido na última busca (para explicar)
tipo_da_conversa = None        # "serie"/"filme" pedido por último (vale até você mudar)


def reiniciar_conversa():
    """Esquece tudo da conversa atual (usado em "Nova conversa" e nos testes)."""
    global filme_atual, pedido_anterior, candidatos_anteriores
    global filmes_recomendados, qualidade_pedida, busca_usou_perfil, contexto_relativo
    global historico_recomendacoes, ultima_busca_semantica, tipo_da_conversa

    filme_atual = None
    pedido_anterior = None
    candidatos_anteriores = None
    filmes_recomendados = []
    qualidade_pedida = None
    busca_usou_perfil = False
    contexto_relativo = None
    historico_recomendacoes = []
    ultima_busca_semantica = None
    tipo_da_conversa = None


def restaurar_contexto(chaves_filmes_recomendados):
    """
    Ao reabrir uma conversa salva: o último filme recomendado volta a ser
    o "filme atual", para "Quem dirigiu ele?" continuar funcionando.
    """
    global filme_atual, filmes_recomendados, historico_recomendacoes

    reiniciar_conversa()
    filmes_por_chave = {usuario.chave_filme(filme): filme for filme in filmes}

    filmes_da_conversa = [
        filmes_por_chave[chave]
        for chave in chaves_filmes_recomendados
        if chave in filmes_por_chave
    ]

    # Sem repetir: o mesmo filme pode aparecer em várias mensagens (perguntas sobre ele).
    for filme in filmes_da_conversa:
        if filme not in historico_recomendacoes:
            historico_recomendacoes.append(filme)

    filmes_recomendados = list(historico_recomendacoes)

    if filmes_da_conversa:
        filme_atual = filmes_da_conversa[-1]


def criar_resultado(texto, tipo="mensagem", filme=None, atualizou_usuario=False):
    """
    atualizou_usuario=True avisa a interface que favoritos/assistidos/notas
    mudaram (ex.: "já vi esse" marca como assistido E recomenda outro).
    """
    return {
        "texto": texto,
        "tipo": tipo,
        "filme": filme,
        "atualizou_usuario": atualizou_usuario or tipo == "usuario_atualizado"
    }


def registrar_recomendacao(filme):
    """Guarda o filme na lista da busca atual e no histórico da conversa."""
    if filme not in filmes_recomendados:
        filmes_recomendados.append(filme)
    if filme not in historico_recomendacoes:
        historico_recomendacoes.append(filme)


# =========================================================
# FRASES CURTAS DO CHAT
# =========================================================
PALAVRAS_DE_REJEICAO = {"nao", "nem", "pula", "pular", "passa", "passar", "proximo", "proxima"}
PALAVRAS_EXTRAS_DE_REJEICAO = {"pula", "pular", "passa", "passar", "nem", "pensar", "quero", "rola"}


def eh_rejeicao(cliente):
    """
    "Esse não", "Não gostei desse", "Pula", "Nem pensar" -> True.
    Só vale se a frase não traz assunto novo ("Não quero terror" é busca nova).
    """
    palavras = extrair_palavras(cliente)
    if not palavras or not (set(palavras) & PALAVRAS_DE_REJEICAO):
        return False

    permitidas = PALAVRAS_DE_PREENCHIMENTO | PALAVRAS_EXTRAS_DE_REJEICAO | PALAVRAS_DE_REJEICAO
    return all(palavra in permitidas for palavra in palavras)


PALAVRAS_DE_JA_VISTO = {"vi", "assisti", "visto", "assistido", "conheco", "vimos"}
PALAVRAS_PERMITIDAS_JA_VISTO = PALAVRAS_DE_JA_VISTO | {
    "ja", "eu", "esse", "este", "essa", "ele", "isso", "filme", "tambem", "faz",
    "tempo", "ano", "anos", "quero", "outro", "outra", "um", "uma", "me", "manda",
    "mostra", "recomenda", "entao", "ai", "mas", "e", "o", "a", "de", "desse"
}


def eh_ja_vi_esse(cliente):
    """"Já vi esse", "Esse eu já assisti", "Já vi, quero outro" -> True."""
    palavras = extrair_palavras(cliente)
    if "ja" not in palavras or not (set(palavras) & PALAVRAS_DE_JA_VISTO):
        return False
    return all(palavra in PALAVRAS_PERMITIDAS_JA_VISTO for palavra in palavras)


# ---------------- Histórico: "qual foi o primeiro?" ----------------
RAIZES_DE_RECOMENDAR = ("recomend", "indic", "sugeri", "sugest", "mostr", "mand", "fal", "pass")
PALAVRAS_PERMITIDAS_ANTERIOR = {
    "o", "a", "anterior", "volta", "voltar", "volte", "pro", "para", "pra", "ao",
    "de", "antes", "filme", "quero", "me", "mostra", "aquele", "aquela", "outro",
    "mesmo", "esse", "e", "eh", "qual", "era", "foi", "mesmo", "do"
}


def detectar_pedido_de_historico(cliente):
    """
    "Qual foi o primeiro que você recomendou?" -> "primeiro"
    "O anterior" / "Volta pro anterior"         -> "anterior"
    "Quais você já recomendou?"                 -> "lista"
    """
    palavras = extrair_palavras(cliente)
    conjunto = set(palavras)
    fala_de_recomendar = any(
        palavra.startswith(RAIZES_DE_RECOMENDAR) for palavra in palavras
    ) or "voce" in conjunto or "vc" in conjunto

    if "anterior" in conjunto and all(palavra in PALAVRAS_PERMITIDAS_ANTERIOR for palavra in palavras):
        return "anterior"

    if conjunto & {"primeiro", "primeira"} and fala_de_recomendar:
        return "primeiro"

    if "anterior" in conjunto and fala_de_recomendar:
        return "anterior"

    if conjunto & {"quais", "lista", "todos", "listar"} and any(
        palavra.startswith(("recomend", "indic", "sugeri")) for palavra in palavras
    ):
        return "lista"

    return None


def responder_historico(tipo):
    global filme_atual, contexto_relativo

    if not historico_recomendacoes:
        return criar_resultado(
            "Ainda não recomendei nenhum filme nesta conversa. 🎬 "
            'Peça um, por exemplo: "Me recomenda algo".'
        )

    if tipo == "lista":
        linhas = [
            f"{posicao}. {descrever_filme_curto(filme)}"
            for posicao, filme in enumerate(historico_recomendacoes, start=1)
        ]
        return criar_resultado(
            "🎞️ Filmes que eu já recomendei nesta conversa:\n\n" + "\n".join(linhas)
        )

    if tipo == "primeiro":
        escolhido = historico_recomendacoes[0]
        introducao = "🎞️ O primeiro que eu recomendei foi este:"
    else:
        if len(historico_recomendacoes) < 2:
            return criar_resultado(
                f'Só recomendei um filme até agora: {historico_recomendacoes[0]["nome"]}.',
                filme=historico_recomendacoes[0]
            )
        posicao_atual = (
            historico_recomendacoes.index(filme_atual)
            if filme_atual in historico_recomendacoes
            else len(historico_recomendacoes) - 1
        )
        if posicao_atual == 0:
            return criar_resultado(
                f'{historico_recomendacoes[0]["nome"]} já é o primeiro que eu recomendei. 🎞️',
                filme=historico_recomendacoes[0]
            )
        escolhido = historico_recomendacoes[posicao_atual - 1]
        introducao = "⏪ Voltando ao anterior:"

    # Ele volta a ser o filme da conversa: "Quem dirigiu ele?" passa a falar dele.
    filme_atual = escolhido
    contexto_relativo = None

    return criar_resultado(
        introducao + "\n\n" + gerar_resposta(escolhido),
        tipo="recomendacao",
        filme=escolhido
    )


def texto_da_recomendacao(filme, usou_perfil, aviso_perfil_pequeno=False, generos_ignorados=()):
    """Recomendação + (se usou o seu gosto) o porquê."""
    texto = gerar_resposta(filme, qualidade_pedida)

    if aviso_perfil_pequeno:
        texto = (
            "Ainda estou te conhecendo 🙂 Dê estrelas a alguns filmes que você já viu "
            "para eu acertar o seu gosto. Por enquanto, uma escolha popular:\n\n"
            + texto
        )

    if usou_perfil:
        explicacao = perfil.explicar_recomendacao(
            filme, perfil.calcular_perfil(filmes), generos_ignorados
        )
        if explicacao:
            texto += f"\n\n{explicacao}"

    return texto


PALAVRAS_PERMITIDAS_COM_TITULO = (
    PALAVRAS_DE_PREENCHIMENTO | PALAVRAS_GENERICAS_DE_PEDIDO | PALAVRAS_DE_SERIE
    | PALAVRAS_DE_FILME | {
        "rever", "fala", "fale", "falar", "conta", "conte", "contar", "sobre", "mais",
        "detalhes", "saber", "info", "informacoes", "achar", "acha", "procura", "procure",
        "pesquisa", "pesquise", "abre", "abra", "abrir", "o", "a", "os", "as"
    }
)


def titulo_pedido_diretamente(cliente):
    """
    "O Mentalista", "Quero a série O Mentalista", "Me fala de Interestelar"
    -> o título citado. Se a frase tiver mais assunto ("um filme como Shrek
    mas com dragões"), não é pedido direto: devolve None.
    """
    citado = encontrar_filme_citado(cliente)
    if citado is None:
        return None

    palavras_do_titulo = set()
    for titulo in citado.get("titulos_busca", set()) | {
        " ".join(extrair_palavras(curto)) for curto in citado.get("titulos_curtos", set())
    }:
        palavras_do_titulo.update(titulo.split())

    sobrando = [
        palavra for palavra in extrair_palavras(cliente)
        if palavra not in palavras_do_titulo and palavra not in PALAVRAS_PERMITIDAS_COM_TITULO
    ]
    if sobrando:
        return None

    # "Quero uma série O Mentalista" pediu série: se o título for de filme, não força.
    tipo = detectar_tipo(cliente)
    if tipo is not None and tipo_do_item(citado) != tipo:
        return None
    return citado


def mostrar_titulo_pedido(filme):
    """Mostra o título pedido pelo nome; "quero outro" depois traz os parecidos com ele."""
    global filme_atual, pedido_anterior, candidatos_anteriores, filmes_recomendados
    global qualidade_pedida, busca_usou_perfil, contexto_relativo, ultima_busca_semantica

    parecidos = [
        outro for outro in filtrar_por_tipo(filmes, tipo_do_item(filme))
        if usuario.chave_filme(outro) != usuario.chave_filme(filme)
    ]
    parecidos, _ = remover_assistidos(parecidos, "")

    filmes_recomendados = []
    pedido_anterior = filme["nome"]
    candidatos_anteriores = ordenar_por_semelhanca(filme, parecidos)
    qualidade_pedida = None
    busca_usou_perfil = False
    contexto_relativo = ("parecido", filme)
    ultima_busca_semantica = None

    filme_atual = filme
    registrar_recomendacao(filme)

    texto = "🎯 Achei pelo título:\n\n" + gerar_resposta(filme)
    texto += '\n\n💬 Quer um parecido? É só pedir "quero outro".'
    return criar_resultado(texto, tipo="recomendacao", filme=filme)


MAXIMO_TITULOS_NO_AVISO = 5


def texto_ja_assistidos(quantidade_pulada):
    """
    "Você já assistiu a O Mentalista (série), o único título que encontrei..."
    "Você já assistiu aos 8 títulos que encontrei: Interestelar, A Origem, ..."
    """
    vistos = list(ultimos_assistidos_pulados)

    if quantidade_pulada == 1 and len(vistos) == 1:
        visto = vistos[0]
        tipo = "série" if eh_serie(visto) else "filme"
        return (
            f"Você já assistiu a {visto['nome']} ({tipo}), o único título que encontrei "
            "com esses critérios. ✅\n\n"
            f'Quer rever? É só me dizer o nome: "{visto["nome"]}". '
            "Ou tente outra busca."
        )

    nomes = ", ".join(filme["nome"] for filme in vistos[:MAXIMO_TITULOS_NO_AVISO])
    if len(vistos) > MAXIMO_TITULOS_NO_AVISO:
        nomes += "…"
    lista = f": {nomes}" if nomes else ""
    return (
        f"Você já assistiu aos {quantidade_pulada} títulos que encontrei com esses critérios{lista}. ✅\n\n"
        "Quer tentar outra busca? Se quiser rever algum, é só me dizer o nome dele."
    )


def recomendar_outro_da_busca(introducao=""):
    """
    Próximo filme da última busca ("Quero outro", "Esse não", "Já vi esse").
    Devolve o resultado pronto ou None se acabaram as opções.
    """
    global filme_atual

    if candidatos_anteriores is not None:
        resultado = buscar_outro_filme(candidatos_anteriores, filmes_recomendados, pedido_anterior)
    elif pedido_anterior is not None:
        resultado = buscar_outro_semantico(pedido_anterior, filmes_recomendados)
    else:
        resultado = None

    if resultado is None:
        return None

    filme_atual = resultado
    registrar_recomendacao(resultado)

    generos_ignorados = []
    if contexto_relativo is not None:
        generos_ignorados = generos_contrarios(filme_atual, contexto_relativo[0])

    texto = texto_da_recomendacao(
        filme_atual, busca_usou_perfil, generos_ignorados=generos_ignorados
    )

    if contexto_relativo is not None:
        tipo_relativo, filme_referencia = contexto_relativo
        texto += "\n\n" + explicar_relativo(tipo_relativo, filme_referencia, filme_atual)
    elif not busca_usou_perfil and pedido_anterior:
        explicacao = explicar_busca(pedido_anterior, filme_atual, ultima_busca_semantica)
        if explicacao:
            texto += "\n\n" + explicacao

    if introducao:
        texto = introducao + "\n\n" + texto

    return criar_resultado(texto, tipo="recomendacao", filme=filme_atual)


def recomendar_por_leveza(cliente, leve):
    """"Quero algo leve" / "algo tenso" sem filme na conversa."""
    global filme_atual, pedido_anterior, candidatos_anteriores, filmes_recomendados
    global qualidade_pedida, busca_usou_perfil, contexto_relativo, ultima_busca_semantica

    base, _ = remover_assistidos(
        filtrar_por_tipo(filmes_mais_leves_ou_pesados(leve), detectar_tipo(cliente)), cliente
    )
    if not base:
        return criar_resultado(
            "Não encontrei um filme assim que você ainda não tenha visto.",
            tipo="sem_resultado"
        )

    perfil_atual = perfil.calcular_perfil(filmes)
    usou_perfil = perfil_atual["suficiente"]
    ordenados = ordenar_por_leveza(base, perfil_atual, leve)
    rastro.etapa(
        "☀️" if leve else "🌑", "Leveza dos gêneros",
        f"{len(base)} filmes {'leves' if leve else 'tensos'} • ordem = seu gosto "
        f"+ {PESO_LEVEZA_NA_ORDEM} × leveza • 1º: {ordenados[0]['nome']} "
        f"(leveza {leveza(ordenados[0]):+.2f})"
    )

    tipo = "mais_leve" if leve else "mais_pesado"
    pedido_anterior = cliente
    candidatos_anteriores = ordenados
    qualidade_pedida = None
    busca_usou_perfil = usou_perfil
    contexto_relativo = (tipo, None)
    ultima_busca_semantica = None
    filmes_recomendados = []

    filme_atual = ordenados[0]
    registrar_recomendacao(filme_atual)

    texto = texto_da_recomendacao(
        filme_atual, usou_perfil, generos_ignorados=generos_contrarios(filme_atual, tipo)
    )
    texto += "\n\n" + explicar_relativo(tipo, None, filme_atual)
    return criar_resultado(texto, tipo="recomendacao", filme=filme_atual)


def marcar_atual_como_assistido():
    """"Já vi esse": marca o filme atual e recomenda o próximo da mesma busca."""
    filme_visto = filme_atual
    if not usuario.foi_assistido(filme_visto):
        usuario.alternar_assistido(filme_visto)

    aviso = f'✅ Anotei: você já viu {filme_visto["nome"]}. Ele não volta mais nas sugestões.'

    resultado = recomendar_outro_da_busca(aviso + " Que tal este?")
    if resultado is None:
        return criar_resultado(
            aviso + "\n\nEsses eram todos os filmes dessa busca. "
            "Me conte o que mais você quer ver!",
            tipo="usuario_atualizado"
        )

    resultado["atualizou_usuario"] = True
    return resultado


# =========================================================
# PROCESSAR MENSAGEM
# =========================================================
def processar_mensagem(cliente):
    """Responde a mensagem e grava o caminho percorrido (Painel do RAG)."""
    rastro.iniciar(cliente.strip())
    try:
        resultado = responder_mensagem(cliente)
    except Exception as erro:
        rastro.finalizar(erro=erro)
        raise
    resultado["rastro"] = rastro.finalizar(resultado)
    return resultado


def rota(descricao):
    """Etapa que diz qual caminho do processar_mensagem a mensagem seguiu."""
    rastro.etapa("🛤", "Rota", descricao)


def responder_mensagem(cliente):

    global filme_atual
    global pedido_anterior
    global candidatos_anteriores
    global filmes_recomendados
    global qualidade_pedida
    global busca_usou_perfil
    global contexto_relativo

    cliente = cliente.strip()

    if cliente == "":
        return criar_resultado("Digite alguma coisa para eu poder ajudar.")

    # ---------------- Saudação ----------------
    if eh_saudacao(cliente):
        rota("saudação (regra: só palavras de cumprimento)")
        return criar_resultado(
            "Olá! 🎬 Me conte que tipo de filme você quer ver. "
            "Pode ser um gênero, um ator, um diretor, um ano "
            "ou o assunto da história."
        )

    # ---------------- Histórico: "qual foi o primeiro?", "o anterior" ----------------
    tipo_historico = detectar_pedido_de_historico(cliente)
    if tipo_historico is not None:
        rota(f"histórico da conversa ({tipo_historico})")
        return responder_historico(tipo_historico)

    # ---------------- Comparar: "Interestelar ou Matrix?" ----------------
    dupla = detectar_comparacao(cliente)
    if dupla is not None:
        rota(f'comparação: {dupla[0]["nome"]} × {dupla[1]["nome"]}')
        comparacao = comparar_filmes(*dupla)
        rastro.etapa(
            "⚖️", "Comparação",
            "\n".join(comparacao["veredictos"] + [f"semelhança da história: {comparacao['semelhanca']}%"])
        )
        resultado = criar_resultado(texto_da_comparacao(comparacao), tipo="comparacao")
        resultado["comparacao"] = comparacao
        return resultado

    # ---------------- "Já vi esse" ----------------
    if filme_atual is not None and eh_ja_vi_esse(cliente):
        rota(f'"já vi esse": marca {filme_atual["nome"]} como assistido e pega o próximo')
        return marcar_atual_como_assistido()

    # ---------------- Sobre você (notas, favoritos, assistidos) ----------------
    resposta_pessoal = responder_sobre_usuario(cliente)
    if resposta_pessoal is not None:
        rota("sobre você: notas, favoritos, assistidos ou perfil")
        return resposta_pessoal

    # ---------------- Fora do escopo ----------------
    if parece_fora_do_escopo(cliente, filme_atual):
        rota("fora do escopo (regra: pergunta sem nada de cinema)")
        return criar_resultado(MENSAGEM_FORA_DO_ESCOPO, tipo="fora_do_escopo")

    # ---------------- Quero outro / Esse não ----------------
    if filme_atual is not None and (eh_pedido_de_outro_filme(cliente) or eh_rejeicao(cliente)):
        rota('"quero outro" / "esse não": próximo da lista da busca anterior')

        resultado = recomendar_outro_da_busca()

        if resultado is None:
            return criar_resultado(
                f'Não encontrei outro filme parecido com {filme_atual["nome"]} '
                "dentro desses critérios.\n\n"
                "Que tal descrever uma nova busca? Por exemplo, "
                "um gênero, um ano, um ator ou o assunto do filme."
            )

        return resultado

    # ---------------- Pelo título: "O Mentalista" ----------------
    titulo_direto = titulo_pedido_diretamente(cliente)
    # Vale também quando o título já é o da conversa ("o mentalista" logo depois
    # de recomendar O Mentalista): mostra ele de novo em vez de virar busca por assunto.
    if titulo_direto is not None:
        rota(f'pedido pelo título: {titulo_direto["nome"]}')
        return mostrar_titulo_pedido(titulo_direto)

    # ---------------- Filme ou série? ----------------
    # Sem dizer o tipo, continua o da conversa: depois de "uma série de comédia",
    # "quero uma dos anos 2000" ainda é série.
    global tipo_da_conversa
    tipo_explicito = detectar_tipo(cliente)
    if pede_os_dois_tipos(cliente):
        tipo_da_conversa = None
    elif tipo_explicito is not None:
        tipo_da_conversa = tipo_explicito

    cliente_com_tipo = cliente
    tipo_herdado = False
    if tipo_explicito is None and not pede_os_dois_tipos(cliente) and tipo_da_conversa is not None:
        cliente_com_tipo = f"{cliente} ({'série' if tipo_da_conversa == TIPO_SERIE else 'filme'})"
        tipo_herdado = True

    # ---------------- Parecido com esse / mais recente / mesmo diretor ----------------
    tipo_relativo = detectar_pedido_relativo(cliente)

    if tipo_relativo is not None:
        rota(f"pedido relativo: {tipo_relativo}")
        filme_citado = encontrar_filme_citado(cliente)
        filme_referencia = filme_citado or filme_atual

        # "Quero algo leve" (sem "mais"/"menos" e sem citar filme) não compara com ninguém.
        if tipo_relativo in ("mais_leve", "mais_pesado"):
            comparativo = bool(set(extrair_palavras(cliente)) & {"mais", "menos"})
            if filme_referencia is None or (filme_citado is None and not comparativo):
                return recomendar_por_leveza(cliente_com_tipo, leve=(tipo_relativo == "mais_leve"))

        if filme_referencia is None:
            return criar_resultado(
                "Com base em qual filme? Me diga o nome, por exemplo: "
                '"Um filme parecido com Shrek", ou peça uma recomendação primeiro.'
            )

        # "um mais recente" depois de "um filme do Nolan" continua entre os do Nolan
        tipos_que_mantem_criterios = ("mais_recente", "mais_antigo", "mais_curto", "mais_longo")
        if tipo_relativo in tipos_que_mantem_criterios and candidatos_anteriores:
            base = filtrar_relativo(tipo_relativo, filme_referencia, candidatos_anteriores)
        else:
            base = []

        if not base:
            base = filtrar_relativo(tipo_relativo, filme_referencia, filmes)

        # "Parecido com Breaking Bad" traz séries; "um FILME parecido com Breaking Bad", filmes.
        tipo_desejado = detectar_tipo(cliente) or tipo_do_item(filme_referencia)
        base = filtrar_por_tipo(base, tipo_desejado)

        chaves_ignoradas = {usuario.chave_filme(filme) for filme in filmes_recomendados}
        chaves_ignoradas.add(usuario.chave_filme(filme_referencia))
        base = [filme for filme in base if usuario.chave_filme(filme) not in chaves_ignoradas]
        base, _ = remover_assistidos(base, cliente)

        if not base:
            return criar_resultado(
                MENSAGEM_SEM_RELATIVO[tipo_relativo].format(nome=filme_referencia["nome"]),
                tipo="sem_resultado"
            )

        ordenados = ordenar_por_semelhanca(filme_referencia, base)
        rastro.tabela(
            "🔗", f"Semelhança com {filme_referencia['nome']}",
            ["semelhança"],
            [
                (filme["nome"], [f"{semelhanca_entre_filmes(filme_referencia, filme):.3f}"],
                 max(semelhanca_entre_filmes(filme_referencia, filme), 0))
                for filme in ordenados[:5]
            ],
            detalhe=(
                f"{len(base)} candidatos • semelhança = cosseno das sinopses "
                f"+ {PESO_GENERO_NA_SEMELHANCA} × gêneros em comum"
            )
        )

        pedido_anterior = cliente
        candidatos_anteriores = ordenados
        qualidade_pedida = None
        busca_usou_perfil = False
        contexto_relativo = (tipo_relativo, filme_referencia)

        if filme_referencia not in filmes_recomendados:
            filmes_recomendados.append(filme_referencia)

        filme_atual = ordenados[0]
        registrar_recomendacao(filme_atual)

        texto = (
            gerar_resposta(filme_atual)
            + "\n\n"
            + explicar_relativo(tipo_relativo, filme_referencia, filme_atual)
        )
        return criar_resultado(texto, tipo="recomendacao", filme=filme_atual)

    pedido_personalizado = eh_pedido_personalizado(cliente)

    # ---------------- Pergunta sobre o filme atual ----------------
    intencao = None
    if filme_atual is not None and not pedido_personalizado:
        intencao = identificar_intencao(cliente, filme_atual)

    if intencao == "FORA":
        return criar_resultado(MENSAGEM_FORA_DO_ESCOPO, tipo="fora_do_escopo")

    if intencao == "PERGUNTA":
        rota(f'pergunta sobre {filme_atual["nome"]}')
        return criar_resultado(
            responder_sobre_filme(filme_atual, cliente),
            tipo="pergunta",
            filme=filme_atual
        )

    # ---------------- Nova busca ----------------
    rota("nova busca personalizada (o seu gosto decide)" if pedido_personalizado else "nova busca")
    if tipo_herdado:
        rastro.etapa("📺", "Tipo da conversa",
                     f"você não disse filme ou série: continuei com {tipo_da_conversa}")
    contexto_relativo = None
    pedido_anterior = cliente_com_tipo
    qualidade_pedida = detectar_qualidade(cliente)
    filmes_recomendados = []

    perfil_atual = perfil.calcular_perfil(filmes)

    resultado, candidatos_anteriores, quantidade_pulada, busca_usou_perfil = buscar_filme(
        cliente_com_tipo, perfil_atual, pedido_personalizado
    )

    # Herdou "série", mas não existe série assim ("algo com DiCaprio"): tenta os dois.
    if resultado is None and quantidade_pulada == 0 and tipo_herdado:
        rastro.etapa("📺", "Tipo da conversa", "nada com esse tipo: tentei filmes e séries")
        cliente_com_tipo = cliente
        pedido_anterior = cliente
        resultado, candidatos_anteriores, quantidade_pulada, busca_usou_perfil = buscar_filme(
            cliente, perfil_atual, pedido_personalizado
        )

    if resultado is None:
        if quantidade_pulada > 0:
            return criar_resultado(texto_ja_assistidos(quantidade_pulada), tipo="sem_resultado")

        return criar_resultado(
            "Nenhum filme adequado foi encontrado para esses critérios.",
            tipo="sem_resultado"
        )

    filme_atual = resultado
    registrar_recomendacao(resultado)

    texto = texto_da_recomendacao(
        filme_atual,
        busca_usou_perfil,
        aviso_perfil_pequeno=pedido_personalizado and not perfil_atual["suficiente"]
    )

    if not busca_usou_perfil and not pedido_personalizado:
        explicacao = explicar_busca(cliente_com_tipo, filme_atual, ultima_busca_semantica)
        if explicacao:
            texto += "\n\n" + explicacao

    return criar_resultado(texto, tipo="recomendacao", filme=filme_atual)


# =========================================================
# TERMINAL
# =========================================================
if __name__ == "__main__":

    while True:
        cliente = input("O que você gostaria de assistir? ").strip()

        if cliente.lower() == "sair":
            print("Até mais cinéfilo!")
            break

        resposta = processar_mensagem(cliente)
        print(resposta["texto"])