"""
tela/base.py — A base da janela: imports, cores, fontes, funções de apoio e a janela principal (janela = ctk.CTk()).

Parte da janela do CineAI (veja cineai/interface.py, que junta todas as partes).
"""
# Os imports daqui servem para TODAS as partes da janela (cada parte importa
# tudo das anteriores com "from ... import *").
import random
import re
import threading
import unicodedata
import os
import sys
import webbrowser
from datetime import date
from pathlib import Path
import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageTk

from cineai import conversas, diario_pdf, filmes, letterboxd, perfil, retrato, streamings, usuario
from cineai.caminhos import CAMINHO_ICONE, PASTA_POSTERS
from cineai.rastreio import formatar_ms, rastro


# =========================================================
# CONSERTO DOS "RASTROS" AO ROLAR (Windows)
# =========================================================
# Toda área com rolagem do customtkinter é um Canvas com a página dentro.
# No Windows, ao rolar rápido, o Canvas "arrasta" a imagem antiga em vez de
# redesenhar os cards: aparecem pôsteres repetidos e borrados (o bug do print).
# Aqui, sempre que uma área rola, mandamos o Windows redesenhar ela inteira
# (com todos os widgets de dentro) logo em seguida. Vale para TODAS as páginas,
# inclusive as que forem criadas depois, porque é instalado no próprio
# CTkScrollableFrame antes de qualquer janela existir.
ATRASO_REDESENHO_MS = 15
RDW_INVALIDATE, RDW_ERASE, RDW_ALLCHILDREN, RDW_UPDATENOW = 0x0001, 0x0004, 0x0080, 0x0100


def redesenhar_area_inteira(widget):
    """Pede ao Windows para repintar o widget e tudo o que está dentro dele, já."""
    widget.redesenho_agendado = None
    try:
        if not widget.winfo_exists():
            return
        if sys.platform.startswith("win"):
            import ctypes
            ctypes.windll.user32.RedrawWindow(
                widget.winfo_id(), None, None,
                RDW_INVALIDATE | RDW_ERASE | RDW_ALLCHILDREN | RDW_UPDATENOW
            )
        else:
            widget.update_idletasks()
    except Exception:
        pass   # redesenhar é só um capricho: se falhar, a rolagem continua funcionando


def agendar_redesenho(widget):
    """Junta vários movimentos da rodinha num redesenho só (no máximo ~60 por segundo)."""
    if getattr(widget, "redesenho_agendado", None) is None:
        widget.redesenho_agendado = widget.after(ATRASO_REDESENHO_MS, lambda: redesenhar_area_inteira(widget))


def instalar_conserto_de_rolagem(area_rolavel):
    canvas = getattr(area_rolavel, "_parent_canvas", None)
    barra = getattr(area_rolavel, "_scrollbar", None)
    if canvas is None or barra is None:
        return
    vertical = getattr(area_rolavel, "_orientation", "vertical") != "horizontal"

    def ao_rolar(inicio, fim):
        barra.set(inicio, fim)          # o que o customtkinter já fazia
        agendar_redesenho(canvas)       # + o redesenho completo

    canvas.configure(**{"yscrollcommand" if vertical else "xscrollcommand": ao_rolar})


init_original_area_rolavel = ctk.CTkScrollableFrame.__init__


def init_area_rolavel_com_conserto(self, *argumentos, **opcoes):
    init_original_area_rolavel(self, *argumentos, **opcoes)
    instalar_conserto_de_rolagem(self)


ctk.CTkScrollableFrame.__init__ = init_area_rolavel_com_conserto


# =========================================================
# CONFIGURAÇÕES E CONSTANTES
# =========================================================
# Visual "diário de cinema": capa vermelha, papel creme, ingressos,
# película 5-4-3-2-1, dourado do Oscar e anotações em caneta azul.
ctk.set_appearance_mode("light")


