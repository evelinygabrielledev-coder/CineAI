"""
letterboxd.py — traz o seu histórico do Letterboxd para o diário do CineAI.

No Letterboxd: Settings › Data › Export your data. Ele baixa um .zip com:
    diary.csv      cada vez que você registrou um filme (data, nota, "rewatch")
    watched.csv    todos os filmes marcados como vistos
    ratings.csv    a sua nota atual de cada filme (0,5 a 5 estrelas)
    reviews.csv    as suas resenhas (viram anotações no diário)
    watchlist.csv  a lista "quero ver"
    likes/films.csv os filmes que você curtiu (viram favoritos)

O que este módulo faz com isso:
    - cada filme vira uma entrada do diário, com a data em que você viu;
    - cada registro a mais no diary.csv vira um "vi de novo" (revisita);
    - a nota vira estrelas (meia estrela arredondada para cima: 3,5 -> 4);
    - a resenha vira a anotação daquela sessão;
    - curtidos -> favoritos; watchlist -> Quero assistir.

Nada do que você já tem no CineAI é apagado: notas e anotações que já existem
ficam como estão, e importar o mesmo arquivo de novo não duplica nada.
Antes de mexer, o CineAI faz um backup do diário.

Os filmes são achados no catálogo pelo nome e ano (em português ou o título
original). O que não estiver no catálogo aparece no resumo; o
importadores/importar_letterboxd.py --adicionar busca esses no TMDB e coloca no catálogo.
"""
import csv
import html
import io
import re
import unicodedata
import zipfile
from datetime import date
from pathlib import Path

from cineai import usuario

ARQUIVOS = {
    "diario": "diary.csv",
    "vistos": "watched.csv",
    "notas": "ratings.csv",
    "resenhas": "reviews.csv",
    "quero_ver": "watchlist.csv",
    "curtidos": "films.csv",          # fica em likes/films.csv
}


# =========================================================
# 1. Ler a exportação (o .zip ou a pasta já descompactada)
# =========================================================
def ler_csv(texto):
    return list(csv.DictReader(io.StringIO(texto.lstrip("﻿"))))


def ler_exportacao(caminho):
    """{"diario": [linhas], "vistos": [...], ...} (listas vazias para o que faltar)."""
    caminho = Path(caminho)
    conteudos = {}

    def guardar(nome_arquivo, texto, dentro_de_likes):
        for chave, esperado in ARQUIVOS.items():
            if nome_arquivo == esperado and (chave != "curtidos" or dentro_de_likes):
                conteudos[chave] = ler_csv(texto)

    if caminho.is_dir():
        for arquivo in caminho.rglob("*.csv"):
            guardar(arquivo.name, arquivo.read_text(encoding="utf-8"), "likes" in arquivo.parts)
    elif zipfile.is_zipfile(caminho):
        with zipfile.ZipFile(caminho) as pacote:
            for nome in pacote.namelist():
                if nome.lower().endswith(".csv"):
                    partes = nome.replace("\\", "/").split("/")
                    guardar(partes[-1], pacote.read(nome).decode("utf-8"), "likes" in partes)
    elif caminho.suffix.lower() == ".csv":
        guardar(caminho.name, caminho.read_text(encoding="utf-8"), False)
    else:
        raise ValueError("Escolha o .zip que o Letterboxd baixou (ou a pasta dele descompactada).")

    if not any(conteudos.values()):
        raise ValueError("Não achei os arquivos do Letterboxd (diary.csv, watched.csv...) aí dentro.")
    return {chave: conteudos.get(chave, []) for chave in ARQUIVOS}


# =========================================================
# 2. Achar cada filme no catálogo
# =========================================================
def simplificar(texto):
    texto = unicodedata.normalize("NFD", str(texto or "").lower())
    texto = "".join(caractere for caractere in texto if unicodedata.category(caractere) != "Mn")
    texto = texto.replace("&", " and ")
    return " ".join(re.findall(r"[a-z0-9]+", texto))


def ano_da_linha(linha):
    try:
        return int(linha.get("Year") or 0) or None
    except ValueError:
        return None


