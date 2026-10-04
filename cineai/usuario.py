"""
Dados pessoais do usuário do CineAI: favoritos, assistidos (com nota),
anotações e a lista "Quero assistir".

Tudo fica salvo em usuario.json, na pasta do projeto. Exemplo do arquivo:

{
  "favoritos": {
    "808": {"nome": "Shrek", "adicionado_em": "2026-10-03"}
  },
  "assistidos": {
    "808": {"nome": "Shrek", "adicionado_em": "2026-10-03"}
  }
}

A chave de cada filme é o id do TMDB (como texto, porque o JSON só aceita
texto como chave). Filmes sem id usam o nome. Assim, dois filmes com o mesmo
título (ex.: "O Rei Leão" de 1994 e de 2019) nunca se misturam.

Este módulo não sabe nada de interface: o cineai.py e o filmes.py usam as
mesmas funções.
"""

import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path


# Os testes automáticos usam outra pasta para não mexer nos seus dados.
from cineai.caminhos import PASTA_PROJETO, PASTA_USUARIO

PASTA_DADOS = PASTA_USUARIO                       # dados/ (os testes trocam por uma pasta temporária)
CAMINHO_USUARIO = PASTA_DADOS / "usuario.json"


def trazer_arquivo_do_lugar_antigo(nome_arquivo):
    """
    Antes da organização em pastas, os seus dados ficavam soltos na raiz do projeto.
    Se ainda estiverem lá (e não em dados/), são movidos uma vez, sem perder nada.
    """
    if "CINEAI_PASTA_USUARIO" in os.environ:
        return   # nos testes (pasta temporária) nunca mexemos nos seus arquivos de verdade
    caminho_novo = PASTA_DADOS / nome_arquivo
    caminho_antigo = PASTA_PROJETO / nome_arquivo
    if not caminho_novo.exists() and caminho_antigo.exists() and caminho_antigo != caminho_novo:
        PASTA_DADOS.mkdir(parents=True, exist_ok=True)
        caminho_antigo.replace(caminho_novo)
        print(f"{nome_arquivo} foi movido para a pasta dados/.")


trazer_arquivo_do_lugar_antigo("usuario.json")

# anotacoes = "Minhas anotações" de cada filme | quero_assistir = guardados "pra depois"
# configuracoes = coisas suas que não são filmes (ex.: o nome na capa do diário)
LISTAS = ("favoritos", "assistidos", "anotacoes", "quero_assistir", "configuracoes")


# =========================================================
# IDENTIFICAÇÃO DO FILME
# =========================================================
def chave_filme(filme):
    """
    Shrek (id 808) -> "808" | série Breaking Bad (id 1396) -> "serie:1396".
    Sem id -> "nome:Shrek".
    Filmes e séries têm numerações separadas no TMDB (um filme e uma série
    podem ter o mesmo id), por isso a série ganha o prefixo "serie:".
    """
    if filme.get("id") is not None:
        if filme.get("tipo") == "serie":
            return f'serie:{filme["id"]}'
        return str(filme["id"])
    return "nome:" + filme["nome"]


# =========================================================
# LEITURA E GRAVAÇÃO DO ARQUIVO
# =========================================================
def criar_dados_vazios():
    return {nome_lista: {} for nome_lista in LISTAS}


def carregar_dados():
    """Lê o usuario.json. Se não existir ou estiver corrompido, começa vazio."""
    if not CAMINHO_USUARIO.exists():
        return criar_dados_vazios()

    try:
        with open(CAMINHO_USUARIO, "r", encoding="utf-8") as arquivo:
            dados_lidos = json.load(arquivo)
    except (json.JSONDecodeError, OSError) as erro:
        # Guarda o arquivo problemático para não perder nada sem querer.
        caminho_backup = CAMINHO_USUARIO.with_suffix(".corrompido.json")
        try:
            CAMINHO_USUARIO.replace(caminho_backup)
            print(f"usuario.json estava com problema ({erro}). Cópia salva em {caminho_backup.name}.")
        except OSError:
            pass
        return criar_dados_vazios()

    dados = criar_dados_vazios()

    for nome_lista in LISTAS:
        lista_lida = dados_lidos.get(nome_lista, {})
        if isinstance(lista_lida, dict):
            dados[nome_lista] = lista_lida

    return dados