# ---------------- Papel ----------------
COR_FUNDO = "#F1E4C8"            # página envelhecida (fundo das telas)
COR_PAPEL = "#FBF4E3"            # papel claro (cards, chat, campos)
COR_PAPEL_ESCURO = "#E6D3AE"     # papel kraft
COR_BORDA_PAPEL = "#D6BF95"      # bordas de papel
COR_FITA = "#E4CF9C"             # fita adesiva dos cards
COR_MESA = "#CDB48A"             # "mesa" atrás da janela de detalhes

# ---------------- Capa e cinema ----------------
COR_MENU = "#A3221C"             # capa vermelha do diário
COR_MENU_HOVER = "#BD3329"
COR_VERMELHO = "#B3261E"
COR_VERMELHO_HOVER = "#8E1D17"
COR_VINHO = "#5C1A16"
COR_PELICULA = "#231A17"         # película preta
COR_FURO_PELICULA = "#F1E4C8"
COR_DOURADO = "#C99A3B"          # Oscar
COR_DOURADO_CLARO = "#ECCB80"
COR_INGRESSO = "#F3DACE"         # ingresso rosado ("ADMIT ONE")
COR_INGRESSO_BORDA = "#C98279"
COR_TEXTO_CAPA = "#FFF1DC"       # texto creme sobre o vermelho
COR_MARCA_TEXTO = COR_DOURADO_CLARO  # marca-texto dos títulos à mão (dourado, dentro da paleta)
COR_RABISCO = COR_VERMELHO           # rabisco antes dos títulos à mão
COR_TITULO_MANUSCRITO = COR_VERMELHO  # texto dos títulos à mão
COR_AZUL_CANETA = "#2F4FA0"      # caneta azul do diário

# ---------------- Cards ----------------
COR_CARD = COR_PAPEL
COR_POSTER = "#2B211D"
COR_SELO = "#7A1D18"

# ---------------- Favoritos, assistidos e estrelas ----------------
COR_FAVORITO = COR_VERMELHO
COR_FAVORITO_HOVER = COR_VERMELHO_HOVER
COR_ASSISTIDO = "#5E7A3C"
COR_ASSISTIDO_HOVER = "#4A6130"
COR_BOTAO_NEUTRO = COR_PAPEL_ESCURO
COR_BOTAO_NEUTRO_HOVER = "#D8C298"
COR_TRAILER = COR_PELICULA        # botão ▶ trailer: película preta com letras douradas
COR_TRAILER_HOVER = COR_VINHO
COR_SURPRESA = COR_DOURADO        # botão 🎲 Surpreenda-me: dourado do Oscar
COR_SURPRESA_HOVER = "#B0842C"
COR_SERIE = COR_AZUL_CANETA         # etiqueta "SÉRIE" (caneta azul do diário)
COR_ESTRELA_ACESA = "#D4A017"
COR_ESTRELA_APAGADA = "#CDBB98"

# ---------------- Texto ----------------
COR_TEXTO = "#2A1C17"            # tinta
COR_TEXTO_SECUNDARIO = "#6B5546"
COR_TEXTO_SUAVE = "#8F7A66"
COR_TEXTO_CONTEUDO = "#3E2F27"

# ---------------- Rolagem ----------------
COR_ROLAGEM = "#C9AE82"
COR_ROLAGEM_HOVER = "#A88A5E"

# ---------------- Fontes ----------------
# Os nomes abaixo existem no Windows. Logo depois de criar a janela,
# escolher_fonte() confere quais estão instaladas e usa a alternativa
# se faltar alguma (assim nada quebra em outro computador).
FONTE_TITULO = "Impact"          # letreiro de cinema
FONTE = "Georgia"                # texto de livro/diário
FONTE_MANUSCRITA = "Ink Free"    # anotações à mão
FONTE_INTERFACE = "Arial"        # etiquetas pequenas

COLUNAS_CARDS = 4
CARDS_POR_PAGINA = 20              # cards por página no Catálogo (◀ ▶ para trocar)
LIMITE_CARDS_GRADE = 60            # máximo nas outras grades (Recomendações, Meu diário...)
ATRASO_BUSCA_CATALOGO_MS = 300     # espera a pessoa parar de digitar

