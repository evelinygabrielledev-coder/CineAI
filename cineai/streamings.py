"""
streamings.py — "onde assistir?" (Netflix, Prime Video, Max...).

Os dados vêm do TMDB, que usa a JustWatch: para cada título, quais streamings
POR ASSINATURA do Brasil têm ele no catálogo. O importadores/importar_onde_assistir.py
guarda isso no filmes.json, assim:

    "onde_assistir": {"assinatura": ["Netflix", "Max"], "consultado_em": "2026-10-04"}

Este módulo não sabe nada de interface: o chat (filmes.py) e a janela (interface.py)
usam as mesmas funções.
"""
import re
import unicodedata

from cineai import usuario

# Nome que aparece no CineAI, cor do selinho e pedaços do nome que o TMDB usa.
# A ordem importa: "Paramount Plus Apple TV Channel" é Paramount+, não Apple TV+.
STREAMINGS = [
    {"nome": "Netflix", "cor": "#E50914", "chaves": ["netflix"]},
    {"nome": "Prime Video", "cor": "#00A8E1", "chaves": ["primevideo", "amazonprime"]},
    {"nome": "Max", "cor": "#002BE7", "chaves": ["hbomax", "max"]},
    {"nome": "Disney+", "cor": "#113CCF", "chaves": ["disney", "starplus"]},
    {"nome": "Globoplay", "cor": "#FB0234", "chaves": ["globoplay"]},
    {"nome": "Paramount+", "cor": "#0064FF", "chaves": ["paramount"]},
    {"nome": "Apple TV+", "cor": "#1D1D1F", "chaves": ["appletv"]},
    {"nome": "Crunchyroll", "cor": "#F47521", "chaves": ["crunchyroll"]},
    {"nome": "MUBI", "cor": "#2A2A2A", "chaves": ["mubi"]},
    {"nome": "Claro tv+", "cor": "#DA291C", "chaves": ["clarotv", "claro"]},
]
NOMES_DOS_STREAMINGS = [streaming["nome"] for streaming in STREAMINGS]
COR_PADRAO = "#5C1A16"

MEUS_STREAMINGS = "meus"   # filtro especial: "os que eu tenho"

# Como cada streaming aparece numa frase ("na netflix", "no prime", "na hbo"...)
APELIDOS_NO_CHAT = {
    "Netflix": ["netflix"],
    "Prime Video": ["prime video", "prime", "amazon prime", "amazon"],
    "Max": ["max", "hbo max", "hbo"],
    "Disney+": ["disney plus", "disney+", "disney", "star plus"],
    "Globoplay": ["globoplay", "globo play"],
    "Paramount+": ["paramount plus", "paramount+", "paramount"],
    "Apple TV+": ["apple tv", "apple tv+", "apple"],
    "Crunchyroll": ["crunchyroll"],
    "MUBI": ["mubi"],
    "Claro tv+": ["claro tv"],
}
EXPRESSOES_MEUS_STREAMINGS = [
    "que eu tenho", "que eu assino", "nos meus streamings", "meus streamings",
    "no que eu tenho", "que eu pago", "nas minhas assinaturas",
]


def simplificar(texto):
    """'Amazon Prime Video with Ads' -> 'amazonprimevideowithads'"""
    texto = unicodedata.normalize("NFD", str(texto).lower())
    texto = "".join(caractere for caractere in texto if unicodedata.category(caractere) != "Mn")
    return re.sub(r"[^a-z0-9]", "", texto)


def nome_padrao(nome_tmdb):
    """
    'Amazon Prime Video with Ads' -> 'Prime Video' | 'HBO Max' -> 'Max'.
    Nomes que não conhecemos continuam como vieram.
    """
    simples = simplificar(nome_tmdb)
    for streaming in STREAMINGS:
        for chave in streaming["chaves"]:
            # "max" só vale no começo ("Max", "Max Amazon Channel"), senão "Cinemax" viraria Max
            if (chave == "max" and simples.startswith("max")) or (chave != "max" and chave in simples):
                return streaming["nome"]
    return nome_tmdb.strip()