def salvar_dados():
    """
    Grava primeiro num arquivo temporário e só depois troca pelo original.
    Se o programa fechar no meio da gravação, o usuario.json antigo continua inteiro.
    """
    caminho_temporario = CAMINHO_USUARIO.with_suffix(".tmp")

    with open(caminho_temporario, "w", encoding="utf-8") as arquivo:
        json.dump(dados_usuario, arquivo, ensure_ascii=False, indent=2)

    caminho_temporario.replace(CAMINHO_USUARIO)


dados_usuario = carregar_dados()


# =========================================================
# CONSULTAS
# =========================================================
def esta_na_lista(nome_lista, filme):
    return chave_filme(filme) in dados_usuario[nome_lista]


def eh_favorito(filme):
    return esta_na_lista("favoritos", filme)


def foi_assistido(filme):
    return esta_na_lista("assistidos", filme)


def quer_assistir(filme):
    return esta_na_lista("quero_assistir", filme)


def filmes_da_lista(nome_lista, catalogo):
    """
    Devolve os filmes do catálogo que estão na lista,
    do adicionado mais recentemente para o mais antigo.
    """
    filmes_por_chave = {chave_filme(filme): filme for filme in catalogo}
    itens_lista = dados_usuario[nome_lista]

    # Python mantém a ordem de inserção dos dicionários: o último é o mais novo.
    chaves_mais_novas_primeiro = list(itens_lista.keys())[::-1]

    return [
        filmes_por_chave[chave]
        for chave in chaves_mais_novas_primeiro
        if chave in filmes_por_chave
    ]


def chaves_assistidas():
    return set(dados_usuario["assistidos"].keys())


# =========================================================
# ALTERAÇÕES
# =========================================================
def alternar(nome_lista, filme):
    """
    Adiciona o filme se ainda não estiver na lista, ou remove se já estiver.
    Salva no arquivo na hora. Retorna True se o filme ficou NA lista.
    """
    chave = chave_filme(filme)
    lista = dados_usuario[nome_lista]

    if chave in lista:
        del lista[chave]
        ficou_na_lista = False
    else:
        lista[chave] = {
            "nome": filme["nome"],
            "ano": filme.get("ano"),
            "adicionado_em": date.today().isoformat()
        }
        ficou_na_lista = True

        # Viu? Então sai do "Quero assistir" (a promessa foi cumprida).
        if nome_lista == "assistidos":
            dados_usuario["quero_assistir"].pop(chave, None)

    salvar_dados()
    return ficou_na_lista


def alternar_favorito(filme):
    return alternar("favoritos", filme)


def alternar_quero_assistir(filme):
    """Guarda (ou tira) o título da lista "Quero assistir". True se ficou na lista."""
    return alternar("quero_assistir", filme)


def guardar_para_depois(filme):
    """Coloca no "Quero assistir" (sem tirar se já estava). True se entrou agora."""
    if quer_assistir(filme):
        return False
    return alternar("quero_assistir", filme)


def data_em_que_guardou(filme):
    """Quando o título entrou no "Quero assistir" (um date), ou None."""
    registro = dados_usuario["quero_assistir"].get(chave_filme(filme)) or {}
    try:
        return date.fromisoformat(registro.get("adicionado_em") or "")
    except ValueError:
        return None


def alternar_assistido(filme):
    """Desmarcar como assistido também apaga a nota que você deu."""
    return alternar("assistidos", filme)


# =========================================================
# NOTA PESSOAL (1 a 5 estrelas)
# =========================================================
# A nota fica dentro do registro de "assistidos":
#   "808": {"nome": "Shrek", "ano": 2001, "adicionado_em": "...", "nota": 5}
NOTA_MINIMA = 1
NOTA_MAXIMA = 5


def obter_nota(filme):
    """Nota de 1 a 5, ou None se você ainda não avaliou."""
    registro = dados_usuario["assistidos"].get(chave_filme(filme))
    if registro is None:
        return None
    return registro.get("nota")


def definir_nota(filme, nota):
    """
    Salva a sua nota (1 a 5). Dar nota a um filme marca ele como assistido,
    afinal você só avalia o que já viu. nota=None apaga a avaliação.
    """
    if nota is not None and not (NOTA_MINIMA <= nota <= NOTA_MAXIMA):
        raise ValueError(f"A nota precisa ser de {NOTA_MINIMA} a {NOTA_MAXIMA}.")

    chave = chave_filme(filme)
    assistidos = dados_usuario["assistidos"]

    if chave not in assistidos:
        if nota is None:
            return  # nada para apagar
        assistidos[chave] = {
            "nome": filme["nome"],
            "ano": filme.get("ano"),
            "adicionado_em": date.today().isoformat()
        }
        dados_usuario["quero_assistir"].pop(chave, None)  # viu: sai do "Quero assistir"

    if nota is None:
        assistidos[chave].pop("nota", None)
    else:
        assistidos[chave]["nota"] = int(nota)
        assistidos[chave]["avaliado_em"] = date.today().isoformat()

    salvar_dados()


