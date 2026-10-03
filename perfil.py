"""
Perfil de preferências do CineAI: aprende o seu gosto a partir de
favoritos, filmes assistidos e estrelas, e pontua os filmes que você ainda não viu.

Tipo de sistema: FILTRAGEM BASEADA EM CONTEÚDO.
Recomendamos pelo conteúdo (gêneros, diretores, atores, sinopse) dos filmes
que VOCÊ curtiu. (A alternativa clássica, a filtragem colaborativa, usa
"quem gostou disso também gostou daquilo" e precisa de muitos usuários.)

Passo a passo:
  1. Cada filme que você marcou vira um SINAL (positivo ou negativo).
  2. O sinal é repassado para os gêneros, diretores e atores do filme.
  3. Cada característica ganha uma AFINIDADE = soma dos sinais / √(quantidade + SUAVIZACAO).
  4. As sinopses dos filmes marcados viram um VETOR DE GOSTO (média ponderada).
  5. Cada filme não assistido recebe uma pontuação combinando tudo isso.

Este módulo não sabe nada de interface nem de chat.
"""

import math
import unicodedata

import numpy as np

import usuario


# =========================================================
# PESOS (mude à vontade para experimentar)
# =========================================================
# 1) Quanto cada ação vale como sinal
PESO_POR_NOTA = {5: 2.0, 4: 1.0, 3: 0.0, 2: -1.0, 1: -2.0}
SINAL_FAVORITO = 1.5             # soma com a nota
SINAL_ASSISTIDO_SEM_NOTA = 0.5

# 2) Suavização: cada característica começa com este número de filmes
#    "neutros" imaginários. Assim UM filme de terror com 5★ não faz de
#    Terror o seu gênero favorito; só vários filmes fazem.
#
#    afinidade = soma dos sinais / √(quantidade + SUAVIZACAO)
#
#    Por que a raiz quadrada? Com uma média simples (soma / quantidade), dar 4★
#    para mais uma animação DIMINUÍA a afinidade com Animação se as outras
#    tinham 5★. Avaliar bem mais um filme do gênero nunca deveria diminuir o
#    seu gosto por ele. Com a raiz, a confiança cresce com a quantidade de
#    filmes e um sinal positivo praticamente sempre soma. (O testes.py pegou isso.)
SUAVIZACAO = 2.0

# 3) Quantos atores do elenco principal entram no perfil
MAXIMO_ATORES_PERFIL = 3

# 4) Peso de cada parte na pontuação final de um filme
PESO_GENEROS = 0.45
PESO_DIRETORES = 0.15
PESO_ATORES = 0.10
PESO_GOSTO = 0.30          # parecido com as histórias que você curtiu
PESO_POPULARIDADE = 0.10   # pequeno empurrão para filmes conhecidos
PESO_QUALIDADE = 0.15      # empurrão para filmes bem avaliados

# 5) Escalas para deixar cada parte entre -1 e 1
ESCALA_AFINIDADE = 3.0
ESCALA_GOSTO = 2.0

# 6) Mínimo de filmes com sinal para o perfil valer
MINIMO_FILMES_PARA_PERFIL = 3

# 7) Nas buscas normais ("uma comédia"), quanto o gosto pesa no desempate
PESO_DESEMPATE = 0.5


# =========================================================
# AUXILIARES
# =========================================================
def limitar(valor, minimo=-1.0, maximo=1.0):
    return max(minimo, min(maximo, valor))


def normalizar_chave(texto):
    """'Ficção científica' -> 'ficcao cientifica' (para comparar sem acento)."""
    texto = unicodedata.normalize("NFD", str(texto).strip().lower())
    return "".join(caractere for caractere in texto if unicodedata.category(caractere) != "Mn")


def separar_por_virgula(texto):
    return [parte.strip() for parte in str(texto).split(",") if parte.strip()]


def generos_do_filme(filme):
    return separar_por_virgula(filme.get("genero", ""))


def diretores_do_filme(filme):
    return separar_por_virgula(filme.get("diretor", ""))


def atores_principais(filme):
    return list(filme.get("elenco", []))[:MAXIMO_ATORES_PERFIL]


# =========================================================
# 1) SINAIS
# =========================================================
def sinal_do_filme(filme):
    """Quanto este filme diz sobre o seu gosto (positivo = gostou)."""
    nota = usuario.obter_nota(filme)

    if nota is not None:
        sinal = PESO_POR_NOTA[nota]
    elif usuario.foi_assistido(filme):
        sinal = SINAL_ASSISTIDO_SEM_NOTA
    else:
        sinal = 0.0

    if usuario.eh_favorito(filme):
        sinal += SINAL_FAVORITO

    return sinal