class Localizador:
    """Acha um filme do catálogo pelo nome + ano (ou pelo id do TMDB, se souber)."""

    def __init__(self, catalogo, buscar_id=None):
        self.por_nome_ano = {}
        self.por_nome = {}
        self.por_id = {}
        self.buscar_id = buscar_id   # função opcional (nome, ano) -> id do TMDB
        for filme in catalogo:
            if filme.get("tipo") == "serie":
                continue   # o Letterboxd só tem filmes
            if filme.get("id") is not None:
                self.por_id[filme["id"]] = filme
            for titulo in {filme.get("nome"), filme.get("titulo_original"), filme.get("titulo_letterboxd")}:
                if titulo:
                    chave = simplificar(titulo)
                    self.por_nome_ano.setdefault((chave, filme.get("ano")), filme)
                    self.por_nome.setdefault(chave, []).append(filme)

    def achar(self, nome, ano):
        chave = simplificar(nome)
        for ano_tentado in (ano, (ano or 0) + 1, (ano or 0) - 1):   # o ano às vezes difere em 1
            if (chave, ano_tentado) in self.por_nome_ano:
                return self.por_nome_ano[(chave, ano_tentado)]
        candidatos = {id(filme): filme for filme in self.por_nome.get(chave, [])}
        if len(candidatos) == 1 and ano is None:
            return next(iter(candidatos.values()))
        if self.buscar_id is not None:
            id_tmdb = self.buscar_id(nome, ano)
            if id_tmdb in self.por_id:
                return self.por_id[id_tmdb]
        return None


# =========================================================
# 3. Converter os valores
# =========================================================
def converter_nota(texto):
    """'3.5' -> 4 | '0.5' -> 1 | '' -> None (meia estrela arredondada para cima)."""
    try:
        valor = float(texto)
    except (TypeError, ValueError):
        return None
    if valor <= 0:
        return None
    return max(usuario.NOTA_MINIMA, min(usuario.NOTA_MAXIMA, int(valor + 0.5)))


def converter_data(texto):
    try:
        return date.fromisoformat((texto or "").strip()[:10])
    except ValueError:
        return None


def limpar_resenha(texto):
    """Tira as marcações HTML (<i>, <br>...) que o Letterboxd deixa nas resenhas."""
    texto = re.sub(r"<br\s*/?>", "\n", texto or "", flags=re.IGNORECASE)
    texto = re.sub(r"<[^>]+>", "", texto)
    texto = html.unescape(texto)
    return "\n".join(linha.strip() for linha in texto.strip().splitlines()).strip()[:usuario.TAMANHO_MAXIMO_ANOTACAO]


# =========================================================
# 4. Importar
# =========================================================
def sessoes_por_filme(exportacao, localizador, nao_encontrados):
    """
    {chave do filme: (filme, [(data, texto da resenha)])}, em ordem de data.
    Vem do diary.csv (uma linha por vez que viu) + reviews.csv (as resenhas).
    Filmes só do watched.csv entram com a data em que foram marcados.
    """
    resenhas = {}
    for linha in exportacao["resenhas"]:
        chave = (linha.get("Name"), linha.get("Year"), linha.get("Watched Date") or linha.get("Date"))
        resenhas[chave] = limpar_resenha(linha.get("Review"))

    sessoes = {}

    def anotar(linha, data, texto):
        filme = localizador.achar(linha.get("Name"), ano_da_linha(linha))
        if filme is None:
            nao_encontrados.add(f'{linha.get("Name")} ({linha.get("Year")})')
            return
        chave = usuario.chave_filme(filme)
        sessoes.setdefault(chave, (filme, []))[1].append((data, texto))

    for linha in exportacao["diario"]:
        data = converter_data(linha.get("Watched Date")) or converter_data(linha.get("Date"))
        texto = resenhas.get((linha.get("Name"), linha.get("Year"), linha.get("Watched Date") or linha.get("Date")), "")
        anotar(linha, data, texto)

    # Resenhas sem linha no diário (dá para resenhar sem registrar a data)
    no_diario = {(linha.get("Name"), linha.get("Year"), linha.get("Watched Date") or linha.get("Date"))
                 for linha in exportacao["diario"]}
    for linha in exportacao["resenhas"]:
        chave = (linha.get("Name"), linha.get("Year"), linha.get("Watched Date") or linha.get("Date"))
        if chave not in no_diario:
            anotar(linha, converter_data(chave[2]), resenhas[chave])

    # Vistos sem nenhum registro no diário
    for linha in exportacao["vistos"]:
        filme = localizador.achar(linha.get("Name"), ano_da_linha(linha))
        if filme is None:
            nao_encontrados.add(f'{linha.get("Name")} ({linha.get("Year")})')
            continue
        if usuario.chave_filme(filme) not in sessoes:
            sessoes[usuario.chave_filme(filme)] = (filme, [(converter_data(linha.get("Date")), "")])

    for filme, lista in sessoes.values():
        lista.sort(key=lambda sessao: sessao[0] or date.max)
    return sessoes


