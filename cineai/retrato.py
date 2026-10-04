"""
retrato.py — "O que meu diário diz sobre mim".

A IA local (Ollama) lê um resumo do seu diário (gêneros, notas, favoritos,
revistos e as suas anotações) e escreve um parágrafo sobre você como espectadora.

Como um modelo pequeno às vezes inventa, o texto passa por uma conferência:
    - precisa citar pelo menos um título que está mesmo no seu diário;
    - não pode ser curto nem comprido demais, nem vir em outro alfabeto.
Se a IA estiver desligada ou o texto não passar, o CineAI escreve o retrato
sozinho, com frases prontas (origem "regras"). As anotações mostradas embaixo
do parágrafo são sempre as SUAS, copiadas do diário, nunca da IA.

O retrato fica guardado no usuario.json (em "configuracoes") junto com uma
"impressão digital" do diário: só é escrito de novo quando algo muda
(ou quando você pede "escrever de novo").

Este módulo não importa o filmes.py: quem chama passa a função que conversa
com a IA (filmes.perguntar_ao_modelo). Assim o filmes.py pode usar o retrato no chat.
"""
import hashlib
import json
import re
import unicodedata
from datetime import date

from cineai import usuario

MINIMO_TITULOS_RETRATO = 3
MINIMO_PALAVRAS_ANOTACAO = 3
MAXIMO_ANOTACOES_NO_PROMPT = 8
TAMANHO_MAXIMO_ANOTACAO_NO_PROMPT = 280   # caracteres
MAXIMO_CITACOES = 3
TAMANHO_MINIMO_TEXTO_IA = 120
TAMANHO_MAXIMO_TEXTO_IA = 1600
PALAVRAS_DO_TRECHO = 14

ORIGEM_IA = "ia"
ORIGEM_REGRAS = "regras"
CHAVE_CONFIGURACAO = "retrato"
MARCA_DO_PROMPT = "Escreva o retrato"


# =========================================================
# 1. Os fatos do diário (tudo o que a IA pode usar)
# =========================================================
def contar_mais_frequentes(valores, quantidade):
    contagem = {}
    for valor in valores:
        contagem[valor] = contagem.get(valor, 0) + 1
    ordem = {valor: posicao for posicao, valor in enumerate(contagem)}
    ordenados = sorted(contagem.items(), key=lambda par: (-par[1], ordem[par[0]]))
    return ordenados[:quantidade]


def anotacoes_escolhidas(sessoes):
    """
    As anotações com pelo menos 3 palavras, priorizando as notas extremas
    (5★ e 1★ dizem mais sobre você) e os textos mais longos. Ficam na ordem do diário.
    """
    anotadas = [
        sessao for sessao in sessoes
        if len((sessao["anotacao"] or "").split()) >= MINIMO_PALAVRAS_ANOTACAO
    ]

    def peso(sessao):
        nota = sessao["nota"]
        extremo = abs(nota - 3) if nota is not None else 0
        return (extremo, len(sessao["anotacao"].split()))

    melhores = sorted(anotadas, key=peso, reverse=True)[:MAXIMO_ANOTACOES_NO_PROMPT]
    return [sessao for sessao in anotadas if sessao in melhores]