def descrever_sinal(filme):
    """Como o filme aparece nas explicações: 'Shrek (5★)', 'Toy Story (❤️)'."""
    nota = usuario.obter_nota(filme)
    if nota is not None:
        return f'{filme["nome"]} ({nota}★)'
    if usuario.eh_favorito(filme):
        return f'{filme["nome"]} (❤️)'
    return filme["nome"]


# =========================================================
# 2) e 3) AFINIDADES
# =========================================================
def acumular(acumulador, nome_exibicao, sinal, filme):
    chave = normalizar_chave(nome_exibicao)
    item = acumulador.setdefault(
        chave,
        {"nome": nome_exibicao, "soma": 0.0, "quantidade": 0, "filmes": []}
    )
    item["soma"] += sinal
    item["quantidade"] += 1
    item["filmes"].append((sinal, filme))


def calcular_afinidades(acumulador):
    for item in acumulador.values():
        item["afinidade"] = item["soma"] / math.sqrt(item["quantidade"] + SUAVIZACAO)
        # Filmes que mais contribuíram primeiro (para as explicações)
        item["filmes"].sort(key=lambda par: par[0], reverse=True)


# =========================================================
# 4) VETOR DE GOSTO
# =========================================================
def calcular_vetor_gosto(filmes_com_sinal):
    """
    Média das sinopses ponderada pelo sinal: filmes que você amou puxam o
    vetor na direção deles; filmes que você odiou empurram para longe.
    """
    soma_vetores = None

    for filme, sinal in filmes_com_sinal:
        if sinal == 0 or "vetor_sinopse" not in filme:
            continue

        contribuicao = sinal * np.asarray(filme["vetor_sinopse"], dtype=np.float32)
        soma_vetores = contribuicao if soma_vetores is None else soma_vetores + contribuicao

    if soma_vetores is None:
        return None

    tamanho = np.linalg.norm(soma_vetores)
    if tamanho == 0:
        return None

    return soma_vetores / tamanho


# =========================================================
# PERFIL COMPLETO
# =========================================================
def calcular_perfil(catalogo):
    """
    Monta o perfil a partir dos seus dados. É rápido (só os filmes que você
    marcou entram no cálculo), então pode ser recalculado sempre que precisar.
    """
    filmes_marcados = [
        filme for filme in catalogo
        if usuario.eh_favorito(filme) or usuario.foi_assistido(filme)
    ]

    filmes_com_sinal = [(filme, sinal_do_filme(filme)) for filme in filmes_marcados]

    generos = {}
    diretores = {}
    atores = {}

    for filme, sinal in filmes_com_sinal:
        for genero in generos_do_filme(filme):
            acumular(generos, genero, sinal, filme)
        for diretor in diretores_do_filme(filme):
            acumular(diretores, diretor, sinal, filme)
        for ator in atores_principais(filme):
            acumular(atores, ator, sinal, filme)

    calcular_afinidades(generos)
    calcular_afinidades(diretores)
    calcular_afinidades(atores)

    quantidade_com_sinal = sum(1 for _, sinal in filmes_com_sinal if sinal != 0)

    return {
        "quantidade_filmes": len(filmes_marcados),
        "quantidade_com_sinal": quantidade_com_sinal,
        "suficiente": quantidade_com_sinal >= MINIMO_FILMES_PARA_PERFIL,
        "generos": generos,
        "diretores": diretores,
        "atores": atores,
        "vetor_gosto": calcular_vetor_gosto(filmes_com_sinal),
    }


def itens_ordenados(itens_perfil, positivos=True, quantidade=5, minimo_filmes=1):
    """Top gêneros/diretores/atores. positivos=False devolve os que você menos curte."""
    if positivos:
        selecionados = [item for item in itens_perfil.values() if item["afinidade"] > 0]
    else:
        selecionados = [item for item in itens_perfil.values() if item["afinidade"] < 0]

    selecionados = [item for item in selecionados if item["quantidade"] >= minimo_filmes]
    selecionados.sort(key=lambda item: item["afinidade"], reverse=positivos)
    return selecionados[:quantidade]