def importar(catalogo, caminho, buscar_id=None, simular=False, hoje=None):
    """
    Lê a exportação e junta ao diário. Devolve um resumo:
        filmes, sessoes, notas, anotacoes, favoritos, quero_assistir,
        nao_encontrados (lista "Nome (ano)"), backup (caminho ou None)
    simular=True só conta o que aconteceria, sem gravar nada.
    """
    hoje = hoje or date.today()
    exportacao = ler_exportacao(caminho)
    localizador = Localizador(catalogo, buscar_id)
    nao_encontrados = set()
    resumo = {"filmes": 0, "sessoes": 0, "notas": 0, "anotacoes": 0, "favoritos": 0,
              "quero_assistir": 0, "nao_encontrados": [], "backup": None}

    dados = usuario.dados_usuario
    if simular:
        import copy
        dados = copy.deepcopy(dados)
    elif any(dados[lista] for lista in ("assistidos", "favoritos", "quero_assistir", "anotacoes")):
        resumo["backup"] = usuario.fazer_backup()   # para dar para voltar atrás

    assistidos, anotacoes = dados["assistidos"], dados["anotacoes"]

    def registro_basico(filme, quando):
        return {"nome": filme["nome"], "ano": filme.get("ano"), "adicionado_em": (quando or hoje).isoformat()}

    # ---------- sessões (1ª vez + revisitas) e resenhas ----------
    for chave, (filme, sessoes) in sessoes_por_filme(exportacao, localizador, nao_encontrados).items():
        novo_no_diario = chave not in assistidos
        if novo_no_diario:
            primeira_data, primeiro_texto = sessoes[0]
            assistidos[chave] = registro_basico(filme, primeira_data)
            dados["quero_assistir"].pop(chave, None)
            resumo["filmes"] += 1
            resumo["sessoes"] += 1
            if primeiro_texto and chave not in anotacoes:
                anotacoes[chave] = {"nome": filme["nome"], "texto": primeiro_texto, "atualizado_em": hoje.isoformat()}
                resumo["anotacoes"] += 1
            restantes = sessoes[1:]
        else:
            restantes = sessoes
            # Marcou no CineAI depois (ex.: hoje), mas no Letterboxd consta que viu antes:
            # a 1ª vez passa a ser a data do Letterboxd (é a mesma sessão, só registrada antes).
            primeira_data_lb = sessoes[0][0]
            data_no_cineai = converter_data(assistidos[chave].get("adicionado_em"))
            if primeira_data_lb and data_no_cineai and primeira_data_lb < data_no_cineai \
                    and not assistidos[chave].get("revisitas"):
                assistidos[chave]["adicionado_em"] = primeira_data_lb.isoformat()
                if sessoes[0][1] and chave not in anotacoes:
                    anotacoes[chave] = {"nome": filme["nome"], "texto": sessoes[0][1], "atualizado_em": hoje.isoformat()}
                    resumo["anotacoes"] += 1
                restantes = sessoes[1:]

        registro = assistidos[chave]
        revisitas = registro.setdefault("revisitas", [])
        datas_que_ja_existem = {registro.get("adicionado_em")} | {revisita.get("data") for revisita in revisitas}
        for data, texto in restantes:
            data_texto = (data or hoje).isoformat()
            if data_texto in datas_que_ja_existem:
                # Essa sessão já está no diário: só completa a anotação, se faltar.
                if texto and data_texto == registro.get("adicionado_em") and chave not in anotacoes:
                    anotacoes[chave] = {"nome": filme["nome"], "texto": texto, "atualizado_em": hoje.isoformat()}
                    resumo["anotacoes"] += 1
                continue
            revisitas.append({"data": data_texto, "texto": texto})
            datas_que_ja_existem.add(data_texto)
            resumo["sessoes"] += 1
            resumo["anotacoes"] += 1 if texto else 0
        if not revisitas:
            registro.pop("revisitas", None)

    # ---------- notas ----------
    for linha in exportacao["notas"]:
        filme = localizador.achar(linha.get("Name"), ano_da_linha(linha))
        nota = converter_nota(linha.get("Rating"))
        if filme is None:
            nao_encontrados.add(f'{linha.get("Name")} ({linha.get("Year")})')
            continue
        if nota is None:
            continue
        chave = usuario.chave_filme(filme)
        if chave not in assistidos:
            assistidos[chave] = registro_basico(filme, converter_data(linha.get("Date")))
            dados["quero_assistir"].pop(chave, None)
            resumo["filmes"] += 1
            resumo["sessoes"] += 1
        if assistidos[chave].get("nota") is None:
            assistidos[chave]["nota"] = nota
            assistidos[chave]["avaliado_em"] = (converter_data(linha.get("Date")) or hoje).isoformat()
            resumo["notas"] += 1

    # ---------- curtidos -> favoritos ----------
    for linha in exportacao["curtidos"]:
        filme = localizador.achar(linha.get("Name"), ano_da_linha(linha))
        if filme is None:
            nao_encontrados.add(f'{linha.get("Name")} ({linha.get("Year")})')
            continue
        chave = usuario.chave_filme(filme)
        if chave not in dados["favoritos"]:
            dados["favoritos"][chave] = registro_basico(filme, converter_data(linha.get("Date")))
            resumo["favoritos"] += 1

    # ---------- watchlist -> Quero assistir ----------
    for linha in exportacao["quero_ver"]:
        filme = localizador.achar(linha.get("Name"), ano_da_linha(linha))
        if filme is None:
            nao_encontrados.add(f'{linha.get("Name")} ({linha.get("Year")})')
            continue
        chave = usuario.chave_filme(filme)
        if chave not in assistidos and chave not in dados["quero_assistir"]:
            dados["quero_assistir"][chave] = registro_basico(filme, converter_data(linha.get("Date")))
            resumo["quero_assistir"] += 1

    if not simular:
        usuario.salvar_dados()
    resumo["nao_encontrados"] = sorted(nao_encontrados)
    return resumo


def texto_do_resumo(resumo):
    """Resumo em poucas linhas (para a janela e para o terminal)."""
    def plural(quantidade, singular, plural_da_palavra):
        return f"{quantidade} {singular if quantidade == 1 else plural_da_palavra}"

    linhas = [
        f"✎ {plural(resumo['filmes'], 'filme novo', 'filmes novos')} no diário "
        f"({plural(resumo['sessoes'], 'sessão', 'sessões')})",
        f"★ {plural(resumo['notas'], 'nota', 'notas')}",
        f"✍ {plural(resumo['anotacoes'], 'resenha virou anotação', 'resenhas viraram anotações')}",
        f"♥ {plural(resumo['favoritos'], 'favorito', 'favoritos')}",
        f"📌 {plural(resumo['quero_assistir'], 'título', 'títulos')} no Quero assistir",
    ]
    if resumo["nao_encontrados"]:
        linhas.append(f"\n{plural(len(resumo['nao_encontrados']), 'filme não está', 'filmes não estão')} no catálogo do CineAI.")
    return "\n".join(linhas)
