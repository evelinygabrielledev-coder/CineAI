"""
Dados pessoais do usuário do CineAI: favoritos e filmes já assistidos.

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
from datetime import date
from pathlib import Path


# Os testes automáticos usam outra pasta para não mexer nos seus dados.
PASTA_DADOS = Path(os.environ.get("CINEAI_PASTA_USUARIO", Path(__file__).resolve().parent))
CAMINHO_USUARIO = PASTA_DADOS / "usuario.json"

LISTAS = ("favoritos", "assistidos", "anotacoes")  # anotacoes = "Minhas anotações" de cada filme


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

    salvar_dados()
    return ficou_na_lista


def alternar_favorito(filme):
    return alternar("favoritos", filme)


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


def obter_anotacao(filme):
    """O texto que você escreveu sobre o filme, ou "" se ainda não escreveu nada."""
    registro = dados_usuario["anotacoes"].get(chave_filme(filme))
    return registro["texto"] if registro else ""


def definir_anotacao(filme, texto):
    """
    Guarda (ou apaga, se vier vazio) a sua anotação sobre o filme.
    Salva no arquivo na hora, como os favoritos.
    """
    texto = (texto or "").strip()[:TAMANHO_MAXIMO_ANOTACAO]
    chave = chave_filme(filme)
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


def numero_da_entrada(filme):
    """
    "Entrada" do filme no seu diário: o 1º filme que você marcou como visto é a
    entrada 1, o 2º é a 2... (na ordem em que foram marcados). None se não viu.
    """
    chave = chave_filme(filme)
    for posicao, chave_vista in enumerate(dados_usuario["assistidos"], start=1):
        if chave_vista == chave:
            return posicao
    return None



# =========================================================
# DIÁRIO AUTOMÁTICO (uma entrada para cada título visto)
# =========================================================
ORDEM_DIARIO_RECENTES = "recentes"
ORDEM_DIARIO_ANTIGOS = "antigos"
ORDEM_DIARIO_NOTA = "nota"


def data_em_que_assistiu(filme):
    """A data guardada quando você marcou como visto (um date), ou None."""
    registro = dados_usuario["assistidos"].get(chave_filme(filme)) or {}
    try:
        return date.fromisoformat(registro.get("adicionado_em") or "")
    except ValueError:
        return None


def entradas_do_diario(catalogo, ordem=ORDEM_DIARIO_RECENTES):
    """
    Cada título visto vira uma entrada do diário:
        {"filme", "numero", "data", "nota", "anotacao"}

    O número da entrada segue a ordem em que você marcou (1º visto = #1),
    e nunca muda, mesmo que você troque a ordem de exibição.
    Ordens: "recentes" (padrão), "antigos" ou "nota" (5★ primeiro; sem nota no fim).
    """
    filmes_por_chave = {chave_filme(filme): filme for filme in catalogo}

    entradas = []
    for numero, chave in enumerate(dados_usuario["assistidos"], start=1):
        filme = filmes_por_chave.get(chave)
        if filme is None:
            continue  # saiu do catálogo: o número dele continua reservado
        entradas.append({
            "filme": filme,
            "numero": numero,
            "data": data_em_que_assistiu(filme),
            "nota": obter_nota(filme),
            "anotacao": obter_anotacao(filme),
        })

    if ordem == ORDEM_DIARIO_ANTIGOS:
        return entradas

    entradas.reverse()  # mais recentes primeiro
    if ordem == ORDEM_DIARIO_NOTA:
        # sort é estável: no empate, o visto por último continua na frente
        entradas.sort(key=lambda entrada: entrada["nota"] or 0, reverse=True)
    return entradas