def fatos_do_diario(catalogo):
    """
    Resumo do diário em dados simples (texto e números), ou None se ainda
    houver poucos títulos vistos para falar alguma coisa.
    """
    sessoes = usuario.entradas_do_diario(catalogo, usuario.ORDEM_DIARIO_ANTIGOS)
    primeiras = [sessao for sessao in sessoes if sessao["sessao"] is None]
    if len(primeiras) < MINIMO_TITULOS_RETRATO:
        return None

    numeros = usuario.estatisticas_do_diario(catalogo)
    generos = contar_mais_frequentes(
        [genero for entrada in primeiras for genero in usuario.separar_nomes(entrada["filme"].get("genero"))], 3
    )
    decadas = contar_mais_frequentes(   # 1994 -> "anos 90", 2010 -> "anos 10"
        [f"anos {str(entrada['filme']['ano'])[2]}0" for entrada in primeiras if entrada["filme"].get("ano")], 1
    )

    def nomes(entradas, limite):
        vistos = []
        for entrada in entradas:
            nome = entrada["filme"]["nome"]
            if nome not in vistos:
                vistos.append(nome)
        return vistos[:limite]

    return {
        "nome": usuario.obter_nome_do_dono(),
        "titulos": numeros["total"],
        "filmes": numeros["filmes"],
        "series": numeros["series"],
        "nota_media": numeros["nota_media"],
        "generos": [nome for nome, _ in generos],
        "decada": decadas[0][0] if decadas and decadas[0][1] >= 2 else None,
        "pessoa": numeros["pessoa"][0] if numeros["pessoa"] else None,
        "favoritos": [filme["nome"] for filme in usuario.filmes_da_lista("favoritos", catalogo)][:5],
        "cinco_estrelas": nomes([entrada for entrada in reversed(primeiras) if entrada["nota"] == 5], 5),
        "notas_baixas": nomes([entrada for entrada in primeiras if entrada["nota"] is not None and entrada["nota"] <= 2], 3),
        "revistos": nomes([sessao for sessao in sessoes if sessao["sessao"] is not None], 3),
        "anotacoes": [
            {
                "filme": sessao["filme"]["nome"],
                "nota": sessao["nota"],
                "texto": " ".join(sessao["anotacao"].split())[:TAMANHO_MAXIMO_ANOTACAO_NO_PROMPT],
                "data": sessao["data"].isoformat() if sessao["data"] else None,
            }
            for sessao in anotacoes_escolhidas(sessoes)
        ],
    }