def padronizar_lista(nomes_tmdb):
    """Tira repetidos ('Netflix' e 'Netflix basic with Ads' são o mesmo) e ordena."""
    vistos = []
    for nome in nomes_tmdb:
        padrao = nome_padrao(nome)
        if padrao and padrao not in vistos:
            vistos.append(padrao)
    ordem = {nome: posicao for posicao, nome in enumerate(NOMES_DOS_STREAMINGS)}
    return sorted(vistos, key=lambda nome: (ordem.get(nome, 99), nome))


def cor_do_streaming(nome):
    for streaming in STREAMINGS:
        if streaming["nome"] == nome:
            return streaming["cor"]
    return COR_PADRAO


def foi_consultado(filme):
    return isinstance(filme.get("onde_assistir"), dict)


def onde_assistir(filme):
    """Lista dos streamings por assinatura (pode ser vazia), ou None se ainda não consultamos."""
    if not foi_consultado(filme):
        return None
    return list(filme["onde_assistir"].get("assinatura") or [])


def esta_no_streaming(filme, nome_streaming):
    return nome_streaming in (onde_assistir(filme) or [])


def esta_nos_meus_streamings(filme):
    meus = set(usuario.obter_meus_streamings())
    return bool(meus & set(onde_assistir(filme) or []))


def filtrar_por_streaming(lista_filmes, streaming):
    """streaming: um nome ('Netflix'), MEUS_STREAMINGS ou None (não filtra)."""
    if not streaming:
        return list(lista_filmes)
    if streaming == MEUS_STREAMINGS:
        return [filme for filme in lista_filmes if esta_nos_meus_streamings(filme)]
    return [filme for filme in lista_filmes if esta_no_streaming(filme, streaming)]


def contem_expressao(texto, expressao):
    palavras_texto = " " + " ".join(re.findall(r"[a-z0-9+]+", simplificar_com_espacos(texto))) + " "
    palavras_expressao = " " + " ".join(re.findall(r"[a-z0-9+]+", simplificar_com_espacos(expressao))) + " "
    return palavras_expressao.strip() != "" and palavras_expressao in palavras_texto


def simplificar_com_espacos(texto):
    texto = unicodedata.normalize("NFD", str(texto).lower())
    return "".join(caractere for caractere in texto if unicodedata.category(caractere) != "Mn")


def detectar_streaming(texto):
    """
    'uma comédia na Netflix'        -> 'Netflix'
    'algo que eu tenho' / 'nos meus' -> MEUS_STREAMINGS
    nada disso                       -> None
    Só vale com "na/no/da/do/tá na..." antes, para "Max" ou "Prime" soltos
    (ex.: "um filme com o Max") não virarem streaming.
    """
    if any(contem_expressao(texto, expressao) for expressao in EXPRESSOES_MEUS_STREAMINGS):
        return MEUS_STREAMINGS
    for nome, apelidos in APELIDOS_NO_CHAT.items():
        for apelido in sorted(apelidos, key=len, reverse=True):
            for preposicao in ("na", "no", "da", "do", "pela", "pelo", "em"):
                if contem_expressao(texto, f"{preposicao} {apelido}"):
                    return nome
            if apelido in ("netflix", "globoplay", "crunchyroll", "mubi", "prime video", "disney plus") \
                    and contem_expressao(texto, apelido):
                return nome
    return None


def texto_onde_assistir(filme):
    """Frase curta para o chat (ou "" se ainda não consultamos)."""
    lista = onde_assistir(filme)
    if lista is None:
        return ""
    if not lista:
        return "📺 Não está em nenhum streaming por assinatura no Brasil agora (só aluguel ou compra)."
    meus = set(usuario.obter_meus_streamings())
    marcados = [f"{nome} ✓" if nome in meus else nome for nome in lista]
    return "📺 Onde assistir: " + ", ".join(marcados)