def filmes_avaliados(catalogo, nota=None):
    """
    Filmes com nota, da maior para a menor (empate: o avaliado por último primeiro).
    Com nota=5, só os de 5 estrelas.
    """
    assistidos_mais_novos_primeiro = filmes_da_lista("assistidos", catalogo)

    avaliados = [
        filme for filme in assistidos_mais_novos_primeiro
        if obter_nota(filme) is not None
        and (nota is None or obter_nota(filme) == nota)
    ]

    # sort é estável: quem já vinha primeiro (mais novo) continua na frente no empate
    avaliados.sort(key=obter_nota, reverse=True)
    return avaliados


def texto_estrelas(nota):
    """4 -> '★★★★☆'"""
    if nota is None:
        return "☆" * NOTA_MAXIMA
    return "★" * nota + "☆" * (NOTA_MAXIMA - nota)


# =========================================================
# MINHAS ANOTAÇÕES (o que você escreveu sobre o filme)
# =========================================================
TAMANHO_MAXIMO_ANOTACAO = 2000  # letras


def obter_anotacao(filme, sessao=None):
    """
    O texto que você escreveu sobre o filme, ou "" se ainda não escreveu nada.
    sessao=None: a 1ª vez que viu | sessao=0, 1...: cada vez que viu DE NOVO.
    """
    if sessao is not None:
        revisitas = revisitas_do_registro(chave_filme(filme))
        return revisitas[sessao].get("texto", "") if 0 <= sessao < len(revisitas) else ""
    registro = dados_usuario["anotacoes"].get(chave_filme(filme))
    return registro["texto"] if registro else ""


def definir_anotacao(filme, texto, sessao=None):
    """
    Guarda (ou apaga, se vier vazio) a sua anotação sobre o filme.
    Salva no arquivo na hora, como os favoritos.
    """
    texto = (texto or "").strip()[:TAMANHO_MAXIMO_ANOTACAO]
    chave = chave_filme(filme)

    if sessao is not None:
        revisitas = revisitas_do_registro(chave)
        if 0 <= sessao < len(revisitas) and revisitas[sessao].get("texto", "") != texto:
            revisitas[sessao]["texto"] = texto
            salvar_dados()
        return
    anotacoes = dados_usuario["anotacoes"]

    if texto == "":
        if chave in anotacoes:
            del anotacoes[chave]
            salvar_dados()
        return

    if anotacoes.get(chave, {}).get("texto") == texto:
        return  # nada mudou: não precisa gravar de novo

    anotacoes[chave] = {
        "nome": filme["nome"],
        "texto": texto,
        "atualizado_em": date.today().isoformat()
    }
    salvar_dados()


def data_do_registro(chave):
    """A data guardada em "assistidos" para essa chave (um date), ou None."""
    registro = dados_usuario["assistidos"].get(chave) or {}
    try:
        return date.fromisoformat(registro.get("adicionado_em") or "")
    except ValueError:
        return None


# ---------------- Sessões: a 1ª vez + cada "vi de novo" ----------------
# No usuario.json, quem você viu de novo ganha uma lista dentro do registro:
#   "808": {"nome": "Shrek", "adicionado_em": "2019-05-02", "nota": 5,
#           "revisitas": [{"data": "2026-10-03", "texto": "ainda engraçado!"}]}
# Cada sessão vira uma entrada do diário. sessao=None é a 1ª vez; 0, 1... as revisitas.
def revisitas_do_registro(chave):
    """As revisitas de um título (lista vazia se nunca viu de novo). Só lê: não muda o arquivo."""
    registro = dados_usuario["assistidos"].get(chave)
    if registro is None:
        return []
    return registro.get("revisitas") or []


def data_da_sessao(chave, sessao=None):
    if sessao is None:
        return data_do_registro(chave)
    revisitas = revisitas_do_registro(chave)
    if not 0 <= sessao < len(revisitas):
        return None
    try:
        return date.fromisoformat(revisitas[sessao].get("data") or "")
    except ValueError:
        return None


