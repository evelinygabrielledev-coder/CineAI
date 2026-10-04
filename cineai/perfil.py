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
  5. As suas ANOTAÇÕES do diário viram vetores também: um filme cuja sinopse
     lembra o que você escreveu sobre um título que AMOU sobe; se lembra o que
     você escreveu sobre um que DETESTOU, desce. (As estrelas dão o sinal: o
     embedding sozinho não sabe a diferença entre "amei" e "odiei".)
  6. Cada filme não assistido recebe uma pontuação combinando tudo isso.

Este módulo não sabe nada de interface nem de chat.
"""

import math
import unicodedata

import numpy as np

from cineai import usuario


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
PESO_ANOTACOES = 0.25      # parecido com o que você ESCREVEU no diário

# 5) Escalas para deixar cada parte entre -1 e 1
ESCALA_AFINIDADE = 3.0
ESCALA_GOSTO = 2.0
# As anotações usam uma curva suave (tanh) em vez de um teto: com 1.900 títulos,
# muitos passavam de "2,5 desvios" e TODOS empatavam em +1,00 (a anotação parava
# de diferenciar). Com a curva, 2 desvios ≈ 0,46 | 4 ≈ 0,76 | 6 ≈ 0,91: nunca empata.
ESCALA_ANOTACOES = 4.0

# 6) Mínimo de filmes com sinal para o perfil valer
MINIMO_FILMES_PARA_PERFIL = 3

# 7) Nas buscas normais ("uma comédia"), quanto o gosto pesa no desempate
PESO_DESEMPATE = 0.5

# 8) Anotações: a partir de quantos desvios a explicação cita o que você escreveu
LIMITE_ANOTACAO_NA_EXPLICACAO = 1.5
TAMANHO_TRECHO_ANOTACAO = 70
PESO_SO_ANOTACOES = 0.8    # "me recomenda pelo que eu escrevi": anotações valem 80%
MINIMO_PALAVRAS_ANOTACAO = 3  # "amei" sozinho não diz SOBRE O QUÊ: fica de fora da busca
VIZINHOS_POR_ANOTACAO = 3     # quantos títulos parecidos com cada anotação o Painel do RAG mostra
# A anotação é misturada com a sinopse do próprio título anotado ("âncora").
# Só o texto: "marcou minha infância" acha filmes SOBRE infância. Com a âncora,
# a busca fica "infância + o que esse filme é" (minions, vilão que vira pai...).
# 1,0 = só o que você escreveu | 0,0 = só a sinopse do filme anotado.
PESO_TEXTO_DA_ANOTACAO = 0.6

# O filmes.py liga isto ao modelo de embeddings (perfil.codificar_texto = modelo.encode).
# Sem ele (ex.: funções chamadas soltas), as anotações simplesmente não entram.
codificar_texto = None


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
# 5) ANOTAÇÕES (o que você escreveu no diário)
# =========================================================
# Por que "desvios" (z) e não a similaridade direta? Um texto curto em português
# já fica um pouco parecido com QUALQUER sinopse (0,2 ~ 0,3 no modelo real).
# Então comparamos cada filme com a média do catálogo para a mesma anotação:
#     z = (similaridade - média) / desvio padrão
# z = 0 é "normal"; z = 2 é bem mais parecido que o resto do catálogo.
cache_vetores_texto = {}
cache_matriz_sinopses = {"chave": None, "matriz": None}


def vetor_do_texto(texto):
    """Embedding (tamanho 1) de um texto, guardado em memória para não recalcular."""
    if codificar_texto is None or not texto:
        return None
    if texto not in cache_vetores_texto:
        vetor = np.asarray(codificar_texto(texto), dtype=np.float32)
        tamanho = np.linalg.norm(vetor)
        cache_vetores_texto[texto] = vetor / tamanho if tamanho else None
    return cache_vetores_texto[texto]


def matriz_das_sinopses(catalogo):
    """Todas as sinopses empilhadas numa matriz (uma linha por filme), com cache."""
    chave = (id(catalogo), len(catalogo))
    if cache_matriz_sinopses["chave"] != chave:
        vetores = [filme["vetor_sinopse"] for filme in catalogo if "vetor_sinopse" in filme]
        cache_matriz_sinopses["chave"] = chave
        cache_matriz_sinopses["matriz"] = np.vstack(vetores).astype(np.float32) if vetores else None
    return cache_matriz_sinopses["matriz"]


def calcular_anotacoes(catalogo):
    """
    Cada anotação de um título com sinal (gostou ou não gostou) vira:
        {"filme", "texto", "sinal", "vetor", "media", "desvio"}
    Anotação de filme com 3★ (sinal 0) não diz nada do seu gosto e fica de fora.
    """
    filmes_por_chave = {usuario.chave_filme(filme): filme for filme in catalogo}
    matriz = matriz_das_sinopses(catalogo)
    anotacoes = []

    for chave, registro in usuario.dados_usuario.get("anotacoes", {}).items():
        filme = filmes_por_chave.get(chave)
        if filme is None:
            continue
        sinal = sinal_do_filme(filme)
        texto = registro.get("texto", "")
        if sinal == 0 or len(texto.split()) < MINIMO_PALAVRAS_ANOTACAO:
            continue
        vetor = vetor_do_texto(texto)
        if vetor is None:
            continue
        vetor_ancora = filme.get("vetor_sinopse")
        if vetor_ancora is not None and len(vetor_ancora) == len(vetor):
            mistura = PESO_TEXTO_DA_ANOTACAO * vetor + (1 - PESO_TEXTO_DA_ANOTACAO) * np.asarray(vetor_ancora, dtype=np.float32)
            tamanho = np.linalg.norm(mistura)
            if tamanho:
                vetor = mistura / tamanho

        media, desvio = 0.0, 1.0
        if matriz is not None and len(matriz) > 1 and matriz.shape[1] == len(vetor):
            similaridades = matriz @ vetor
            media = float(similaridades.mean())
            desvio = float(similaridades.std()) or 1.0

        anotacoes.append({
            "filme": filme, "texto": registro["texto"], "sinal": sinal,
            "vetor": vetor, "media": media, "desvio": desvio,
        })

    return anotacoes


def ecos_das_anotacoes(filme, perfil):
    """
    O quanto a sinopse do filme "ecoa" cada anotação: [(contribuição, z, anotação)].
    contribuição = peso da anotação (-1 a 1, pelas estrelas) × z (só a parte acima do normal).
    """
    anotacoes = perfil.get("anotacoes") or []
    if not anotacoes or "vetor_sinopse" not in filme:
        return []

    chave = usuario.chave_filme(filme)
    ecos = []
    for anotacao in anotacoes:
        if usuario.chave_filme(anotacao["filme"]) == chave:
            continue  # a anotação do próprio filme não conta para ele
        if len(anotacao["vetor"]) != len(filme["vetor_sinopse"]):
            continue
        similaridade = float(np.dot(anotacao["vetor"], filme["vetor_sinopse"]))
        z = (similaridade - anotacao["media"]) / anotacao["desvio"]
        peso = limitar(anotacao["sinal"] / 2.0)
        ecos.append((peso * max(z, 0.0), z, anotacao))
    return ecos


def parte_das_anotacoes(filme, perfil):
    """
    -1 a 1: o eco da anotação que MAIS combina (de um título que você curtiu)
    menos o eco da que mais lembra um título que você não curtiu.
    """
    ecos = ecos_das_anotacoes(filme, perfil)
    if not ecos:
        return 0.0
    melhor_positivo = max((contribuicao for contribuicao, _, _ in ecos if contribuicao > 0), default=0.0)
    pior_negativo = min((contribuicao for contribuicao, _, _ in ecos if contribuicao < 0), default=0.0)
    return math.tanh((melhor_positivo + pior_negativo) / ESCALA_ANOTACOES)


def vizinhos_da_anotacao(anotacao, candidatos, quantidade=VIZINHOS_POR_ANOTACAO):
    """Os títulos cuja sinopse mais lembra uma anotação: [(z, filme)] (para o Painel do RAG)."""
    pontuados = []
    for filme in candidatos:
        if "vetor_sinopse" not in filme or len(filme["vetor_sinopse"]) != len(anotacao["vetor"]):
            continue
        if usuario.chave_filme(filme) == usuario.chave_filme(anotacao["filme"]):
            continue
        similaridade = float(np.dot(anotacao["vetor"], filme["vetor_sinopse"]))
        pontuados.append(((similaridade - anotacao["media"]) / anotacao["desvio"], filme))
    pontuados.sort(key=lambda par: par[0], reverse=True)
    return pontuados[:quantidade]


def anotacao_que_lembra(filme, perfil):
    """(anotação, z) da anotação positiva que mais combina com o filme, ou (None, 0)."""
    positivos = [(contribuicao, z, anotacao) for contribuicao, z, anotacao in ecos_das_anotacoes(filme, perfil)
                 if contribuicao > 0]
    if not positivos:
        return None, 0.0
    _, z, anotacao = max(positivos, key=lambda eco: eco[0])
    return anotacao, z


def trecho(texto, tamanho=TAMANHO_TRECHO_ANOTACAO):
    texto = " ".join(texto.split())
    return texto if len(texto) <= tamanho else texto[: tamanho - 1].rstrip() + "…"


def frase_da_anotacao(filme, perfil):
    """'📝 Lembra o que você escreveu sobre Titanic: “chorei no final…”' ou None."""
    anotacao, z = anotacao_que_lembra(filme, perfil)
    if anotacao is None or z < LIMITE_ANOTACAO_NA_EXPLICACAO:
        return None
    return f'📝 Lembra o que você escreveu sobre {anotacao["filme"]["nome"]}: “{trecho(anotacao["texto"])}”'


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
        "anotacoes": calcular_anotacoes(catalogo),
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
        "anotacoes": parte_das_anotacoes(filme, perfil),
    }

    pontuacao = (
        PESO_GENEROS * partes["generos"]
        + PESO_DIRETORES * partes["diretores"]
        + PESO_ATORES * partes["atores"]
        + PESO_GOSTO * partes["gosto"]
        + PESO_POPULARIDADE * partes["popularidade"]
        + PESO_QUALIDADE * partes["qualidade"]
        + PESO_ANOTACOES * partes["anotacoes"]
    )

    return pontuacao, partes


def pontuar_pelas_anotacoes(filme, perfil):
    """'Me recomenda pelo que eu escrevi': as anotações mandam, o resto desempata."""
    pontuacao, partes = pontuar_filme(filme, perfil)
    return PESO_SO_ANOTACOES * partes["anotacoes"] + (1 - PESO_SO_ANOTACOES) * pontuacao


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
        return frase_da_anotacao(filme, perfil)

    frase_anotacao = frase_da_anotacao(filme, perfil)

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

    explicacao = None
    if motivos:
        explicacao = "💡 Combina com você: " + "; e ".join(motivos) + "."
    elif frase_anotacao is None:
        _, partes = pontuar_filme(filme, perfil)
        if partes["gosto"] > 0.5:
            explicacao = "💡 Tem o tipo de história que você costuma curtir."

    if frase_anotacao is not None:
        explicacao = f"{explicacao}\n{frase_anotacao}" if explicacao else frase_anotacao

    return explicacao


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