# Tela inicial "delicada": letreiro em papel creme e cards de recorte claros
ALTURA_POSTER_INICIO = 230             # pôsteres dos 4 cards da tela inicial
COR_RECORTE_VAZIO = COR_PAPEL_ESCURO   # card ainda sem filme (kraft claro, não marrom escuro)

# Capa do diário (menu)
COR_LOMBADA = "#7C1914"          # faixa mais escura na borda da capa
COR_COSTURA = "#E7A99C"          # pontinhos da costura da lombada
LARGURA_LOMBADA = 14
TAMANHO_ICONE_MENU = 20          # ícones desenhados à mão (em pontos)
INTENSIDADE_TEXTURA_CAPA = 5     # 0 desliga a textura de tecido da capa

# Texto do ingresso no rodapé do menu (troque aqui se quiser outra palavra)
TEXTO_INGRESSO_MENU = "SESSÃO VIP"

# Película da contagem 5-4-3-2-1 (desenhada com o Pillow)
ALTURA_PELICULA_CONTAGEM = 72    # altura da faixa (em pontos); diminua para ficar mais fina
NUMEROS_CONTAGEM = ["5", "4", "3", "2", "1"]
PROPORCAO_QUADRO_CONTAGEM = 1.6  # largura ÷ altura de cada quadro
FONTES_NUMERO_CONTAGEM = [  # a primeira que existir no computador é usada
    "arial.ttf", "Arial.ttf", "segoeui.ttf", "DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

NOME_IA = "CineAI"
NOME_USUARIO = "Você"
MENSAGEM_BOAS_VINDAS = (
    "Olá! Que filme ou série vai entrar no seu diário hoje? "
    "Me conte o que você está com vontade de assistir."
)

# Cores dos nomes no chat (vermelho do CineAI, caneta azul para você)
COR_NOME_IA = COR_VERMELHO
COR_NOME_USUARIO = COR_AZUL_CANETA

# Animação de "pensando": a contagem regressiva do começo dos filmes
QUADROS_ANIMACAO = ["⑤", "④", "③", "②", "①"]
TEXTO_ANIMACAO = "CineAI está rodando o projetor..."
INTERVALO_ANIMACAO_MS = 260

# Botão 🎲: a mensagem que ele manda para o CineAI
MENSAGEM_SURPRESA = "🎲 Me surpreenda!"

# Faixa "Se você gostou, veja também" na janela de detalhes
TAMANHO_POSTER_SEMELHANTE = (78, 114)
QUANTIDADE_SEMELHANTES_DIARIO = 5
TAMANHO_MAXIMO_LEGENDA_SEMELHANTE = 24  # letras; títulos maiores ganham "…"

# Efeito de digitação da resposta
INTERVALO_DIGITACAO_MS = 18
DURACAO_MAXIMA_DIGITACAO_MS = 3000



COR_BILHETE = "#FFFDF7"

# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================
def cor_rgb(cor_hex):
    """"#B3261E" -> (179, 38, 30), para desenhar com o Pillow."""
    cor_hex = cor_hex.lstrip("#")
    return tuple(int(cor_hex[posicao:posicao + 2], 16) for posicao in (0, 2, 4))


def normalizar_texto(texto):
    """Remove acentos e converte para minúsculas."""
    texto = unicodedata.normalize("NFD", str(texto))
    texto = "".join(
        caractere
        for caractere in texto
        if unicodedata.category(caractere) != "Mn"
    )
    return texto.lower()


EXTENSOES_POSTER = [".png", ".jpg", ".jpeg"]


def criar_nome_arquivo(nome_filme, extensao=".png"):
    """Gera o nome do arquivo do pôster a partir do nome do filme."""
    nome = normalizar_texto(nome_filme)
    nome = re.sub(r"[^a-z0-9]+", "_", nome)
    return nome.strip("_") + extensao


def obter_caminho_poster(filme):
    """
    1º: o arquivo indicado no campo "poster" (filmes importados do TMDB).
    2º: o nome do filme em .png ou .jpg (pôsteres colocados à mão).
    """
    if filme.get("poster"):
        caminho_tmdb = PASTA_POSTERS / filme["poster"]
        if caminho_tmdb.exists():
            return caminho_tmdb

    for extensao in EXTENSOES_POSTER:
        caminho = PASTA_POSTERS / criar_nome_arquivo(filme["nome"], extensao)
        if caminho.exists():
            return caminho

    # Nenhum encontrado: devolve o caminho .png (que não existe).
    return PASTA_POSTERS / criar_nome_arquivo(filme["nome"])


# Guarda as imagens já abertas para não ler o mesmo arquivo de novo
# a cada busca no catálogo. Chave: (caminho, tamanho).
cache_imagens = {}


def carregar_poster(filme, tamanho):
    """Retorna um CTkImage com o pôster do filme, ou None se não existir."""
    caminho_poster = obter_caminho_poster(filme)

    if not caminho_poster.exists():
        return None

    chave_cache = (str(caminho_poster), tamanho)
    if chave_cache in cache_imagens:
        return cache_imagens[chave_cache]

    try:
        with Image.open(caminho_poster) as arquivo_imagem:
            imagem_original = arquivo_imagem.copy()  # libera o arquivo no disco

        imagem = ctk.CTkImage(
            light_image=imagem_original,
            dark_image=imagem_original,
            size=tamanho
        )
    except Exception as erro:
        print(f"Erro ao carregar pôster de {filme['nome']}: {erro}")
        return None

    cache_imagens[chave_cache] = imagem
    return imagem


def exibir_poster(label_poster, imagem, emoji="🎞\nSEM PÔSTER"):
    """Mostra a imagem no label, ou o texto se não houver imagem."""
    if imagem is not None:
        label_poster.configure(image=imagem, text="")
    else:
        label_poster.configure(image=None, text=emoji)
        # Bug do customtkinter 5.2: image=None não apaga a imagem antiga do
        # label interno do Tk, então o pôster velho ficava por baixo do texto.
        label_poster._label.configure(image="")


def texto_resumo_filme(filme):
    """Linha pequena do card: '2001 • Animação, Comédia • 🍅 88%'."""
    resumo = f'{filmes.periodo_de_exibicao(filme)} • {filme.get("genero", "")}'

    if filmes.eh_serie(filme) and filme.get("temporadas"):
        resumo += f' • {filme["temporadas"]} temp.'

    rotten = filme.get("rotten_tomatoes")
    if isinstance(rotten, dict) and rotten.get("critica"):
        resumo += f' • 🍅 {rotten["critica"]}%'

    return resumo


# =========================================================
# JANELA PRINCIPAL
# =========================================================
janela = ctk.CTk()
janela.title("CineAI — seu diário de cinema")
if sys.platform.startswith("win") and CAMINHO_ICONE.exists():
    try:
        janela.iconbitmap(default=str(CAMINHO_ICONE))   # ícone da janela e da barra de tarefas
    except tk.TclError:
        pass
janela.geometry("1200x760")
janela.minsize(1050, 680)
janela.configure(fg_color=COR_FUNDO)
janela.grid_rowconfigure(0, weight=1)
janela.grid_columnconfigure(1, weight=1)


# ---------------- Fontes disponíveis neste computador ----------------
familias_instaladas = {familia.lower() for familia in tkfont.families(janela)}


def escolher_fonte(*opcoes):
    """Primeira fonte da lista que estiver instalada (a última é o plano B)."""
    for opcao in opcoes:
        if opcao.lower() in familias_instaladas:
            return opcao
    return opcoes[-1]


FONTE_TITULO = escolher_fonte("Impact", "Haettenschweiler", "Arial Black", "Arial")
FONTE = escolher_fonte("Georgia", "Cambria", "Times New Roman", "Arial")
FONTE_MANUSCRITA = escolher_fonte("Ink Free", "Segoe Print", "Comic Sans MS", FONTE)
FONTE_INTERFACE = escolher_fonte("Arial", "Segoe UI", FONTE)
# Fonte com os símbolos ★ ❤ ✦ ● (Georgia e Impact não têm todos)
FONTE_SIMBOLOS = escolher_fonte("Segoe UI Symbol", "DejaVu Sans", FONTE_INTERFACE)