def sessoes_em_ordem_cronologica():
    """
    Todas as sessões [(chave, sessao)], da mais antiga para a mais nova, pela data.
    Mesma data: vale a ordem em que foram marcadas. Sem data vai para o fim.
    """
    sessoes = []
    for posicao, chave in enumerate(dados_usuario["assistidos"]):
        sessoes.append((chave, None, posicao, -1))
        for indice in range(len(revisitas_do_registro(chave))):
            sessoes.append((chave, indice, posicao, indice))
    sessoes.sort(key=lambda item: (data_da_sessao(item[0], item[1]) or date.max, item[2], item[3]))
    return [(chave, sessao) for chave, sessao, _, _ in sessoes]


def chaves_em_ordem_cronologica():
    """Os títulos vistos do mais antigo para o mais novo (pela 1ª vez que você viu)."""
    return [chave for chave, sessao in sessoes_em_ordem_cronologica() if sessao is None]


def numero_da_entrada(filme, sessao=None):
    """
    "Entrada" no seu diário: a sessão mais antiga é a entrada 1, a seguinte a 2...
    (pela data). sessao=None é a 1ª vez que você viu o título. None se não viu.
    """
    procurada = (chave_filme(filme), sessao)
    for posicao, sessao_vista in enumerate(sessoes_em_ordem_cronologica(), start=1):
        if sessao_vista == procurada:
            return posicao
    return None


def quantas_vezes_viu(filme):
    """0 (não viu), 1 (viu uma vez), 2 (viu de novo)..."""
    chave = chave_filme(filme)
    if chave not in dados_usuario["assistidos"]:
        return 0
    return 1 + len(revisitas_do_registro(chave))


def registrar_revisita(filme, data_vista=None):
    """
    "Vi de novo": nova sessão com a data de hoje (ou a informada).
    Se você ainda não tinha visto, só marca como visto. Devolve o índice da sessão
    nova (0, 1...) ou None quando foi a 1ª vez. Também sai do "Quero assistir".
    """
    chave = chave_filme(filme)
    if chave not in dados_usuario["assistidos"]:
        alternar("assistidos", filme)
        return None
    data_vista = data_vista or date.today()
    revisitas = dados_usuario["assistidos"][chave].setdefault("revisitas", [])
    revisitas.append({"data": data_vista.isoformat(), "texto": ""})
    dados_usuario["quero_assistir"].pop(chave, None)
    salvar_dados()
    return len(revisitas) - 1


def apagar_revisita(filme, sessao):
    revisitas = revisitas_do_registro(chave_filme(filme))
    if 0 <= sessao < len(revisitas):
        del revisitas[sessao]
        salvar_dados()


DATA_MAIS_ANTIGA_PERMITIDA = date(1900, 1, 1)


def definir_data_assistido(filme, nova_data, sessao=None):
    """
    Corrige o dia em que você viu o título (ex.: marcou hoje algo que viu em 2015).
    sessao=None corrige a 1ª vez; 0, 1... corrigem cada "vi de novo".
    Não aceita data no futuro nem título que você ainda não marcou como visto.
    """
    chave = chave_filme(filme)
    if chave not in dados_usuario["assistidos"]:
        raise ValueError("Esse título ainda não está marcado como visto.")
    if nova_data > date.today():
        raise ValueError("Essa data ainda não chegou. 🙂")
    if nova_data < DATA_MAIS_ANTIGA_PERMITIDA:
        raise ValueError("Essa data é antiga demais.")
    if sessao is None:
        dados_usuario["assistidos"][chave]["adicionado_em"] = nova_data.isoformat()
    else:
        revisitas = revisitas_do_registro(chave)
        if not 0 <= sessao < len(revisitas):
            raise ValueError("Essa sessão não existe mais.")
        revisitas[sessao]["data"] = nova_data.isoformat()
    salvar_dados()



# =========================================================
# DIÁRIO AUTOMÁTICO (uma entrada para cada título visto)
# =========================================================
ORDEM_DIARIO_RECENTES = "recentes"
ORDEM_DIARIO_ANTIGOS = "antigos"
ORDEM_DIARIO_NOTA = "nota"


def data_em_que_assistiu(filme):
    """A data em que você viu (um date), ou None."""
    return data_do_registro(chave_filme(filme))