# =========================================================
# 5) PONTUAÇÃO DE UM FILME
# =========================================================
def media_das_afinidades(itens_perfil, nomes, contar_desconhecidos):
    """
    Média das afinidades dos nomes que existem no perfil.
    contar_desconhecidos=True: nomes fora do perfil entram como 0 (neutro).
    """
    valores = []

    for nome in nomes:
        item = itens_perfil.get(normalizar_chave(nome))
        if item is not None:
            valores.append(item["afinidade"])
        elif contar_desconhecidos:
            valores.append(0.0)

    if len(valores) == 0:
        return 0.0

    return sum(valores) / len(valores)


def popularidade_normalizada(filme):
    """0 a 1, em escala logarítmica: 100 votos ~ 0,4 | 100 mil votos ~ 1."""
    votos = filme.get("votos_tmdb") or 0
    return limitar(math.log10(votos + 1) / 5, 0.0, 1.0)


def qualidade_normalizada(filme):
    """-1 a 1, centrado em nota 70/100."""
    notas = []

    rotten = filme.get("rotten_tomatoes")
    if isinstance(rotten, dict) and rotten.get("critica"):
        notas.append(rotten["critica"])
    if filme.get("nota_imdb"):
        notas.append(filme["nota_imdb"] * 10)
    if not notas and filme.get("nota_tmdb"):
        notas.append(filme["nota_tmdb"] * 10)

    if not notas:
        return 0.0

    media = sum(notas) / len(notas)
    return limitar((media - 70) / 30)


def pontuar_filme(filme, perfil):
    """Devolve (pontuação_total, partes) — as partes ajudam a explicar e depurar."""
    # Gêneros que o perfil ainda não conhece ficam de fora da média: assim
    # "Comédia, Música" não perde para "Comédia" só por ter um gênero a mais.
    afinidade_generos = media_das_afinidades(
        perfil["generos"], generos_do_filme(filme), contar_desconhecidos=False
    )
    afinidade_diretores = media_das_afinidades(
        perfil["diretores"], diretores_do_filme(filme), contar_desconhecidos=False
    )
    afinidade_atores = media_das_afinidades(
        perfil["atores"], atores_principais(filme), contar_desconhecidos=False
    )

    similaridade_gosto = 0.0
    if perfil["vetor_gosto"] is not None and "vetor_sinopse" in filme:
        similaridade_gosto = float(np.dot(perfil["vetor_gosto"], filme["vetor_sinopse"]))

    partes = {
        "generos": limitar(afinidade_generos / ESCALA_AFINIDADE),
        "diretores": limitar(afinidade_diretores / ESCALA_AFINIDADE),
        "atores": limitar(afinidade_atores / ESCALA_AFINIDADE),
        "gosto": limitar(similaridade_gosto * ESCALA_GOSTO),
        "popularidade": popularidade_normalizada(filme),
        "qualidade": qualidade_normalizada(filme),
    }

    pontuacao = (
        PESO_GENEROS * partes["generos"]
        + PESO_DIRETORES * partes["diretores"]
        + PESO_ATORES * partes["atores"]
        + PESO_GOSTO * partes["gosto"]
        + PESO_POPULARIDADE * partes["popularidade"]
        + PESO_QUALIDADE * partes["qualidade"]
    )

    return pontuacao, partes


def ordenar_por_afinidade(candidatos, perfil):
    """Do filme que mais combina com você para o que menos combina."""
    return sorted(
        candidatos,
        key=lambda filme: pontuar_filme(filme, perfil)[0],
        reverse=True
    )


def ordenar_com_desempate(candidatos, perfil):
    """
    Para buscas normais ("uma comédia"): a popularidade continua mandando,
    mas entre filmes parecidos, os que combinam com você sobem.
    """
    return sorted(
        candidatos,
        key=lambda filme: (
            popularidade_normalizada(filme)
            + PESO_DESEMPATE * pontuar_filme(filme, perfil)[0]
        ),
        reverse=True
    )


def recomendar(catalogo, perfil, quantidade=20):
    """Os filmes não assistidos que mais combinam com você."""
    nao_assistidos = [filme for filme in catalogo if not usuario.foi_assistido(filme)]
    return ordenar_por_afinidade(nao_assistidos, perfil)[:quantidade]


# =========================================================
# EXPLICAÇÕES ("por que recomendei isto?")
# =========================================================
def evidencias(item_perfil, filme_recomendado, quantidade=2, chaves_ja_citadas=()):
    """Os filmes que você mais curtiu dentro de um gênero/diretor."""
    chaves_ignoradas = {usuario.chave_filme(filme_recomendado), *chaves_ja_citadas}
    return [
        filme for sinal, filme in item_perfil["filmes"]
        if sinal > 0 and usuario.chave_filme(filme) not in chaves_ignoradas
    ][:quantidade]