def impressao_digital(fatos):
    """Muda sempre que algo relevante do diário muda (notas, anotações, favoritos...)."""
    texto = json.dumps(fatos, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(texto.encode("utf-8")).hexdigest()[:16]


def titulos_citaveis(fatos):
    """Todos os nomes de título que aparecem nos fatos (para conferir o texto da IA)."""
    nomes = set(fatos["favoritos"] + fatos["cinco_estrelas"] + fatos["notas_baixas"] + fatos["revistos"])
    nomes.update(anotacao["filme"] for anotacao in fatos["anotacoes"])
    return nomes


# =========================================================
# 2. A IA escreve
# =========================================================
def texto_estrelas_curto(nota):
    return f"{nota}★" if nota is not None else "sem nota"


def montar_prompt(fatos):
    linhas = [
        f"{MARCA_DO_PROMPT} desta pessoa como espectadora, a partir do diário de cinema dela.",
        "",
        "Regras:",
        "- Um único parágrafo, de 4 a 6 frases, em português do Brasil.",
        '- Fale diretamente com a pessoa, usando "você".',
        "- Use SOMENTE as informações abaixo. Não invente filmes, nomes, gostos nem acontecimentos.",
        "- Cite pelo menos dois títulos do diário e comente o que as anotações mostram sobre ela.",
        "- Não copie as anotações inteiras; pode citar só uma expressão curta entre aspas.",
        "- Tom carinhoso e observador, como uma amiga que leu o diário. Sem listas, sem títulos, sem emojis.",
        "",
        "Diário" + (f" de {fatos['nome']}" if fatos["nome"] else "") + ":",
        f"- Títulos vistos: {fatos['titulos']} ({fatos['filmes']} filmes, {fatos['series']} séries)",
    ]
    if fatos["nota_media"] is not None:
        linhas.append(f"- Nota média que costuma dar: {fatos['nota_media']} de 5")
    if fatos["generos"]:
        linhas.append("- Gêneros que mais aparecem: " + ", ".join(fatos["generos"]))
    if fatos["decada"]:
        linhas.append(f"- Época dos filmes que mais vê: {fatos['decada']}")
    if fatos["pessoa"]:
        linhas.append(f"- Diretor que mais aparece: {fatos['pessoa']}")
    if fatos["favoritos"]:
        linhas.append("- Favoritos: " + ", ".join(fatos["favoritos"]))
    if fatos["cinco_estrelas"]:
        linhas.append("- Deu 5 estrelas para: " + ", ".join(fatos["cinco_estrelas"]))
    if fatos["notas_baixas"]:
        linhas.append("- Não gostou (1 ou 2 estrelas): " + ", ".join(fatos["notas_baixas"]))
    if fatos["revistos"]:
        linhas.append("- Viu de novo: " + ", ".join(fatos["revistos"]))
    if fatos["anotacoes"]:
        linhas.append("- Anotações que ela escreveu (título, estrelas: texto):")
        for anotacao in fatos["anotacoes"]:
            linhas.append(f'  * {anotacao["filme"]} ({texto_estrelas_curto(anotacao["nota"])}): "{anotacao["texto"]}"')
    else:
        linhas.append("- Ela ainda não escreveu anotações.")
    linhas += ["", "Responda somente com o parágrafo.", "", "Retrato:"]
    return "\n".join(linhas)


def simplificar(texto):
    texto = unicodedata.normalize("NFD", str(texto).lower())
    texto = "".join(caractere for caractere in texto if unicodedata.category(caractere) != "Mn")
    return " ".join(re.findall(r"[a-z0-9]+", texto))


def limpar_texto_da_ia(texto):
    """Tira o <think>, rótulos, markdown e quebras de linha: fica um parágrafo só."""
    texto = re.sub(r"<think>.*?</think>", "", texto or "", flags=re.DOTALL)
    texto = re.sub(r"^\s*(retrato|resposta)\s*:\s*", "", texto.strip(), flags=re.IGNORECASE)
    texto = texto.replace("**", "").replace("__", "")
    texto = re.sub(r"^#+\s*", "", texto, flags=re.MULTILINE)
    texto = " ".join(texto.split())
    if len(texto) >= 2 and texto[0] in "\"“'" and texto[-1] in "\"”'":
        texto = texto[1:-1].strip()
    return texto


def tem_outro_alfabeto(texto):
    """Chinês, japonês, coreano, cirílico... (o qwen às vezes escapa para o chinês)."""
    return any(
        "Ѐ" <= caractere <= "ӿ" or "぀" <= caractere <= "ヿ"
        or "一" <= caractere <= "鿿" or "가" <= caractere <= "힯"
        for caractere in texto
    )


def conferir_texto_da_ia(texto, fatos):
    """O texto limpo, se passar na conferência; senão None."""
    texto = limpar_texto_da_ia(texto)
    if not TAMANHO_MINIMO_TEXTO_IA <= len(texto) <= TAMANHO_MAXIMO_TEXTO_IA:
        return None
    if tem_outro_alfabeto(texto):
        return None
    texto_simples = f" {simplificar(texto)} "
    if not any(f" {simplificar(nome)} " in texto_simples for nome in titulos_citaveis(fatos)):
        return None   # não citou nenhum título de verdade: provavelmente inventou
    return texto


def escrever_com_ia(fatos, perguntar):
    """Pede o parágrafo à IA. None se ela estiver desligada ou o texto não passar."""
    if perguntar is None:
        return None
    try:
        resposta = perguntar(montar_prompt(fatos))
    except Exception:
        return None   # Ollama fechado, modelo não baixado...
    return conferir_texto_da_ia(resposta, fatos)


# =========================================================
# 3. Sem IA: o retrato com frases prontas
# =========================================================
def juntar(nomes):
    """['A', 'B', 'C'] -> 'A, B e C'"""
    nomes = list(nomes)
    if len(nomes) <= 1:
        return "".join(nomes)
    return ", ".join(nomes[:-1]) + " e " + nomes[-1]


def trecho(texto):
    palavras = texto.split()
    if len(palavras) <= PALAVRAS_DO_TRECHO:
        return texto.rstrip(" .")
    return " ".join(palavras[:PALAVRAS_DO_TRECHO]).rstrip(" ,.;") + "…"


def texto_por_regras(fatos):
    frases = []
    quantidade = f"{fatos['titulos']} título{'s' if fatos['titulos'] != 1 else ''}"
    if fatos["generos"]:
        frases.append(f"Seu diário já tem {quantidade}, e quem folheia percebe logo uma queda por {juntar(fatos['generos'][:2]).lower()}.")
    else:
        frases.append(f"Seu diário já tem {quantidade}, e cada página conta um pouco de você.")
    if fatos["pessoa"]:
        frases.append(f"O nome de {fatos['pessoa']} aparece mais de uma vez: você acompanha o trabalho dele de perto.")
    if fatos["cinco_estrelas"]:
        frases.append(f"Quando um filme te ganha, você não economiza: {juntar(fatos['cinco_estrelas'][:2])} levaram 5 estrelas.")
    if fatos["anotacoes"]:
        escolhida = max(fatos["anotacoes"], key=lambda anotacao: (anotacao["nota"] or 0, len(anotacao["texto"])))
        frases.append(f"E as anotações contam o resto: sobre {escolhida['filme']}, você escreveu \"{trecho(escolhida['texto'])}\".")
    if fatos["revistos"]:
        frases.append(f"Você também volta aos que ama, e {fatos['revistos'][0]} já foi visto mais de uma vez.")
    if fatos["notas_baixas"]:
        frases.append(f"Mas nem tudo te convence: {juntar(fatos['notas_baixas'][:2])} não passaram das 2 estrelas.")
    return " ".join(frases)


# =========================================================
# 4. Juntando tudo (com o retrato guardado)
# =========================================================
def citacoes(fatos):
    """
    Até 3 anotações SUAS para mostrar embaixo do parágrafo:
    a de maior nota, a de menor nota e a mais longa que sobrar.
    """
    anotacoes = list(fatos["anotacoes"])
    escolhidas = []

    def pegar(chave, reverso):
        restantes = [anotacao for anotacao in anotacoes if anotacao not in escolhidas]
        if restantes:
            escolhidas.append(sorted(restantes, key=chave, reverse=reverso)[0])

    pegar(lambda anotacao: (anotacao["nota"] or 0, len(anotacao["texto"])), True)
    com_nota_baixa = [anotacao for anotacao in anotacoes if anotacao["nota"] is not None and anotacao["nota"] <= 2]
    if com_nota_baixa and com_nota_baixa[0] not in escolhidas:
        escolhidas.append(min(com_nota_baixa, key=lambda anotacao: anotacao["nota"]))
    while len(escolhidas) < min(MAXIMO_CITACOES, len(anotacoes)):
        pegar(lambda anotacao: len(anotacao["texto"]), True)
    return escolhidas[:MAXIMO_CITACOES]


def montar_retrato(fatos, texto_ia):
    """O retrato final (com o texto da IA, se ele passou na conferência) e guarda no usuario.json."""
    retrato = {
        "texto": texto_ia or texto_por_regras(fatos),
        "origem": ORIGEM_IA if texto_ia else ORIGEM_REGRAS,
        "citacoes": citacoes(fatos),
        "criado_em": date.today().isoformat(),
        "impressao": impressao_digital(fatos),
    }
    usuario.dados_usuario["configuracoes"][CHAVE_CONFIGURACAO] = retrato
    usuario.salvar_dados()
    return retrato


def retrato_guardado(fatos):
    """O retrato que já foi escrito, se o diário não mudou desde então."""
    guardado = usuario.dados_usuario["configuracoes"].get(CHAVE_CONFIGURACAO)
    if isinstance(guardado, dict) and guardado.get("impressao") == impressao_digital(fatos):
        return guardado
    return None


def gerar_retrato(catalogo, perguntar=None, forcar=False):
    """
    O retrato do diário (dict com texto, origem, citacoes, criado_em), ou None
    se ainda há poucos títulos. forcar=True escreve de novo mesmo sem mudanças.
    """
    fatos = fatos_do_diario(catalogo)
    if fatos is None:
        return None
    if not forcar:
        guardado = retrato_guardado(fatos)
        if guardado is not None:
            return guardado
    return montar_retrato(fatos, escrever_com_ia(fatos, perguntar))