def entradas_do_diario(catalogo, ordem=ORDEM_DIARIO_RECENTES):
    """
    Cada SESSÃO vira uma entrada do diário (a 1ª vez e cada "vi de novo"):
        {"filme", "numero", "data", "nota", "anotacao", "sessao", "vez"}
    "vez": 1 = primeira vez, 2 = segunda...

    O número da entrada segue a data (a sessão mais antiga = #1)
    e não muda quando você troca a ordem de exibição.
    Ordens: "recentes" (padrão), "antigos" ou "nota" (5★ primeiro; sem nota no fim).
    """
    filmes_por_chave = {chave_filme(filme): filme for filme in catalogo}

    entradas = []
    vezes_por_chave = {}
    for numero, (chave, sessao) in enumerate(sessoes_em_ordem_cronologica(), start=1):
        vezes_por_chave[chave] = vezes_por_chave.get(chave, 0) + 1
        filme = filmes_por_chave.get(chave)
        if filme is None:
            continue  # saiu do catálogo: o número dele continua reservado
        entradas.append({
            "filme": filme,
            "numero": numero,
            "data": data_da_sessao(chave, sessao),
            "nota": obter_nota(filme),
            "anotacao": obter_anotacao(filme, sessao),
            "sessao": sessao,
            "vez": vezes_por_chave[chave],
        })

    if ordem == ORDEM_DIARIO_ANTIGOS:
        return entradas

    entradas.reverse()  # mais recentes primeiro
    if ordem == ORDEM_DIARIO_NOTA:
        # sort é estável: no empate, o visto por último continua na frente
        entradas.sort(key=lambda entrada: entrada["nota"] or 0, reverse=True)
    return entradas


# =========================================================
# CAPA DO DIÁRIO (seu nome + estatísticas)
# =========================================================
TAMANHO_MAXIMO_NOME = 40
MINIMO_PARA_DESTAQUE = 2   # "diretor que mais aparece" só com 2 títulos ou mais


def obter_nome_do_dono():
    return dados_usuario["configuracoes"].get("nome_do_dono", "")


def definir_nome_do_dono(nome):
    nome = " ".join((nome or "").split())[:TAMANHO_MAXIMO_NOME]
    if nome:
        dados_usuario["configuracoes"]["nome_do_dono"] = nome
    else:
        dados_usuario["configuracoes"].pop("nome_do_dono", None)
    salvar_dados()


# ---------------- Meus streamings (os que você assina) ----------------
def obter_meus_streamings():
    return list(dados_usuario["configuracoes"].get("meus_streamings", []))


def definir_meus_streamings(nomes):
    nomes_limpos = []
    for nome in nomes:
        if nome and nome not in nomes_limpos:
            nomes_limpos.append(nome)
    dados_usuario["configuracoes"]["meus_streamings"] = nomes_limpos
    salvar_dados()


def separar_nomes(texto):
    """'Ação, Aventura' -> ['Ação', 'Aventura']"""
    return [parte.strip() for parte in (texto or "").split(",") if parte.strip()]


def mais_frequente(contagem):
    """{'Drama': 3, 'Ação': 3, 'Terror': 1} -> ('Drama', 3) (empate: o que apareceu primeiro)."""
    if not contagem:
        return None
    nome = max(contagem, key=contagem.get)  # max devolve o primeiro em caso de empate
    return nome, contagem[nome]


def minutos_do_titulo(filme):
    """
    Filme: a duração. Série: episódios × duração de um episódio (uma estimativa,
    porque não sabemos quantos episódios você viu). None se faltar informação.
    """
    duracao = filme.get("duracao_minutos")
    if not duracao:
        return None
    if filme.get("tipo") == "serie":
        episodios = filme.get("episodios")
        return episodios * duracao if episodios else None
    return duracao