def juntar_com_e(textos):
    if len(textos) <= 1:
        return "".join(textos)
    return ", ".join(textos[:-1]) + " e " + textos[-1]


def explicar_recomendacao(filme, perfil, generos_ignorados=()):
    """
    Uma frase curta dizendo por que o filme combina com você, ou None.
    generos_ignorados: gêneros que não devem aparecer na explicação
    (ex.: "Crime" num pedido de algo leve).
    """
    generos_ignorados = {normalizar_chave(genero) for genero in generos_ignorados}
    if not perfil["suficiente"]:
        return None

    motivos = []
    chaves_ja_citadas = set()  # para não citar o mesmo filme duas vezes

    # Mesmo diretor de um filme que você curtiu
    for diretor in diretores_do_filme(filme):
        item = perfil["diretores"].get(normalizar_chave(diretor))
        if item is not None and item["afinidade"] > 0:
            filmes_do_diretor = evidencias(item, filme, quantidade=1)
            if filmes_do_diretor:
                quem = "criador" if filme.get("tipo") == "serie" else "diretor"
                motivos.append(
                    f"é do mesmo {quem} de {descrever_sinal(filmes_do_diretor[0])}"
                )
                chaves_ja_citadas.add(usuario.chave_filme(filmes_do_diretor[0]))
                break

    # O gênero do filme que você mais curte
    generos_curtidos = []
    for genero in generos_do_filme(filme):
        if normalizar_chave(genero) in generos_ignorados:
            continue
        item = perfil["generos"].get(normalizar_chave(genero))
        if item is not None and item["afinidade"] > 0:
            generos_curtidos.append(item)

    if generos_curtidos:
        melhor_genero = max(generos_curtidos, key=lambda item: item["afinidade"])
        filmes_do_genero = evidencias(melhor_genero, filme, chaves_ja_citadas=chaves_ja_citadas)
        if filmes_do_genero:
            nomes = juntar_com_e([descrever_sinal(filme_curtido) for filme_curtido in filmes_do_genero])
            # Gênero primeiro: "é Animação, como Toy Story (5★) e Shrek (5★)"
            motivos.insert(0, f"é {melhor_genero['nome']}, como {nomes}")

    if motivos:
        return "💡 Combina com você: " + "; e ".join(motivos) + "."

    _, partes = pontuar_filme(filme, perfil)
    if partes["gosto"] > 0.5:
        return "💡 Tem o tipo de história que você costuma curtir."

    return None


# =========================================================
# RESUMO EM TEXTO (para o chat)
# =========================================================
def resumo_do_perfil(perfil):
    if perfil["quantidade_com_sinal"] == 0:
        return (
            "Ainda não sei nada sobre o seu gosto. 🙂\n\n"
            "Dê estrelas aos filmes que você já viu, ou favorite alguns, "
            "e eu vou aprendendo."
        )

    if not perfil["suficiente"]:
        faltam = MINIMO_FILMES_PARA_PERFIL - perfil["quantidade_com_sinal"]
        return (
            f"Ainda estou te conhecendo: avalie ou favorite mais {faltam} "
            f"filme{'s' if faltam > 1 else ''} para eu montar o seu perfil."
        )

    linhas = [f"Seu perfil (baseado em {perfil['quantidade_filmes']} filmes):"]

    generos_top = itens_ordenados(perfil["generos"], quantidade=4)
    if generos_top:
        linhas.append("🎭 Gêneros que você mais curte: " + ", ".join(item["nome"] for item in generos_top))

    diretores_top = itens_ordenados(perfil["diretores"], quantidade=3)
    if diretores_top:
        linhas.append("🎬 Diretores: " + ", ".join(item["nome"] for item in diretores_top))

    atores_top = itens_ordenados(perfil["atores"], quantidade=3)
    if atores_top:
        linhas.append("⭐ Atores: " + ", ".join(item["nome"] for item in atores_top))

    generos_evitados = itens_ordenados(perfil["generos"], positivos=False, quantidade=2)
    if generos_evitados:
        linhas.append("👎 Menos a sua praia: " + ", ".join(item["nome"] for item in generos_evitados))

    linhas.append('\nPeça "Me recomenda algo" para eu usar isso.')
    return "\n".join(linhas)