def estatisticas_do_diario(catalogo):
    """
    Os números da capa do diário, calculados só com o que você marcou:
        total, filmes, series, nota_media, avaliados, horas, horas_estimadas,
        genero (nome, quantidade), pessoa (nome, quantidade), mes (date, quantidade),
        melhor (entrada), primeira_data, anotacoes, favoritos, quero_assistir,
        sessoes (todas as vezes que viu), revistos (títulos vistos mais de uma vez)
    Títulos contam uma vez só; horas e meses contam cada sessão ("vi de novo" também).
    """
    sessoes = entradas_do_diario(catalogo, ORDEM_DIARIO_ANTIGOS)
    entradas = [sessao for sessao in sessoes if sessao["sessao"] is None]   # 1ª vez de cada título

    contagem_generos = {}
    contagem_pessoas = {}
    contagem_meses = {}
    minutos = 0
    tem_estimativa = False

    for entrada in sessoes:
        filme = entrada["filme"]
        primeira_vez = entrada["sessao"] is None   # gêneros e pessoas contam o título uma vez só
        for genero in separar_nomes(filme.get("genero")) if primeira_vez else []:
            contagem_generos[genero] = contagem_generos.get(genero, 0) + 1
        for pessoa in separar_nomes(filme.get("diretor")) if primeira_vez else []:
            contagem_pessoas[pessoa] = contagem_pessoas.get(pessoa, 0) + 1
        if entrada["data"] is not None:
            mes = entrada["data"].replace(day=1)
            contagem_meses[mes] = contagem_meses.get(mes, 0) + 1

        minutos_vistos = minutos_do_titulo(filme)
        if minutos_vistos:
            minutos += minutos_vistos
            tem_estimativa = tem_estimativa or filme.get("tipo") == "serie"

    notas = [entrada["nota"] for entrada in entradas if entrada["nota"] is not None]
    series = sum(1 for entrada in entradas if entrada["filme"].get("tipo") == "serie")

    pessoa = mais_frequente(contagem_pessoas)
    if pessoa is not None and pessoa[1] < MINIMO_PARA_DESTAQUE:
        pessoa = None

    # Título mais bem avaliado: maior nota; no empate, o visto por último.
    avaliadas = [entrada for entrada in entradas if entrada["nota"] is not None]
    melhor = max(reversed(avaliadas), key=lambda entrada: entrada["nota"]) if avaliadas else None

    datas = [sessao["data"] for sessao in sessoes if sessao["data"] is not None]

    return {
        "total": len(entradas),
        "filmes": len(entradas) - series,
        "series": series,
        "avaliados": len(notas),
        "nota_media": round(sum(notas) / len(notas), 1) if notas else None,
        "horas": round(minutos / 60),
        "horas_estimadas": tem_estimativa,
        "genero": mais_frequente(contagem_generos),
        "pessoa": pessoa,
        "mes": mais_frequente(contagem_meses),
        "melhor": melhor,
        "primeira_data": min(datas) if datas else None,
        "anotacoes": len(dados_usuario["anotacoes"]),
        "favoritos": len(filmes_da_lista("favoritos", catalogo)),
        "quero_assistir": len(filmes_da_lista("quero_assistir", catalogo)),
        "sessoes": len(sessoes),
        "revistos": sum(1 for entrada in entradas if quantas_vezes_viu(entrada["filme"]) > 1),
    }


# =========================================================
# RETROSPECTIVA DO ANO (o "Wrapped" do diário)
# =========================================================
# Só entram as sessões com data naquele ano: a 1ª vez de um título e também
# cada "vi de novo". Assim, rever Shrek em 2026 conta no ano de 2026.
QUANTIDADE_GENEROS_RETROSPECTIVA = 3
MINIMO_DIA_CHEIO = 2          # "dia mais cinéfilo" só aparece com 2 sessões ou mais


def anos_do_diario(catalogo):
    """Os anos que têm alguma sessão no diário, do mais novo para o mais antigo."""
    anos = {entrada["data"].year for entrada in entradas_do_diario(catalogo) if entrada["data"] is not None}
    return sorted(anos, reverse=True)


def ano_padrao_da_retrospectiva(catalogo, hoje=None):
    """O ano de hoje, se já tiver algo nele; senão, o ano mais recente do diário (ou None)."""
    hoje = hoje or date.today()
    anos = anos_do_diario(catalogo)
    if not anos:
        return None
    return hoje.year if hoje.year in anos else anos[0]


def contagem_ordenada(contagem):
    """{'Drama': 2, 'Ação': 3} -> [('Ação', 3), ('Drama', 2)] (empate: quem apareceu primeiro)."""
    ordem = {nome: posicao for posicao, nome in enumerate(contagem)}
    return sorted(contagem.items(), key=lambda par: (-par[1], ordem[par[0]]))


def anotacao_em_destaque(sessoes):
    """
    A anotação que abre a página "nas suas palavras": a do título com a maior nota;
    no empate, a mais longa. None se você não escreveu nada naquele ano.
    """
    anotadas = [sessao for sessao in sessoes if (sessao["anotacao"] or "").strip()]
    if not anotadas:
        return None
    return max(anotadas, key=lambda sessao: (sessao["nota"] or 0, len(sessao["anotacao"].split())))


def retrospectiva_do_ano(catalogo, ano):
    """
    Os números de UM ano do diário:
        ano, sessoes, titulos, novos, filmes, series, horas, horas_estimadas,
        meses (12 contagens, jan..dez), mes (nº do mês, quantidade) ou None,
        generos [(nome, quantidade)] (até 3), pessoa (nome, quantidade) ou None,
        melhor (entrada), nota_media, anotacao (entrada) ou None,
        primeira e ultima (entradas), dia (date, quantidade) ou None,
        revistos [entradas de "vi de novo" no ano], anotacoes (quantas sessões anotadas)
    Devolve None se o ano não tem nenhuma sessão.
    """
    sessoes = [
        entrada for entrada in entradas_do_diario(catalogo, ORDEM_DIARIO_ANTIGOS)
        if entrada["data"] is not None and entrada["data"].year == ano
    ]
    if not sessoes:
        return None

    # Cada título conta uma vez (a sessão mais antiga dele no ano).
    titulos = {}
    for sessao in sessoes:
        titulos.setdefault(chave_filme(sessao["filme"]), sessao)
    entradas_dos_titulos = list(titulos.values())

    contagem_meses = [0] * 12
    contagem_dias = {}
    contagem_generos = {}
    contagem_pessoas = {}
    minutos = 0
    tem_estimativa = False

    for sessao in sessoes:
        contagem_meses[sessao["data"].month - 1] += 1
        contagem_dias[sessao["data"]] = contagem_dias.get(sessao["data"], 0) + 1
        minutos_vistos = minutos_do_titulo(sessao["filme"])
        if minutos_vistos:
            minutos += minutos_vistos
            tem_estimativa = tem_estimativa or sessao["filme"].get("tipo") == "serie"

    for entrada in entradas_dos_titulos:
        for genero in separar_nomes(entrada["filme"].get("genero")):
            contagem_generos[genero] = contagem_generos.get(genero, 0) + 1
        for pessoa in separar_nomes(entrada["filme"].get("diretor")):
            contagem_pessoas[pessoa] = contagem_pessoas.get(pessoa, 0) + 1

    mes = None
    if max(contagem_meses) > 0:
        numero_mes = contagem_meses.index(max(contagem_meses)) + 1   # empate: o mês mais cedo
        mes = (numero_mes, max(contagem_meses))

    pessoa = mais_frequente(contagem_pessoas)
    if pessoa is not None and pessoa[1] < MINIMO_PARA_DESTAQUE:
        pessoa = None

    dia = mais_frequente(contagem_dias)
    if dia is not None and dia[1] < MINIMO_DIA_CHEIO:
        dia = None

    avaliadas = [entrada for entrada in entradas_dos_titulos if entrada["nota"] is not None]
    melhor = max(reversed(avaliadas), key=lambda entrada: entrada["nota"]) if avaliadas else None
    notas = [entrada["nota"] for entrada in avaliadas]

    series = sum(1 for entrada in entradas_dos_titulos if entrada["filme"].get("tipo") == "serie")

    return {
        "ano": ano,
        "sessoes": len(sessoes),
        "titulos": len(entradas_dos_titulos),
        "novos": sum(1 for sessao in sessoes if sessao["sessao"] is None),
        "filmes": len(entradas_dos_titulos) - series,
        "series": series,
        "horas": round(minutos / 60),
        "horas_estimadas": tem_estimativa,
        "meses": contagem_meses,
        "mes": mes,
        "generos": contagem_ordenada(contagem_generos)[:QUANTIDADE_GENEROS_RETROSPECTIVA],
        "pessoa": pessoa,
        "melhor": melhor,
        "nota_media": round(sum(notas) / len(notas), 1) if notas else None,
        "anotacao": anotacao_em_destaque(sessoes),
        "anotacoes": sum(1 for sessao in sessoes if (sessao["anotacao"] or "").strip()),
        "primeira": sessoes[0],
        "ultima": sessoes[-1],
        "dia": dia,
        "revistos": [sessao for sessao in sessoes if sessao["sessao"] is not None],
    }


# =========================================================
# BACKUP DO DIÁRIO (cópias com data, em dados/backups/)
# =========================================================
# Cada backup é UM arquivo com tudo: favoritos, diário, notas, anotações,
# listas e as conversas. Assim dá para voltar no tempo se algo der errado.
#   - automático: ao abrir o CineAI, se o último tiver mais de 7 dias;
#   - manual: botão na Capa do Meu diário.
# Só os 10 mais novos ficam guardados.
PASTA_BACKUPS = PASTA_DADOS / "backups"
MAXIMO_BACKUPS = 10
DIAS_ENTRE_BACKUPS_AUTOMATICOS = 7
PREFIXO_BACKUP = "diario_"
FORMATO_DATA_BACKUP = "%Y-%m-%d_%H%M%S"


def caminho_das_conversas():
    return PASTA_DADOS / "conversas.json"


def listar_backups():
    """Backups do mais novo para o mais antigo: [(caminho, datetime)]."""
    if not PASTA_BACKUPS.exists():
        return []
    backups = []
    for caminho in PASTA_BACKUPS.glob(f"{PREFIXO_BACKUP}*.json"):
        try:
            momento = datetime.strptime(caminho.stem[len(PREFIXO_BACKUP):], FORMATO_DATA_BACKUP)
        except ValueError:
            continue
        backups.append((caminho, momento))
    backups.sort(key=lambda par: par[1], reverse=True)
    return backups


def ultimo_backup():
    backups = listar_backups()
    return backups[0][1] if backups else None


def fazer_backup(momento=None):
    """Guarda uma cópia de tudo agora. Devolve o caminho do arquivo criado."""
    momento = momento or datetime.now()
    PASTA_BACKUPS.mkdir(parents=True, exist_ok=True)

    conversas_salvas = []
    if caminho_das_conversas().exists():
        try:
            conversas_salvas = json.loads(caminho_das_conversas().read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            conversas_salvas = []

    conteudo = {
        "criado_em": momento.isoformat(timespec="seconds"),
        "usuario": dados_usuario,
        "conversas": conversas_salvas,
    }
    caminho = PASTA_BACKUPS / f"{PREFIXO_BACKUP}{momento.strftime(FORMATO_DATA_BACKUP)}.json"
    while caminho.exists():   # dois backups no mesmo segundo: um não pode apagar o outro
        momento += timedelta(seconds=1)
        caminho = PASTA_BACKUPS / f"{PREFIXO_BACKUP}{momento.strftime(FORMATO_DATA_BACKUP)}.json"
    conteudo["criado_em"] = momento.isoformat(timespec="seconds")
    caminho.write_text(json.dumps(conteudo, ensure_ascii=False, indent=2), encoding="utf-8")

    for caminho_antigo, _ in listar_backups()[MAXIMO_BACKUPS:]:
        caminho_antigo.unlink(missing_ok=True)
    return caminho


def backup_automatico_se_precisar(agora=None):
    """Faz backup se nunca foi feito ou se o último tem mais de 7 dias (e se há algo a guardar)."""
    agora = agora or datetime.now()
    tem_algo = any(dados_usuario.get(nome_lista) for nome_lista in LISTAS)
    if not tem_algo:
        return None
    ultimo = ultimo_backup()
    if ultimo is not None and agora - ultimo < timedelta(days=DIAS_ENTRE_BACKUPS_AUTOMATICOS):
        return None
    return fazer_backup(agora)


def resumo_do_backup(caminho):
    """'12 entradas · 5 favoritos · 3 anotações' (para a lista de backups)."""
    try:
        conteudo = json.loads(Path(caminho).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return "arquivo com problema"
    dados = conteudo.get("usuario", {})
    return (
        f"{len(dados.get('assistidos', {}))} vistos · {len(dados.get('favoritos', {}))} favoritos · "
        f"{len(dados.get('anotacoes', {}))} anotações"
    )


def restaurar_backup(caminho):
    """
    Volta o diário (e as conversas) para como estavam no backup.
    Antes, guarda um backup do estado atual: dá para desfazer a restauração.
    """
    global dados_usuario
    conteudo = json.loads(Path(caminho).read_text(encoding="utf-8"))

    fazer_backup(datetime.now())   # rede de segurança

    dados_restaurados = criar_dados_vazios()
    for nome_lista in LISTAS:
        lista = conteudo.get("usuario", {}).get(nome_lista, {})
        if isinstance(lista, dict):
            dados_restaurados[nome_lista] = lista
    dados_usuario = dados_restaurados
    salvar_dados()

    caminho_das_conversas().write_text(
        json.dumps(conteudo.get("conversas", []), ensure_ascii=False, indent=2), encoding="utf-8"
    )