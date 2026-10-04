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

from cineai import conversas, diario_pdf, filmes, perfil, retrato, streamings, usuario
from cineai.caminhos import CAMINHO_ICONE, PASTA_POSTERS
from cineai.rastreio import formatar_ms, rastro


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
# SELOS ❤️ / ✅ NOS CARDS
# =========================================================
# Cada card de filme ganha um selinho no canto do pôster.
# Guardamos (label, filme) de todos os selos visíveis para atualizar
# todos de uma vez quando a pessoa favorita ou marca como assistido.
selos_em_tela = []


def texto_do_selo(filme):
    """'❤️ ★ 4' (favorito com nota 4), '✅' (assistido sem nota), etc."""
    partes_selo = []

    # Coração e visto simples: os emojis "❤️"/"✅" têm um caractere invisível
    # que o Windows desenha como um espaço largo dentro da etiqueta.
    if usuario.eh_favorito(filme):
        partes_selo.append("❤")

    nota = usuario.obter_nota(filme)
    if nota is not None:
        partes_selo.append(f"★ {nota}")
    elif usuario.foi_assistido(filme):
        partes_selo.append("✓")

    return " ".join(partes_selo)


def atualizar_selo(label_selo, filme):
    """Mostra o selo no canto superior direito, ou esconde se não houver nada."""
    texto = texto_do_selo(filme) if filme is not None else ""

    if texto == "":
        label_selo.place_forget()
    else:
        label_selo.configure(text=texto)
        label_selo.place(relx=1.0, rely=0.0, x=-6, y=6, anchor="ne")


def criar_selo(area_poster, filme, registrar=True):
    # Etiqueta impressa: vermelho escuro com letra creme
    label_selo = ctk.CTkLabel(
        area_poster,
        text="",
        font=(FONTE_SIMBOLOS, 12, "bold"),
        text_color=COR_TEXTO_CAPA,
        fg_color=COR_SELO,
        corner_radius=2,
        width=10,
        height=24
    )
    atualizar_selo(label_selo, filme)

    if registrar:
        selos_em_tela.append((label_selo, filme))

    return label_selo


def atualizar_selos_em_tela():
    """Atualiza todos os selos que ainda existem e descarta os de cards apagados."""
    selos_vivos = []

    for label_selo, filme in selos_em_tela:
        if label_selo.winfo_exists():
            atualizar_selo(label_selo, filme)
            selos_vivos.append((label_selo, filme))

    selos_em_tela[:] = selos_vivos

    # Recortes da tela inicial (nota, coração e carimbo mudam junto)
    for dados_card in cards_recomendacao:
        if dados_card["filme"] is not None:
            mostrar_filme_no_card(dados_card, dados_card["filme"])


def ao_mudar_listas():
    """Chamada sempre que um filme entra ou sai dos favoritos/assistidos."""
    atualizar_selos_em_tela()
    atualizar_recortes_em_tela()  # nota, coração e carimbo WATCHED nas polaroides

    # Com "esconder os que já vi" ou ordem "Combina comigo", o Catálogo muda junto.
    if esconder_assistidos_var.get() or filtro_ordem.get() == "Combina comigo":
        atualizar_catalogo(manter_pagina=True)
    atualizar_meus_filmes(voltar_ao_topo=False)
    atualizar_pagina_perfil()


def vincular_clique(widgets, funcao):
    for widget in widgets:
        widget.bind("<Button-1>", funcao)


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


# =========================================================
# JANELA DE DETALHES — um diário aberto
# =========================================================
# Página da esquerda: pôster colado, ações e suas estrelas.
# Página da direita: anotações como no seu diário (caneta azul,
# marca-texto rosa na sinopse, notas em forma de ingresso).

def formatar_duracao(minutos):
    """139 -> '2h 19min'."""
    if not minutos:
        return "Não informada"
    horas, resto = divmod(int(minutos), 60)
    if horas == 0:
        return f"{resto}min"
    return f"{horas}h {resto:02d}min"


def adicionar_campo_diario(container, rotulo, valor):
    """Linha do diário: 'Direção:' em caneta azul + valor em tinta."""
    linha = ctk.CTkFrame(container, fg_color="transparent")
    linha.pack(fill="x", padx=34, pady=2)

    rotulo_label = ctk.CTkLabel(
        linha,
        text=f"{rotulo}:",
        font=(FONTE_MANUSCRITA, 17, "bold"),
        text_color=COR_AZUL_CANETA,
        width=118,
        anchor="w"
    )
    rotulo_label.pack(side="left", anchor="n")

    valor_label = ctk.CTkLabel(
        linha,
        text=valor,
        font=(FONTE, 14),
        text_color=COR_TEXTO,
        anchor="w",
        justify="left",
        wraplength=380
    )
    valor_label.pack(side="left", fill="x", expand=True, anchor="n", pady=(2, 0))

    # Linha de caderno bem discreta embaixo de cada informação
    pauta = ctk.CTkFrame(container, height=1, fg_color=COR_PAUTA_CADERNO, corner_radius=0)
    pauta.pack(fill="x", padx=34, pady=(1, 3))


def adicionar_titulo_secao(container, texto, cor=COR_VERMELHO):
    titulo = ctk.CTkLabel(
        container,
        text=texto,
        font=(FONTE_TITULO, 17),
        text_color=cor,
        anchor="w"
    )
    titulo.pack(fill="x", padx=34, pady=(18, 6))


# ---------------- Onde assistir: selinhos coloridos dos streamings ----------------
def criar_selinhos_de_streaming(container, filme):
    """Um selinho na cor de cada streaming ('✓' nos que você assina) + a fonte dos dados."""
    escala = escala_da_tela(container)

    def px(valor):
        return int(valor * escala)

    area = tk.Frame(container, bg=COR_PAPEL)
    area.pack(fill="x", padx=(px(34), px(26)))

    lista = streamings.onde_assistir(filme)
    if lista is None:
        tk.Label(
            area, text="ainda não consultado — rode  python importadores/importar_onde_assistir.py",
            font=(FONTE_MANUSCRITA, -px(14)), fg=COR_TEXTO_SUAVE, bg=COR_PAPEL, anchor="w"
        ).pack(anchor="w")
        return
    if not lista:
        tk.Label(
            area, text="fora dos streamings por assinatura no Brasil (só aluguel ou compra)",
            font=(FONTE_MANUSCRITA, -px(15)), fg=COR_TEXTO_SECUNDARIO, bg=COR_PAPEL, anchor="w"
        ).pack(anchor="w")
    else:
        meus = set(usuario.obter_meus_streamings())
        linha = tk.Frame(area, bg=COR_PAPEL)
        linha.pack(anchor="w")
        for nome in lista:
            tk.Label(
                linha, text=f" {nome}{'  ✓' if nome in meus else ''} ",
                font=(FONTE_INTERFACE, -px(12), "bold"), fg="#FFFFFF",
                bg=streamings.cor_do_streaming(nome), padx=px(6), pady=px(3)
            ).pack(side="left", padx=(0, px(6)))
        if meus & set(lista):
            tk.Label(
                area, text="✓ = você assina", font=(FONTE_MANUSCRITA, -px(13)),
                fg=COR_ASSISTIDO, bg=COR_PAPEL
            ).pack(anchor="w", pady=(px(4), 0))
    consultado = (filme.get("onde_assistir") or {}).get("consultado_em", "")
    tk.Label(
        area, text=f"dados de streaming: JustWatch (via TMDB) · consultado em {consultado}",
        font=(FONTE_INTERFACE, -px(9)), fg=COR_TEXTO_SUAVE, bg=COR_PAPEL
    ).pack(anchor="w", pady=(px(4), 0))


# ---------------- Peças do diário aberto (tela de detalhes) ----------------
COR_PAUTA_CADERNO = "#E2D2B0"     # linhas de caderno da ficha
COR_SOMBRA_PAPEL = "#E2D0AC"      # sombrinha embaixo dos papéis colados
CORES_PAPEL_SELO = ["#FFFDF7", "#F3E6C8", "#FBF4E3", "#EADBB8"]  # branco, kraft claro, creme, kraft
LARGURA_SOMBRA_DOBRA = 22


def desenhar_sombra_da_dobra(largura, altura, lado):
    """Degradê do papel até uma sombra suave, perto da lombada (lado 'esquerda' ou 'direita')."""
    papel = cor_rgb(COR_PAPEL)
    sombra = tuple(int(canal * 0.86) for canal in papel)
    faixa = Image.new("RGB", (largura, 1))
    for x in range(largura):
        perto_da_dobra = x / max(1, largura - 1)          # 0 longe .. 1 encostado
        if lado == "direita":
            perto_da_dobra = 1 - perto_da_dobra
        forca = perto_da_dobra ** 2.2
        faixa.putpixel((x, 0), tuple(int(p + (s - p) * forca) for p, s in zip(papel, sombra)))
    return faixa.resize((largura, altura))


def notas_para_selos(filme):
    """[(fonte, valor grande, legenda pequena)] de cada nota que o filme tiver."""
    selos = []
    rotten = filme.get("rotten_tomatoes")
    if isinstance(rotten, dict) and rotten.get("critica"):
        legenda = "crítica"
        if rotten.get("publico"):
            legenda += f' · público {rotten["publico"]}%'
        selos.append(("ROTTEN TOMATOES", f'{rotten["critica"]}%', legenda))
    if filme.get("nota_imdb"):
        selos.append(("IMDb", f'{filmes.formatar_nota(filme["nota_imdb"])}/10', "público"))
    if filme.get("metacritic"):
        selos.append(("METACRITIC", f'{filme["metacritic"]}/100', "crítica"))
    if filme.get("nota_tmdb"):
        votos = filme.get("votos_tmdb")
        legenda = f'{votos:,} votos'.replace(",", ".") if votos else "TMDB"
        selos.append(("TMDB", f'{filmes.formatar_nota(round(filme["nota_tmdb"], 1))}/10', legenda))
    return selos


def desenhar_selo_de_nota(fonte, valor, legenda, escala, indice, cor_pagina):
    """Um recorte de papel com a nota, levemente torto (cada um de um jeito)."""
    def px(valor_px):
        return max(1, int(valor_px * escala))

    sorteio = random.Random(f"selo{fonte}{indice}")
    largura, altura = px(102), px(80)
    papel_cor = cor_rgb(CORES_PAPEL_SELO[indice % len(CORES_PAPEL_SELO)]) + (255,)

    selo = Image.new("RGBA", (largura, altura), papel_cor)
    lapis = ImageDraw.Draw(selo)
    lapis.rectangle([0, 0, largura - 1, altura - 1], outline=cor_rgb(COR_BORDA_PAPEL) + (255,))
    lapis.text((largura // 2, px(16)), fonte, font=fonte_pil(FONTES_CARIMBO_PIL, px(10)),
               fill=cor_rgb(COR_VERMELHO) + (255,), anchor="mm")
    lapis.text((largura // 2, px(41)), valor, font=fonte_pil(FONTES_CARIMBO_PIL, px(22)),
               fill=cor_rgb(COR_TEXTO) + (255,), anchor="mm")
    lapis.text((largura // 2, px(65)), legenda, font=fonte_pil(FONTES_MANUSCRITAS_PIL, px(12)),
               fill=COR_TINTA_AZUL, anchor="mm")

    folga = px(8)
    com_sombra = Image.new("RGBA", (largura + 2 * folga, altura + 2 * folga), (0, 0, 0, 0))
    com_sombra.alpha_composite(Image.new("RGBA", (largura, altura), (60, 40, 25, 60)), (folga + px(2), folga + px(3)))
    com_sombra = com_sombra.filter(ImageFilter.GaussianBlur(px(2)))
    com_sombra.alpha_composite(selo, (folga, folga))
    girado = com_sombra.rotate(sorteio.uniform(-4, 4), resample=Image.BICUBIC, expand=True)

    if indice % 2 == 0:  # metade dos selos ganha um pedacinho de fita
        fita = Image.new("RGBA", (px(34), px(10)), sorteio.choice(CORES_FITA))
        fita = fita.rotate(sorteio.uniform(-12, 12), resample=Image.BICUBIC, expand=True)
        girado.alpha_composite(fita, (girado.width // 2 - fita.width // 2, folga - fita.height // 2 + px(2)))

    pagina = Image.new("RGBA", girado.size, cor_rgb(cor_pagina) + (255,))
    pagina.alpha_composite(girado)
    return ImageTk.PhotoImage(pagina.convert("RGB"))


def criar_selos_de_nota(container, filme, imagens):
    """As notas viram recortes colados lado a lado (bagunça organizada)."""
    selos = notas_para_selos(filme)
    if not selos:
        return False
    area = tk.Frame(container, bg=COR_PAPEL)
    area.pack(anchor="w", padx=22, pady=(0, 6))
    escala = escala_da_tela(container)
    for indice, (fonte, valor, legenda) in enumerate(selos):
        foto = desenhar_selo_de_nota(fonte, valor, legenda, escala, indice, COR_PAPEL)
        imagens.append(foto)
        tk.Label(area, image=foto, bg=COR_PAPEL, bd=0).grid(
            row=0, column=indice, padx=0, pady=(int((indice % 2) * 6 * escala), 0), sticky="n"
        )
    return True


def criar_papel_colado(container, texto, fonte=None, cor_texto=COR_TEXTO_CONTEUDO, wraplength=470):
    """
    Pedaço de papel colado na página: papel branquinho com borda, sombra
    embaixo à direita e um pedacinho de fita em cima (a sinopse usa isso).
    """
    escala = escala_da_tela(container)

    def px(valor):
        return int(valor * escala)

    sombra = tk.Frame(container, bg=COR_SOMBRA_PAPEL)
    sombra.pack(anchor="w", padx=(px(30), px(26)), pady=(px(6), px(4)), fill="x")

    papel = tk.Frame(sombra, bg=COR_BILHETE, highlightbackground=COR_BORDA_PAPEL, highlightthickness=1)
    papel.pack(fill="x", padx=(0, px(3)), pady=(0, px(3)))

    label = tk.Label(
        papel, text=texto, font=fonte or (FONTE, -px(14)), fg=cor_texto, bg=COR_BILHETE,
        justify="left", anchor="w", wraplength=px(wraplength)
    )
    label.pack(fill="x", padx=px(16), pady=(px(16), px(14)))

    fita = tk.Frame(papel, bg=COR_FITA, width=px(70), height=px(14))
    fita.place(relx=0.5, y=0, anchor="n")
    return label


def criar_ingressos_de_nota(container, linhas_avaliacao):
    """Cada nota (Rotten, IMDb, Metacritic, TMDB) vira um ingresso."""
    area = ctk.CTkFrame(container, fg_color="transparent")
    area.pack(fill="x", padx=30, pady=(0, 6))

    for posicao, linha in enumerate(linhas_avaliacao):
        ingresso = ctk.CTkFrame(
            area,
            fg_color=COR_INGRESSO,
            border_width=2,
            border_color=COR_INGRESSO_BORDA,
            corner_radius=6
        )
        ingresso.grid(row=posicao // 2, column=posicao % 2, sticky="ew", padx=4, pady=4)

        texto = ctk.CTkLabel(
            ingresso,
            text=linha,
            font=(FONTE, 13, "bold"),
            text_color=COR_VINHO,
            anchor="w",
            justify="left",
            wraplength=210
        )
        texto.pack(fill="x", padx=12, pady=8)

    area.grid_columnconfigure(0, weight=1, uniform="ingressos")
    area.grid_columnconfigure(1, weight=1, uniform="ingressos")


def criar_faixa_semelhantes(container, filme, ao_clicar):
    """
    "🎞 SE VOCÊ GOSTOU, VEJA TAMBÉM": mini polaroides dos filmes mais
    parecidos (sinopse + gêneros), lado a lado como numa tira de fotos.
    """
    semelhantes = filmes.filmes_semelhantes(filme, quantidade=QUANTIDADE_SEMELHANTES_DIARIO)
    if not semelhantes:
        return

    adicionar_titulo_secao(container, "SE VOCÊ GOSTOU DESSE...")

    faixa = ctk.CTkFrame(container, fg_color="transparent")
    faixa.pack(fill="x", padx=26, pady=(0, 4))

    escala = escala_da_tela(container)
    for coluna, outro_filme in enumerate(semelhantes):
        faixa.grid_columnconfigure(coluna, weight=1, uniform="semelhantes")

        # Mini polaroide torta (mesmo desenho dos cards, em versão compacta)
        mini = tk.Frame(faixa, bg=COR_PAPEL, cursor="hand2")
        mini.grid(row=0, column=coluna, padx=2, pady=4, sticky="n")

        foto = imagem_do_recorte(outro_filme, escala, COR_PAPEL, TAMANHO_POSTER_SEMELHANTE, modo="compacto")
        foto_label = tk.Label(mini, image=foto, bg=COR_PAPEL, bd=0, cursor="hand2")
        foto_label.imagem = foto
        foto_label.pack()

        marca = "✓ " if usuario.foi_assistido(outro_filme) else ""
        nome_curto = outro_filme["nome"]
        if len(nome_curto) > TAMANHO_MAXIMO_LEGENDA_SEMELHANTE:
            nome_curto = nome_curto[:TAMANHO_MAXIMO_LEGENDA_SEMELHANTE - 1].rstrip(" :,-") + "…"
        legenda = tk.Label(
            mini, text=f'{marca}{nome_curto}', font=(FONTE_MANUSCRITA, -int(13 * escala)),
            fg=COR_AZUL_CANETA, bg=COR_PAPEL, wraplength=int((TAMANHO_POSTER_SEMELHANTE[0] + 14) * escala),
            justify="center", cursor="hand2"
        )
        legenda.pack(pady=(0, 2))

        vincular_clique(
            [mini, foto_label, legenda],
            lambda event=None, escolhido=outro_filme: ao_clicar(escolhido)
        )


TAMANHO_POSTER_DIARIO = (200, 295)
ATRASO_SALVAR_ANOTACAO_MS = 700


def texto_da_etiqueta_do_diario(filme):
    """'✦ MOVIE JOURNAL · ENTRY #024' (filme visto) ou '· TO WATCH' (ainda não visto)."""
    tipo = "SERIES" if filmes.eh_serie(filme) else "MOVIE"
    entrada = usuario.numero_da_entrada(filme)
    if entrada is None:
        return f"  ✦ {tipo} JOURNAL  •  TO WATCH  "
    return f"  ✦ {tipo} JOURNAL  •  ENTRY #{entrada:03d}  "


def abrir_detalhes(filme):
    if filme is None:
        return

    detalhes = ctk.CTkToplevel(janela)
    detalhes.title(filme["nome"])
    detalhes.geometry("1000x740")
    detalhes.minsize(900, 680)
    detalhes.configure(fg_color=COR_MESA)
    detalhes.transient(janela)
    detalhes.grid_rowconfigure(0, weight=1)
    detalhes.grid_columnconfigure(0, weight=1)
    escala = escala_da_tela(detalhes)
    imagens_da_janela = []  # referências das imagens (senão o Python apaga e elas somem)
    detalhes.imagens_da_janela = imagens_da_janela  # presas à janela enquanto ela existir

    # O "caderno": capa vermelha por trás das duas páginas
    caderno = ctk.CTkFrame(detalhes, fg_color=COR_MENU, corner_radius=10)
    caderno.grid(row=0, column=0, sticky="nsew", padx=22, pady=22)
    caderno.grid_rowconfigure(0, weight=1)
    caderno.grid_columnconfigure(4, weight=1)

    # =====================================================
    # PÁGINA DA ESQUERDA: página pessoal (foto colada, botões, estrelas)
    # =====================================================
    pagina_esquerda = ctk.CTkFrame(caderno, width=330, fg_color=COR_PAPEL, corner_radius=4)
    pagina_esquerda.grid(row=0, column=0, sticky="nsew", padx=(10, 0), pady=10)
    pagina_esquerda.grid_propagate(False)
    pagina_esquerda.pack_propagate(False)

    # Pôster colado: polaroide torta, com fita, sombra e "03 OCT 2026 ♥" à mão
    polaroide_label = tk.Label(pagina_esquerda, bg=COR_PAPEL, bd=0)
    polaroide_label.pack(pady=(18, 4))

    def desenhar_polaroide_do_diario():
        foto = imagem_do_recorte(filme, escala, COR_PAPEL, TAMANHO_POSTER_DIARIO, modo="diario")
        polaroide_label.configure(image=foto)
        polaroide_label.imagem = foto

    # ---------- botões que parecem coisas de papel ----------
    # ♡ Favoritar e 📌 Quero ver: etiquetas de papel lado a lado
    # ✓ Assistido: carimbo   |   ▶ Trailer: ingresso
    linha_etiquetas_papel = ctk.CTkFrame(pagina_esquerda, fg_color="transparent")
    linha_etiquetas_papel.pack(pady=(6, 6))

    botao_favorito = ctk.CTkButton(
        linha_etiquetas_papel, width=113, height=36, corner_radius=2, border_width=1,
        border_color=COR_BORDA_PAPEL, font=(FONTE_MANUSCRITA, 15, "bold")
    )
    botao_favorito.pack(side="left", padx=(0, 4))

    botao_quero_ver = ctk.CTkButton(
        linha_etiquetas_papel, width=113, height=36, corner_radius=2, border_width=1,
        border_color=COR_BORDA_PAPEL, font=(FONTE_MANUSCRITA, 15, "bold")
    )
    botao_quero_ver.pack(side="left")

    botao_assistido = ctk.CTkButton(
        pagina_esquerda, width=230, height=36, corner_radius=6, border_width=2,
        fg_color=COR_PAPEL, hover_color=COR_PAPEL_ESCURO, font=(FONTE_TITULO, 15)
    )
    botao_assistido.pack(pady=(0, 2))

    # "↻ vi de novo": aparece depois de assistir (cada clique = nova sessão no diário)
    link_vi_de_novo = tk.Label(
        pagina_esquerda, text="", font=(FONTE_MANUSCRITA, -int(15 * escala), "bold"),
        fg=COR_VINHO, bg=COR_PAPEL, cursor="hand2"
    )
    link_vi_de_novo.pack(pady=(0, 4))

    texto_trailer = "▶  ASSISTIR TRAILER" if filmes.tem_trailer_salvo(filme) else "▶  PROCURAR TRAILER"
    botao_trailer = ctk.CTkButton(
        pagina_esquerda,
        text=texto_trailer,
        width=230,
        height=40,
        corner_radius=8,
        border_width=2,
        border_color=COR_DOURADO,
        font=(FONTE_TITULO, 16),
        fg_color=COR_TRAILER,
        hover_color=COR_TRAILER_HOVER,
        text_color=COR_DOURADO_CLARO,
        command=lambda: webbrowser.open(filmes.url_trailer(filme))
    )
    botao_trailer.pack(pady=(0, 4))

    # ---------- estrelas (sua nota): vazias ☆, pintadas ★ ----------
    area_estrelas = ctk.CTkFrame(pagina_esquerda, fg_color="transparent")
    area_estrelas.pack(pady=(2, 0))

    botoes_estrela = []

    def pintar_estrelas(quantidade_acesas):
        for posicao, botao_estrela in enumerate(botoes_estrela, start=1):
            if posicao <= quantidade_acesas:
                botao_estrela.configure(text="★", text_color=COR_ESTRELA_ACESA)
            else:
                botao_estrela.configure(text="☆", text_color=COR_TEXTO_SUAVE)

    def clicar_estrela(nota_clicada):
        # Clicar de novo na mesma estrela apaga a nota.
        if usuario.obter_nota(filme) == nota_clicada:
            usuario.definir_nota(filme, None)
        else:
            usuario.definir_nota(filme, nota_clicada)
        atualizar_botoes()
        ao_mudar_listas()

    for nota_estrela in range(1, usuario.NOTA_MAXIMA + 1):
        botao_estrela = ctk.CTkButton(
            area_estrelas,
            text="☆",
            width=36,
            height=34,
            font=(FONTE_SIMBOLOS, 26),
            fg_color="transparent",
            hover_color=COR_PAPEL,
            text_color=COR_TEXTO_SUAVE,
            command=lambda nota=nota_estrela: clicar_estrela(nota)
        )
        botao_estrela.pack(side="left", padx=0)
        botao_estrela.bind("<Enter>", lambda event, nota=nota_estrela: pintar_estrelas(nota))
        botao_estrela.bind("<Leave>", lambda event: pintar_estrelas(usuario.obter_nota(filme) or 0))
        botoes_estrela.append(botao_estrela)

    legenda_estrelas = ctk.CTkLabel(
        pagina_esquerda, text="", font=(FONTE_MANUSCRITA, 14),
        text_color=COR_TEXTO_SECUNDARIO, height=18
    )
    legenda_estrelas.pack(pady=(0, 8))

    # Sombra suave da dobra, no canto da página da esquerda
    sombra_esquerda = ImageTk.PhotoImage(
        desenhar_sombra_da_dobra(int(LARGURA_SOMBRA_DOBRA * escala), int(1400 * escala), "esquerda")
    )
    imagens_da_janela.append(sombra_esquerda)
    tk.Label(pagina_esquerda, image=sombra_esquerda, bd=0, bg=COR_PAPEL).place(relx=1.0, y=0, anchor="ne", relheight=1)

    # =====================================================
    # LOMBADA + SOMBRA DA DOBRA DA DIREITA
    # =====================================================
    lombada = ctk.CTkFrame(caderno, width=8, fg_color=COR_VINHO, corner_radius=0)
    lombada.grid(row=0, column=1, sticky="ns", pady=10)

    sombra_direita = ImageTk.PhotoImage(
        desenhar_sombra_da_dobra(int(LARGURA_SOMBRA_DOBRA * escala), int(1400 * escala), "direita")
    )
    imagens_da_janela.append(sombra_direita)
    faixa_sombra = tk.Label(caderno, image=sombra_direita, bd=0, bg=COR_PAPEL, width=int(LARGURA_SOMBRA_DOBRA * escala))
    faixa_sombra.grid(row=0, column=2, sticky="ns", pady=10)

    # =====================================================
    # PÁGINA DA DIREITA: ficha do filme
    # =====================================================
    pagina_direita = ctk.CTkScrollableFrame(
        caderno,
        fg_color=COR_PAPEL,
        corner_radius=0,
        scrollbar_button_color=COR_ROLAGEM,
        scrollbar_button_hover_color=COR_ROLAGEM_HOVER
    )
    pagina_direita.grid(row=0, column=4, sticky="nsew", padx=(0, 10), pady=10)

    etiqueta = ctk.CTkLabel(
        pagina_direita,
        text=texto_da_etiqueta_do_diario(filme),
        font=(FONTE_INTERFACE, 10, "bold"),
        text_color=COR_TEXTO_CAPA,
        fg_color=COR_VERMELHO,
        corner_radius=2,
        height=22
    )
    etiqueta.pack(anchor="w", padx=(18, 34), pady=(24, 8))

    titulo_detalhes = ctk.CTkLabel(
        pagina_direita,
        text=filme["nome"].upper(),
        font=(FONTE_TITULO, 34),
        text_color=COR_TEXTO,
        anchor="w",
        justify="left",
        wraplength=500
    )
    titulo_detalhes.pack(fill="x", padx=(18, 34))

    sublinhado = ctk.CTkFrame(pagina_direita, height=3, fg_color=COR_VERMELHO, corner_radius=0)
    sublinhado.pack(fill="x", padx=(18, 34), pady=(4, 14))

    # Ficha escrita à mão, com linhas de caderno
    elenco = filme.get("elenco", [])
    texto_elenco = ", ".join(elenco) if isinstance(elenco, list) else str(elenco)

    if filmes.eh_serie(filme):
        adicionar_campo_diario(pagina_direita, "Criação", filme.get("diretor", "Não informado"))
        adicionar_campo_diario(pagina_direita, "Exibição", filmes.periodo_de_exibicao(filme))
        adicionar_campo_diario(pagina_direita, "Temporadas", filmes.resumo_das_temporadas(filme) or "—")
        adicionar_campo_diario(pagina_direita, "Gênero", filme.get("genero", "Não informado"))
        duracao_episodio = formatar_duracao(filme.get("duracao_minutos"))
        if filme.get("duracao_minutos"):
            duracao_episodio += " por episódio"
        adicionar_campo_diario(pagina_direita, "Duração", duracao_episodio)
    else:
        adicionar_campo_diario(pagina_direita, "Direção", filme.get("diretor", "Não informado"))
        adicionar_campo_diario(pagina_direita, "Lançamento", str(filme.get("ano", "—")))
        adicionar_campo_diario(pagina_direita, "Gênero", filme.get("genero", "Não informado"))
        adicionar_campo_diario(pagina_direita, "Duração", formatar_duracao(filme.get("duracao_minutos")))
    if texto_elenco:
        adicionar_campo_diario(pagina_direita, "Elenco", texto_elenco)

    # Sinopse: pedaço de papel colado com fita
    adicionar_titulo_secao(pagina_direita, "SINOPSE")
    criar_papel_colado(pagina_direita, filme.get("sinopse", "Sinopse não disponível."))

    # Prêmios (opcional), em dourado
    premios = filme.get("premios")
    if premios:
        adicionar_titulo_secao(pagina_direita, "🏆 PRÊMIOS", cor=COR_DOURADO)
        texto_premios = "\n".join(f"• {premio}" for premio in premios) if isinstance(premios, list) else str(premios)
        ctk.CTkLabel(
            pagina_direita, text=texto_premios, font=(FONTE, 14), text_color=COR_TEXTO_CONTEUDO,
            anchor="w", justify="left", wraplength=470
        ).pack(fill="x", padx=34)

    # Avaliações: recortes de papel colados, cada um levemente torto
    if notas_para_selos(filme):
        adicionar_titulo_secao(pagina_direita, "AVALIAÇÕES")
        criar_selos_de_nota(pagina_direita, filme, imagens_da_janela)

    # ---------- Onde assistir (streamings do Brasil) ----------
    adicionar_titulo_secao(pagina_direita, "ONDE ASSISTIR 📺")
    criar_selinhos_de_streaming(pagina_direita, filme)

    # ---------- Minhas anotações (só depois de assistir) ----------
    adicionar_titulo_secao(pagina_direita, "MINHAS ANOTAÇÕES ✎")
    area_anotacoes = tk.Frame(pagina_direita, bg=COR_PAPEL)
    area_anotacoes.pack(fill="x", padx=(30, 26))
    estado_anotacao = {"caixa": None, "agendamento": None, "aviso": None}

    def salvar_anotacao():
        estado_anotacao["agendamento"] = None
        caixa = estado_anotacao["caixa"]
        if caixa is None or not caixa.winfo_exists():
            return
        usuario.definir_anotacao(filme, caixa.get("1.0", "end"))
        if estado_anotacao["aviso"] is not None and estado_anotacao["aviso"].winfo_exists():
            estado_anotacao["aviso"].configure(text="salvo no seu diário ✓")

    def agendar_salvamento(event=None):
        """Salva sozinho quando você para de escrever (sem botão de salvar)."""
        if estado_anotacao["agendamento"] is not None:
            detalhes.after_cancel(estado_anotacao["agendamento"])
        if estado_anotacao["aviso"] is not None:
            estado_anotacao["aviso"].configure(text="escrevendo…")
        estado_anotacao["agendamento"] = detalhes.after(ATRASO_SALVAR_ANOTACAO_MS, salvar_anotacao)

    def montar_anotacoes():
        for widget in area_anotacoes.winfo_children():
            widget.destroy()
        estado_anotacao["caixa"] = None
        estado_anotacao["aviso"] = None

        if not usuario.foi_assistido(filme):
            tk.Label(
                area_anotacoes,
                text="Marque como visto para escrever o que você achou. ✎",
                font=(FONTE_MANUSCRITA, -int(15 * escala)), fg=COR_TEXTO_SUAVE, bg=COR_PAPEL, anchor="w"
            ).pack(anchor="w", pady=(0, 4))
            return

        tk.Label(
            area_anotacoes, text="O que você achou desse filme?",
            font=(FONTE_MANUSCRITA, -int(16 * escala)), fg=COR_AZUL_CANETA, bg=COR_PAPEL, anchor="w"
        ).pack(anchor="w")

        caixa = ctk.CTkTextbox(
            area_anotacoes, height=110, wrap="word", corner_radius=2,
            fg_color=COR_BILHETE, text_color=COR_AZUL_CANETA, border_width=1,
            border_color=COR_BORDA_PAPEL, font=(FONTE_MANUSCRITA, 17)
        )
        caixa.pack(fill="x", pady=(4, 2))
        texto_salvo = usuario.obter_anotacao(filme)
        if texto_salvo:
            caixa.insert("1.0", texto_salvo)
        caixa.bind("<KeyRelease>", agendar_salvamento)
        estado_anotacao["caixa"] = caixa

        aviso = tk.Label(
            area_anotacoes, text="salvo no seu diário ✓" if texto_salvo else "escreva à vontade: salva sozinho",
            font=(FONTE_MANUSCRITA, -int(13 * escala)), fg=COR_TEXTO_SUAVE, bg=COR_PAPEL, anchor="e"
        )
        aviso.pack(anchor="e")
        estado_anotacao["aviso"] = aviso

    def ao_fechar():
        if estado_anotacao["agendamento"] is not None:
            detalhes.after_cancel(estado_anotacao["agendamento"])
            salvar_anotacao()
        detalhes.destroy()
        atualizar_meus_filmes(voltar_ao_topo=False)  # a anotação aparece na entrada do diário

    detalhes.protocol("WM_DELETE_WINDOW", ao_fechar)

    # Filmes semelhantes: clicar troca o diário para o filme escolhido
    def abrir_semelhante(outro_filme):
        def trocar():
            ao_fechar()
            abrir_detalhes(outro_filme)
        janela.after(10, trocar)

    criar_faixa_semelhantes(pagina_direita, filme, abrir_semelhante)

    botao_fechar = ctk.CTkButton(
        pagina_direita,
        text="FECHAR O DIÁRIO",
        width=170,
        height=38,
        corner_radius=4,
        font=(FONTE_INTERFACE, 12, "bold"),
        fg_color=COR_VINHO,
        hover_color=COR_VERMELHO,
        text_color=COR_TEXTO_CAPA,
        command=ao_fechar
    )
    botao_fechar.pack(anchor="w", padx=(18, 34), pady=(20, 30))

    # =====================================================
    # ESTADO DOS BOTÕES (favorito, assistido, estrelas)
    # =====================================================
    def atualizar_botoes():
        if usuario.eh_favorito(filme):
            botao_favorito.configure(
                text="♥ favorito", fg_color=COR_BILHETE, hover_color=COR_PAPEL_ESCURO,
                text_color=COR_VERMELHO, border_color=COR_VERMELHO
            )
        else:
            botao_favorito.configure(
                text="♡ favoritar", fg_color=COR_BILHETE, hover_color=COR_PAPEL_ESCURO,
                text_color=COR_VINHO, border_color=COR_BORDA_PAPEL
            )

        if usuario.quer_assistir(filme):
            botao_quero_ver.configure(
                text="📌 na lista", fg_color=COR_BILHETE, hover_color=COR_PAPEL_ESCURO,
                text_color=COR_AZUL_CANETA, border_color=COR_AZUL_CANETA
            )
        else:
            botao_quero_ver.configure(
                text="📌 quero ver", fg_color=COR_BILHETE, hover_color=COR_PAPEL_ESCURO,
                text_color=COR_VINHO, border_color=COR_BORDA_PAPEL
            )

        if usuario.foi_assistido(filme):
            data = data_que_assistiu(filme)
            botao_assistido.configure(
                text=f"✓  WATCHED{' · ' + data if data else ''}",
                border_color=COR_VERMELHO, text_color=COR_VERMELHO
            )
        else:
            botao_assistido.configure(
                text="○  MARCAR COMO VISTO",
                border_color=COR_TEXTO_SUAVE, text_color=COR_TEXTO_SUAVE
            )

        nota_atual = usuario.obter_nota(filme)
        pintar_estrelas(nota_atual or 0)
        if nota_atual is None:
            legenda_estrelas.configure(text="clique numa estrela para dar sua nota")
        else:
            legenda_estrelas.configure(text=f"sua nota: {nota_atual} de {usuario.NOTA_MAXIMA}  (clique de novo para apagar)")

        vezes = usuario.quantas_vezes_viu(filme)
        if vezes == 0:
            link_vi_de_novo.configure(text="")
        elif vezes == 1:
            link_vi_de_novo.configure(text="↻ vi de novo")
        else:
            link_vi_de_novo.configure(text=f"↻ vi de novo   ·   visto {vezes}×")

        etiqueta.configure(text=texto_da_etiqueta_do_diario(filme))
        desenhar_polaroide_do_diario()

    def animar_carimbo_do_adesivo(parametro="escala_adesivo"):
        """
        O coração (ou o carimbo WATCHED) "cai" na polaroide e assenta: 5 quadros, ~0,3 s.
        parametro: "escala_adesivo" ou "escala_carimbo".
        """
        quadros = [
            ImageTk.PhotoImage(desenhar_recorte(
                filme, escala, COR_PAPEL, TAMANHO_POSTER_DIARIO, modo="diario", **{parametro: tamanho}
            ))
            for tamanho in QUADROS_CARIMBO_ADESIVO
        ]
        imagens_da_janela.extend(quadros)   # mantém as imagens vivas durante a animação

        def mostrar(indice):
            if not polaroide_label.winfo_exists():
                return
            if indice >= len(quadros):
                desenhar_polaroide_do_diario()
                return
            polaroide_label.configure(image=quadros[indice])
            detalhes.after(INTERVALO_CARIMBO_MS, lambda: mostrar(indice + 1))

        mostrar(0)

    def clicar_favorito():
        ficou_favorito = usuario.alternar_favorito(filme)
        atualizar_botoes()
        if ficou_favorito:
            animar_carimbo_do_adesivo()
        ao_mudar_listas()

    def clicar_quero_ver():
        usuario.alternar_quero_assistir(filme)
        atualizar_botoes()
        ao_mudar_listas()

    def clicar_assistido():
        ficou_assistido = usuario.alternar_assistido(filme)
        atualizar_botoes()
        if ficou_assistido:
            animar_carimbo_do_adesivo("escala_carimbo")   # o WATCHED é carimbado
        montar_anotacoes()   # anotações aparecem (ou somem) junto
        ao_mudar_listas()

    botao_favorito.configure(command=clicar_favorito)

    def clicar_vi_de_novo(event=None):
        if not usuario.foi_assistido(filme):
            return
        usuario.registrar_revisita(filme)
        atualizar_botoes()
        ao_mudar_listas()

    link_vi_de_novo.bind("<Button-1>", clicar_vi_de_novo)
    botao_quero_ver.configure(command=clicar_quero_ver)
    botao_assistido.configure(command=clicar_assistido)
    atualizar_botoes()
    montar_anotacoes()

    # Estrela dada aqui também conta como "visto": as anotações aparecem
    clicar_estrela_original = clicar_estrela

    def clicar_estrela_e_anotacoes(nota):
        clicar_estrela_original(nota)
        montar_anotacoes()

    for posicao, botao_estrela in enumerate(botoes_estrela, start=1):
        botao_estrela.configure(command=lambda nota=posicao: clicar_estrela_e_anotacoes(nota))

    virar_pagina_ao_abrir(detalhes, caderno, pagina_direita, imagens_da_janela)


# ---------- animação: a página vira ao abrir um filme ----------
# Uma folha de papel cobre a página da direita e "vira" em direção à lombada,
# com uma sombrinha na borda que se mexe. A janela também aparece com um fade.
QUADROS_VIRAR_PAGINA = 9
INTERVALO_VIRAR_PAGINA_MS = 24      # ~0,2 s no total
LARGURA_SOMBRA_VIRANDO = 34


def virar_pagina_ao_abrir(janela_detalhes, caderno, pagina_direita, imagens):
    try:
        janela_detalhes.attributes("-alpha", 0.0)   # some até a página estar pronta
    except tk.TclError:
        pass

    def comecar(tentativa=0):
        if not janela_detalhes.winfo_exists():
            return
        janela_detalhes.update_idletasks()
        moldura = getattr(pagina_direita, "_parent_frame", pagina_direita)
        x, y = moldura.winfo_x(), moldura.winfo_y()
        largura, altura = moldura.winfo_width(), moldura.winfo_height()
        if largura < 10 or altura < 10:
            # A janela ainda não ganhou tamanho na tela: tenta de novo daqui a pouco.
            if tentativa < 20:
                janela_detalhes.after(25, lambda: comecar(tentativa + 1))
                return
            try:
                janela_detalhes.attributes("-alpha", 1.0)
            except tk.TclError:
                pass
            return

        folha = tk.Frame(caderno, bg=COR_PAPEL, bd=0, highlightthickness=0)
        sombra_img = ImageTk.PhotoImage(desenhar_sombra_da_dobra(LARGURA_SOMBRA_VIRANDO, altura, "esquerda"))
        imagens.append(sombra_img)
        sombra = tk.Label(folha, image=sombra_img, bd=0)
        sombra.place(relx=1.0, y=0, anchor="ne", relheight=1.0)
        folha.place(x=x, y=y, width=largura, height=altura)
        folha.lift()

        def passo(numero):
            if not folha.winfo_exists():
                return
            progresso = numero / QUADROS_VIRAR_PAGINA
            facilidade = 1 - (1 - progresso) ** 3          # começa rápido e assenta devagar
            try:
                janela_detalhes.attributes("-alpha", min(1.0, 0.25 + progresso))
            except tk.TclError:
                pass
            if numero >= QUADROS_VIRAR_PAGINA:
                folha.destroy()
                return
            folha.place_configure(width=max(1, int(largura * (1 - facilidade))))
            janela_detalhes.after(INTERVALO_VIRAR_PAGINA_MS, lambda: passo(numero + 1))

        passo(0)

    janela_detalhes.after(30, comecar)


# =========================================================
# JANELA DE COMPARAÇÃO — dois filmes frente a frente
# =========================================================
COR_VENCEDOR = "#F6E3B0"           # fundo dourado claro do valor que ganhou
TAMANHO_POSTER_COMPARACAO = (150, 222)


def criar_polaroide_comparacao(container, filme, coluna, janela_comparacao):
    """Pôster em polaroide; clicar abre o diário completo do filme."""
    polaroide = ctk.CTkFrame(
        container,
        fg_color="#FFFDF7",
        border_width=1,
        border_color=COR_BORDA_PAPEL,
        corner_radius=2,
        cursor="hand2"
    )
    polaroide.grid(row=0, column=coluna, padx=10, pady=(26, 6))

    poster = ctk.CTkLabel(
        polaroide,
        text="",
        width=TAMANHO_POSTER_COMPARACAO[0],
        height=TAMANHO_POSTER_COMPARACAO[1],
        fg_color=COR_POSTER,
        font=(FONTE_TITULO, 14),
        text_color=COR_DOURADO_CLARO,
        cursor="hand2"
    )
    poster.pack(padx=8, pady=(8, 4))
    imagem = carregar_poster(filme, TAMANHO_POSTER_COMPARACAO)
    exibir_poster(poster, imagem)
    poster.imagem = imagem

    legenda = ctk.CTkLabel(
        polaroide,
        text=f'{filme["nome"]}, {filme.get("ano", "")}',
        font=(FONTE_MANUSCRITA, 14),
        text_color=COR_TEXTO_SECUNDARIO,
        wraplength=TAMANHO_POSTER_COMPARACAO[0] + 10,
        cursor="hand2"
    )
    legenda.pack(padx=6, pady=(0, 8))

    fita = ctk.CTkLabel(container, text="", width=70, height=16, fg_color=COR_FITA, corner_radius=0)
    fita.grid(row=0, column=coluna, sticky="n", pady=(18, 0))

    vincular_clique([polaroide, poster, legenda], lambda event=None: abrir_detalhes(filme))


def abrir_comparacao(comparacao):
    """Janela "frente a frente": dois pôsteres, a tabela e o veredicto."""
    filme_a, filme_b = comparacao["filmes"]

    janela_comparacao = ctk.CTkToplevel(janela)
    janela_comparacao.title(f'{filme_a["nome"]} × {filme_b["nome"]}')
    janela_comparacao.geometry("900x740")
    janela_comparacao.minsize(820, 640)
    janela_comparacao.configure(fg_color=COR_MESA)
    janela_comparacao.transient(janela)
    janela_comparacao.grid_rowconfigure(0, weight=1)
    janela_comparacao.grid_columnconfigure(0, weight=1)

    caderno = ctk.CTkFrame(janela_comparacao, fg_color=COR_MENU, corner_radius=10)
    caderno.grid(row=0, column=0, sticky="nsew", padx=22, pady=22)
    caderno.grid_rowconfigure(0, weight=1)
    caderno.grid_columnconfigure(0, weight=1)

    pagina = ctk.CTkScrollableFrame(
        caderno,
        fg_color=COR_PAPEL,
        corner_radius=4,
        scrollbar_button_color=COR_ROLAGEM,
        scrollbar_button_hover_color=COR_ROLAGEM_HOVER
    )
    pagina.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    pagina.grid_columnconfigure(0, weight=1)

    etiqueta = ctk.CTkLabel(
        pagina,
        text="  ⚖ FRENTE A FRENTE  ",
        font=(FONTE_INTERFACE, 10, "bold"),
        text_color=COR_TEXTO_CAPA,
        fg_color=COR_VERMELHO,
        corner_radius=2,
        height=22
    )
    etiqueta.pack(pady=(22, 0))

    # ---------------- Pôsteres com o "×" no meio ----------------
    area_posters = ctk.CTkFrame(pagina, fg_color="transparent")
    area_posters.pack()

    criar_polaroide_comparacao(area_posters, filme_a, 0, janela_comparacao)
    ctk.CTkLabel(
        area_posters, text="×", font=(FONTE_TITULO, 54), text_color=COR_VERMELHO
    ).grid(row=0, column=1, padx=18)
    criar_polaroide_comparacao(area_posters, filme_b, 2, janela_comparacao)

    ctk.CTkLabel(
        pagina,
        text="clique num pôster para abrir o diário do filme",
        font=(FONTE_MANUSCRITA, 13),
        text_color=COR_TEXTO_SUAVE
    ).pack(pady=(0, 6))

    # ---------------- Tabela ----------------
    adicionar_titulo_secao(pagina, "LADO A LADO")

    tabela = ctk.CTkFrame(pagina, fg_color="transparent")
    tabela.pack(fill="x", padx=30)
    tabela.grid_columnconfigure(1, weight=1, uniform="valores")
    tabela.grid_columnconfigure(2, weight=1, uniform="valores")

    for linha_numero, linha in enumerate(comparacao["linhas"]):
        ctk.CTkLabel(
            tabela,
            text=linha["rotulo"] + ":",
            font=(FONTE_MANUSCRITA, 16, "bold"),
            text_color=COR_AZUL_CANETA,
            anchor="w",
            width=185
        ).grid(row=linha_numero * 2, column=0, sticky="nw", pady=4)

        for posicao, valor in enumerate(linha["valores"]):
            venceu = linha["vencedor"] == posicao
            ctk.CTkLabel(
                tabela,
                text=f"★ {valor}" if venceu else valor,
                font=(FONTE, 13, "bold" if venceu else "normal"),
                text_color=COR_VINHO if venceu else COR_TEXTO_CONTEUDO,
                fg_color=COR_VENCEDOR if venceu else "transparent",
                corner_radius=4,
                anchor="w",
                justify="left",
                wraplength=270
            ).grid(row=linha_numero * 2, column=1 + posicao, sticky="ew", padx=6, pady=4)

        ctk.CTkFrame(tabela, height=1, fg_color=COR_BORDA_PAPEL).grid(
            row=linha_numero * 2 + 1, column=0, columnspan=3, sticky="ew"
        )

    # ---------------- Em comum ----------------
    adicionar_titulo_secao(pagina, "EM COMUM")
    ctk.CTkLabel(
        pagina,
        text="\n".join(comparacao["em_comum"]),
        font=(FONTE, 14),
        text_color=COR_TEXTO_CONTEUDO,
        anchor="w",
        justify="left"
    ).pack(fill="x", padx=34)

    # ---------------- Veredicto (em ingressos) ----------------
    if comparacao["veredictos"]:
        adicionar_titulo_secao(pagina, "🏆 VEREDICTO", cor=COR_DOURADO)
        for veredicto in comparacao["veredictos"]:
            ingresso = ctk.CTkFrame(
                pagina,
                fg_color=COR_INGRESSO,
                border_width=2,
                border_color=COR_INGRESSO_BORDA,
                corner_radius=6
            )
            ingresso.pack(fill="x", padx=30, pady=3)
            ctk.CTkLabel(
                ingresso,
                text=veredicto,
                font=(FONTE, 13, "bold"),
                text_color=COR_VINHO,
                anchor="w",
                justify="left",
                wraplength=720
            ).pack(fill="x", padx=14, pady=8)

    ctk.CTkButton(
        pagina,
        text="FECHAR",
        width=150,
        height=36,
        corner_radius=4,
        font=(FONTE_INTERFACE, 12, "bold"),
        fg_color=COR_VINHO,
        hover_color=COR_VERMELHO,
        text_color=COR_TEXTO_CAPA,
        command=janela_comparacao.destroy
    ).pack(pady=(20, 26))


# =========================================================
# MENU LATERAL — a capa vermelha do diário
# =========================================================
menu = ctk.CTkFrame(janela, width=240, corner_radius=0, fg_color=COR_MENU)
menu.grid(row=0, column=0, sticky="nsew")
menu.grid_propagate(False)
menu.grid_rowconfigure(0, weight=1)
menu.grid_columnconfigure(1, weight=1)


def criar_pelicula(container, quantidade_furos=26):
    """Tira de película preta com furos, como na borda da capa."""
    pelicula = ctk.CTkFrame(container, width=22, fg_color=COR_PELICULA, corner_radius=0)
    pelicula.pack_propagate(False)

    for _ in range(quantidade_furos):
        furo = ctk.CTkFrame(pelicula, width=10, height=8, fg_color=COR_FURO_PELICULA, corner_radius=2)
        furo.pack(pady=(9, 9))

    return pelicula


pelicula_menu = criar_pelicula(menu)
pelicula_menu.grid(row=0, column=0, sticky="ns")

conteudo_menu = ctk.CTkFrame(menu, fg_color="transparent")
conteudo_menu.grid(row=0, column=1, sticky="nsew")


# ---------------- Textura de tecido da capa (bem sutil) ----------------
# Uma imagem "atrás" de tudo no menu. Ela precisa ser o PRIMEIRO filho do
# conteúdo para ficar embaixo dos botões e textos.
def desenhar_textura_capa(largura, altura, intensidade):
    sorteio = random.Random(2024)
    vermelho = cor_rgb(COR_MENU)
    textura = Image.new("RGB", (largura, altura), vermelho)
    lapis = ImageDraw.Draw(textura)
    # Fios de tecido: linhas horizontais e verticais um tiquinho mais claras/escuras
    for y in range(0, altura, 3):
        variacao = sorteio.randint(-intensidade, intensidade)
        lapis.line([(0, y), (largura, y)], fill=tuple(max(0, min(255, c + variacao)) for c in vermelho))
    for x in range(0, largura, 3):
        variacao = sorteio.randint(-intensidade, intensidade) // 2
        if variacao:
            cor = tuple(max(0, min(255, c + variacao)) for c in vermelho)
            lapis.line([(x, 0), (x, altura)], fill=cor)
    return textura.filter(ImageFilter.GaussianBlur(0.6))


textura_capa_label = tk.Label(conteudo_menu, bd=0, highlightthickness=0, bg=COR_MENU)
estado_textura_capa = {"tamanho": None}


def aplicar_textura_capa(event=None):
    if INTENSIDADE_TEXTURA_CAPA <= 0:
        return
    largura, altura = conteudo_menu.winfo_width(), conteudo_menu.winfo_height()
    if largura < 20 or altura < 20 or estado_textura_capa["tamanho"] == (largura, altura):
        return
    estado_textura_capa["tamanho"] = (largura, altura)
    foto = ImageTk.PhotoImage(desenhar_textura_capa(largura, altura, INTENSIDADE_TEXTURA_CAPA))
    textura_capa_label.configure(image=foto)
    textura_capa_label.imagem = foto


if INTENSIDADE_TEXTURA_CAPA > 0:
    textura_capa_label.place(x=0, y=0, relwidth=1, relheight=1)
    conteudo_menu.bind("<Configure>", aplicar_textura_capa, add="+")


# ---------------- Lombada: faixa escura com costura ----------------
lombada_menu = tk.Canvas(menu, width=LARGURA_LOMBADA, bg=COR_LOMBADA, highlightthickness=0, bd=0)
lombada_menu.grid(row=0, column=2, sticky="ns")


def desenhar_lombada(event=None):
    lombada_menu.delete("all")
    altura = lombada_menu.winfo_height()
    largura = lombada_menu.winfo_width()
    # brilho fininho na dobra + linha de sombra
    lombada_menu.create_line(1, 0, 1, altura, fill="#9A2620")
    lombada_menu.create_line(largura - 1, 0, largura - 1, altura, fill="#5A110E")
    # costura: tracinhos verticais
    meio = largura // 2
    lombada_menu.create_line(meio, 4, meio, altura - 4, fill=COR_COSTURA, dash=(5, 6), width=1)


lombada_menu.bind("<Configure>", desenhar_lombada)

marca_menu = ctk.CTkLabel(
    conteudo_menu,
    text="★  MOVIE NIGHT  ★",
    font=(FONTE_INTERFACE, 10, "bold"),
    text_color=COR_DOURADO_CLARO
)
marca_menu.pack(pady=(30, 0))

logo = ctk.CTkLabel(
    conteudo_menu,
    text="CineAI",
    font=(FONTE_TITULO, 44),
    text_color=COR_TEXTO_CAPA
)
logo.pack(pady=(0, 0))

lema_menu = ctk.CTkLabel(
    conteudo_menu,
    text="lights • camera • action!",
    font=(FONTE_MANUSCRITA, 15),
    text_color=COR_DOURADO_CLARO
)
lema_menu.pack()

linha_menu = ctk.CTkLabel(
    conteudo_menu,
    text="- - - - - - - - - - - - - - -",
    font=(FONTE_INTERFACE, 10),
    text_color="#D9837A"
)
linha_menu.pack(pady=(10, 18))


# =========================================================
# ÍCONES DESENHADOS À MÃO (caneta) PARA O MENU
# =========================================================
# Cada ícone é desenhado 4x maior com traço de caneta (pontas redondas e um
# tremidinho de mão) e depois reduzido: fica com cara de rabisco no diário.
ESCALA_DESENHO_ICONE = 4


def traco_de_caneta(lapis, pontos, cor, espessura, sorteio, fechado=False):
    """Linha com leve tremido e pontas redondas, ligando os pontos."""
    tremidos = [(x + sorteio.uniform(-1.2, 1.2), y + sorteio.uniform(-1.2, 1.2)) for x, y in pontos]
    if fechado:
        tremidos.append(tremidos[0])
    lapis.line(tremidos, fill=cor, width=espessura, joint="curve")
    raio = espessura / 2
    for x, y in (tremidos[0], tremidos[-1]):
        lapis.ellipse([x - raio, y - raio, x + raio, y + raio], fill=cor)


def pontos_do_circulo(centro_x, centro_y, raio, quantidade=28, inicio=0.0, fim=360.0):
    import math
    return [
        (centro_x + raio * math.cos(math.radians(inicio + (fim - inicio) * passo / quantidade)),
         centro_y + raio * math.sin(math.radians(inicio + (fim - inicio) * passo / quantidade)))
        for passo in range(quantidade + 1)
    ]


def desenhar_icone(nome, cor):
    """Desenha o ícone 'nome' numa imagem de 80x80 (depois vira 20x20)."""
    import math
    tamanho = TAMANHO_ICONE_MENU * ESCALA_DESENHO_ICONE
    imagem = Image.new("RGBA", (tamanho, tamanho), (0, 0, 0, 0))
    lapis = ImageDraw.Draw(imagem)
    sorteio = random.Random(nome)          # o mesmo tremido sempre
    t = tamanho / 100                      # desenhamos numa grade de 0 a 100
    espessura = int(7 * t)

    def p(x, y):
        return (x * t, y * t)

    def traco(*pontos, fechado=False):
        traco_de_caneta(lapis, [p(x, y) for x, y in pontos], cor, espessura, sorteio, fechado)

    if nome == "casa":
        traco((14, 50), (50, 16), (86, 50))                       # telhado
        traco((24, 42), (24, 86), (76, 86), (76, 42))             # paredes
        traco((42, 86), (42, 62), (58, 62), (58, 86))             # porta
    elif nome == "lupa":
        traco_de_caneta(lapis, pontos_do_circulo(42 * t, 42 * t, 26 * t), cor, espessura, sorteio)
        traco((61, 61), (86, 86))
    elif nome == "brilho":
        # estrela de 4 pontas (✦) com os lados curvinhos, e um brilho pequeno ao lado
        traco((44, 10), (52, 40), (80, 48), (52, 56), (44, 88), (36, 56), (10, 48), (36, 40), fechado=True)
        traco((80, 12), (80, 30))
        traco((71, 21), (89, 21))
    elif nome == "coracao":
        contorno = []
        for passo in range(41):
            angulo = math.radians(passo * 9)
            x = 16 * math.sin(angulo) ** 3
            y = -(13 * math.cos(angulo) - 5 * math.cos(2 * angulo) - 2 * math.cos(3 * angulo) - math.cos(4 * angulo))
            contorno.append(p(50 + x * 2.4, 46 + y * 2.4))
        traco_de_caneta(lapis, contorno, cor, espessura, sorteio)
    elif nome == "estrela":
        pontos = []
        for indice in range(10):
            raio = 40 if indice % 2 == 0 else 17
            angulo = math.radians(-90 + indice * 36)
            pontos.append((50 + raio * math.cos(angulo), 54 + raio * math.sin(angulo)))
        traco(*pontos, fechado=True)
    elif nome == "caneta":
        traco((22, 78), (70, 30), (82, 42), (34, 90), (16, 92), (22, 78))
        traco((62, 38), (74, 50))
    elif nome == "olho":
        traco_de_caneta(lapis, pontos_do_circulo(50 * t, 82 * t, 52 * t, inicio=205, fim=335), cor, espessura, sorteio)
        traco_de_caneta(lapis, pontos_do_circulo(50 * t, 18 * t, 52 * t, inicio=25, fim=155), cor, espessura, sorteio)
        lapis.ellipse([p(39, 39), p(61, 61)], fill=cor)
    else:
        traco((20, 50), (80, 50))

    return imagem


ICONES_DO_MENU = {"⌂": "casa", "⌕": "lupa", "✦": "brilho", "♥": "coracao",
                  "★": "estrela", "✎": "caneta", "◈": "olho"}
cache_icones = {}


def icone_desenhado(nome, cor_hex):
    chave = (nome, cor_hex)
    if chave not in cache_icones:
        desenho = desenhar_icone(nome, cor_rgb(cor_hex) + (255,))
        cache_icones[chave] = ctk.CTkImage(
            light_image=desenho, dark_image=desenho,
            size=(TAMANHO_ICONE_MENU, TAMANHO_ICONE_MENU)
        )
    return cache_icones[chave]


class BotaoMenu(ctk.CTkFrame):
    """
    Item do menu: o ícone fica numa coluna de largura fixa e o texto ao lado,
    assim todos os nomes começam alinhados (cada símbolo tem uma largura).
    Aceita configure(fg_color=..., text_color=..., hover_color=..., command=...)
    como um CTkButton, para a navegação não precisar saber a diferença.
    """

    def __init__(self, master, icone, texto):
        super().__init__(master, height=44, corner_radius=4, fg_color="transparent", cursor="hand2")
        self.pack_propagate(False)

        self._comando = None
        self._cor_fundo = "transparent"
        self._cor_hover = COR_MENU_HOVER

        # Ícone desenhado à mão (ou o símbolo, se não houver desenho para ele)
        self.nome_icone = ICONES_DO_MENU.get(icone)
        if self.nome_icone:
            self.icone = ctk.CTkLabel(
                self, text="", width=26,
                image=icone_desenhado(self.nome_icone, COR_TEXTO_CAPA), cursor="hand2"
            )
        else:
            self.icone = ctk.CTkLabel(
                self, text=icone, width=26, font=(FONTE_SIMBOLOS, 15),
                text_color=COR_TEXTO_CAPA, cursor="hand2"
            )
        self.icone.pack(side="left", padx=(12, 8))

        self.texto = ctk.CTkLabel(
            self,
            text=texto,
            font=(FONTE_INTERFACE, 14, "bold"),
            text_color=COR_TEXTO_CAPA,
            anchor="w",
            cursor="hand2"
        )
        self.texto.pack(side="left", fill="x", expand=True)

        for parte in (self, self.icone, self.texto):
            parte.bind("<Button-1>", self._clicar)
            parte.bind("<Enter>", self._entrar)
            parte.bind("<Leave>", self._sair)

    def _clicar(self, event=None):
        if self._comando is not None:
            self._comando()

    def _entrar(self, event=None):
        super().configure(fg_color=self._cor_hover)

    def _sair(self, event=None):
        super().configure(fg_color=self._cor_fundo)

    def configure(self, **opcoes):
        if "command" in opcoes:
            self._comando = opcoes.pop("command")
        if "hover_color" in opcoes:
            self._cor_hover = opcoes.pop("hover_color")
        if "text_color" in opcoes:
            cor_texto = opcoes.pop("text_color")
            if self.nome_icone:
                self.icone.configure(image=icone_desenhado(self.nome_icone, cor_texto))
            else:
                self.icone.configure(text_color=cor_texto)
            self.texto.configure(text_color=cor_texto)
        if "fg_color" in opcoes:
            self._cor_fundo = opcoes["fg_color"]
        if opcoes:
            super().configure(**opcoes)


def criar_botao_menu(icone, texto):
    botao = BotaoMenu(conteudo_menu, icone, texto)
    botao.pack(fill="x", padx=(10, 14), pady=3)
    return botao


botao_inicio = criar_botao_menu("⌂", "Início")
botao_buscar_menu = criar_botao_menu("⌕", "Catálogo")
botao_recomendacoes = criar_botao_menu("✦", "Recomendações")
botao_meus_filmes_menu = criar_botao_menu("♥", "Meu diário")
botao_perfil_menu = criar_botao_menu("★", "Meu perfil")
botao_chat_menu = criar_botao_menu("✎", "Chat CineAI")
botao_rag_menu = criar_botao_menu("◈", "Painel do RAG")

botoes_menu = [
    botao_inicio,
    botao_buscar_menu,
    botao_recomendacoes,
    botao_meus_filmes_menu,
    botao_perfil_menu,
    botao_chat_menu,
    botao_rag_menu
]

# Rodapé: um ingresso "ADMIT ONE"
ingresso_menu = ctk.CTkFrame(
    conteudo_menu,
    fg_color=COR_INGRESSO,
    border_width=2,
    border_color=COR_INGRESSO_BORDA,
    corner_radius=6
)
ingresso_menu.pack(side="bottom", fill="x", padx=(10, 14), pady=24)

ingresso_titulo = ctk.CTkLabel(
    ingresso_menu,
    text=f"🎟  {TEXTO_INGRESSO_MENU}",
    font=(FONTE_TITULO, 16),
    text_color=COR_VERMELHO
)
ingresso_titulo.pack(pady=(8, 0))

ingresso_texto = ctk.CTkLabel(
    ingresso_menu,
    text="seu diário de cinema",
    font=(FONTE_MANUSCRITA, 14),
    text_color=COR_VINHO
)
ingresso_texto.pack(pady=(0, 8))


# =========================================================
# ÁREA PRINCIPAL E PÁGINAS
# =========================================================
area_principal = ctk.CTkFrame(janela, corner_radius=0, fg_color=COR_FUNDO)
area_principal.grid(row=0, column=1, sticky="nsew")
area_principal.grid_rowconfigure(0, weight=1)
area_principal.grid_columnconfigure(0, weight=1)

pagina_inicio = ctk.CTkScrollableFrame(
    area_principal,
    corner_radius=0,
    fg_color=COR_FUNDO,
    scrollbar_button_color=COR_ROLAGEM,
    scrollbar_button_hover_color=COR_ROLAGEM_HOVER
)
pagina_inicio.grid_columnconfigure(0, weight=1)


def criar_pagina(linha_que_cresce):
    pagina = ctk.CTkFrame(area_principal, corner_radius=0, fg_color=COR_FUNDO)
    pagina.grid_rowconfigure(linha_que_cresce, weight=1)
    pagina.grid_columnconfigure(0, weight=1)
    return pagina


pagina_catalogo = criar_pagina(3)
pagina_recomendacoes = criar_pagina(1)
pagina_chat = criar_pagina(1)
pagina_meus_filmes = criar_pagina(2)
pagina_perfil = criar_pagina(3)
pagina_rag = criar_pagina(1)


def criar_cabecalho_pagina(pagina, titulo, subtitulo):
    """Cabeçalho de página de diário: etiqueta, letreiro, anotação e linha."""
    cabecalho = ctk.CTkFrame(pagina, fg_color="transparent")
    cabecalho.grid(row=0, column=0, sticky="ew", padx=42, pady=(26, 14))

    etiqueta = ctk.CTkLabel(
        cabecalho,
        text="  ✦ MOVIE JOURNAL  ",
        font=(FONTE_INTERFACE, 10, "bold"),
        text_color=COR_TEXTO_CAPA,
        fg_color=COR_VERMELHO,
        corner_radius=2,
        height=22
    )
    etiqueta.pack(anchor="w", pady=(0, 6))

    titulo_label = ctk.CTkLabel(
        cabecalho,
        text=titulo.upper(),
        font=(FONTE_TITULO, 36),
        text_color=COR_TEXTO,
        anchor="w"
    )
    titulo_label.pack(fill="x")

    subtitulo_label = ctk.CTkLabel(
        cabecalho,
        text=subtitulo,
        font=(FONTE_MANUSCRITA, 17),
        text_color=COR_TEXTO_SECUNDARIO,
        anchor="w"
    )
    subtitulo_label.pack(fill="x", pady=(0, 6))

    linha = ctk.CTkFrame(cabecalho, height=3, fg_color=COR_VERMELHO, corner_radius=0)
    linha.pack(fill="x")

    return cabecalho


def criar_titulo_manuscrito(container, texto, nome_icone="estrela"):
    """
    Título escrito à mão em caneta azul, com um rabisco desenhado antes
    e uma passada de marca-texto rosa embaixo (o jeito do seu diário).
    """
    caixa = ctk.CTkFrame(container, fg_color="transparent")

    linha = ctk.CTkFrame(caixa, fg_color="transparent")
    linha.pack(anchor="w")

    desenho = desenhar_icone(nome_icone, cor_rgb(COR_RABISCO) + (255,))
    imagem_icone = ctk.CTkImage(light_image=desenho, dark_image=desenho, size=(22, 22))
    ctk.CTkLabel(linha, text="", image=imagem_icone, width=26).pack(side="left", padx=(0, 6))

    ctk.CTkLabel(
        linha, text=texto, font=(FONTE_MANUSCRITA, 23, "bold"), text_color=COR_TITULO_MANUSCRITO
    ).pack(side="left")

    marca_texto = ctk.CTkFrame(caixa, height=6, fg_color=COR_MARCA_TEXTO, corner_radius=3)
    marca_texto.pack(anchor="w", padx=(30, 0), pady=(0, 2))
    marca_texto.configure(width=min(380, 11 * len(texto)))
    return caixa


def criar_titulo_secao(container, texto):
    """Título de seção em letreiro vermelho."""
    return ctk.CTkLabel(
        container,
        text=texto,
        font=(FONTE_TITULO, 20),
        text_color=COR_VERMELHO,
        anchor="w"
    )


# =========================================================
# PÁGINA INICIAL — LETREIRO DE CINEMA
# =========================================================
# Versão delicada: papel creme com borda vermelha fina, letreiro em vermelho
# e lâmpadas douradas pequenas (antes era um bloco vinho escuro).
letreiro = ctk.CTkFrame(
    pagina_inicio,
    fg_color=COR_PAPEL,
    border_width=2,
    border_color=COR_VERMELHO,
    corner_radius=10
)
letreiro.grid(row=0, column=0, sticky="ew", padx=42, pady=(26, 0))

QUANTIDADE_LAMPADAS = 44


def criar_fileira_lampadas(container):
    """Fileira de lâmpadas douradas do letreiro (bolinhas desenhadas)."""
    fileira = ctk.CTkFrame(container, fg_color="transparent", height=10)
    for posicao in range(QUANTIDADE_LAMPADAS):
        fileira.grid_columnconfigure(posicao, weight=1)
        lampada = ctk.CTkFrame(fileira, width=6, height=6, corner_radius=3, fg_color=COR_DOURADO)
        lampada.grid(row=0, column=posicao, pady=2)
    return fileira


lampadas_topo = criar_fileira_lampadas(letreiro)
lampadas_topo.pack(fill="x", padx=18, pady=(10, 0))

etiqueta_letreiro = ctk.CTkLabel(
    letreiro,
    text="✦ NOW PLAYING ✦",
    font=(FONTE_INTERFACE, 10, "bold"),
    text_color=COR_DOURADO,
    height=16
)
etiqueta_letreiro.pack(pady=(4, 0))

titulo_inicio = ctk.CTkLabel(
    letreiro,
    text="O QUE VAMOS ASSISTIR HOJE?",
    font=(FONTE_TITULO, 30),
    text_color=COR_VERMELHO,
    height=38
)
titulo_inicio.pack(padx=20)

subtitulo_inicio = ctk.CTkLabel(
    letreiro,
    text="Conte ao CineAI o que você está com vontade de ver",
    font=(FONTE_MANUSCRITA, 16),
    text_color=COR_TEXTO_SECUNDARIO,
    height=22
)
subtitulo_inicio.pack(pady=(0, 4))

lampadas_base = criar_fileira_lampadas(letreiro)
lampadas_base.pack(fill="x", padx=18, pady=(0, 10))

# =========================================================
# PÁGINA INICIAL — PELÍCULA DA CONTAGEM 5-4-3-2-1
# =========================================================
# Desenhada como imagem, igual à "contagem de início" dos rolos de filme:
# fundo preto arranhado, furos em cima e embaixo e, em cada quadro,
# a cruz, os dois círculos, o quadrante cinza e o número.
def carregar_fonte_contagem(tamanho):
    for nome_fonte in FONTES_NUMERO_CONTAGEM:
        try:
            return ImageFont.truetype(nome_fonte, tamanho)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=tamanho)  # Pillow 10.1 ou mais novo
    except TypeError:
        return ImageFont.load_default()


def desenhar_arranhoes(imagem, largura, altura, sorteio):
    """Riscos e manchas brancas de filme antigo sobre o preto."""
    camada = Image.new("RGBA", (largura, altura), (0, 0, 0, 0))
    lapis = ImageDraw.Draw(camada)

    for _ in range(largura // 3):  # riscos finos
        x = sorteio.randint(0, largura)
        y = sorteio.randint(0, altura)
        comprimento = sorteio.randint(4, 40)
        inclinacao = sorteio.randint(-12, 12)
        opacidade = sorteio.randint(40, 150)
        lapis.line(
            [(x, y), (x + inclinacao, y + comprimento)],
            fill=(255, 255, 255, opacidade),
            width=sorteio.choice([1, 1, 2])
        )

    for _ in range(largura // 2):  # pontinhos de poeira
        x = sorteio.randint(0, largura)
        y = sorteio.randint(0, altura)
        raio = sorteio.choice([1, 1, 2, 3])
        lapis.ellipse([x, y, x + raio, y + raio], fill=(255, 255, 255, sorteio.randint(60, 200)))

    camada = camada.filter(ImageFilter.GaussianBlur(0.6))
    imagem.alpha_composite(camada)


# ---------------- Película animada: o rolo passa e o ponteiro gira ----------------
# A cada "quadro da animação" (a cada INTERVALO_PELICULA_MS):
#   - a fita anda alguns pixels para a esquerda (quadros e furos juntos);
#   - em cada quadro, o ponteiro da contagem gira e escurece o círculo;
#   - riscos e poeira ficam parados, como sujeira na lente do projetor.
# Para ser leve: o fundo (preto + riscos) e o desenho fixo de cada número
# (cruz, círculos e número) são feitos UMA vez; a cada passo só o ponteiro
# é redesenhado e a imagem é atualizada no mesmo lugar (PhotoImage.paste).
INTERVALO_PELICULA_MS = 40          # 25 quadros por segundo
VELOCIDADE_PELICULA = 0.5           # pontos por passo (bem devagar)
VELOCIDADE_PELICULA_PENSANDO = 3.0  # mais rápido enquanto o CineAI pensa
VOLTA_DO_PONTEIRO_MS = 2500         # tempo de uma volta do ponteiro

# Depois do "1": clarão do projetor e o letreiro "CineAI" parado no centro
DURACAO_CLARAO_MS = 900
PAUSA_NO_LETREIRO_MS = 3200
PISCA_LAMPADAS_MS = 380
LARGURA_LETREIRO = 2.8              # em "quadros" (o letreiro é mais largo)
TEXTO_LETREIRO_PELICULA = "CineAI"   # as estrelinhas dos lados são desenhadas

COR_QUADRO_CLARO = (222, 222, 220, 255)
COR_QUADRO_ESCURO = (150, 150, 148, 255)
COR_TRACO_CONTAGEM = (40, 40, 40, 255)
COR_FURO_RGBA = (241, 228, 200, 255)


def medidas_da_pelicula(altura):
    faixa_furos = int(altura * 0.16)
    altura_quadro = altura - 2 * faixa_furos - int(altura * 0.06)
    largura_quadro = int(altura_quadro * PROPORCAO_QUADRO_CONTAGEM)
    largura_furo = max(4, int(faixa_furos * 0.75))
    return {
        "faixa_furos": faixa_furos,
        "altura_quadro": altura_quadro,
        "largura_quadro": largura_quadro,
        "espaco_quadros": max(int(largura_quadro * 0.9), int(altura * 0.3)),
        "largura_furo": largura_furo,
        "altura_furo": max(3, int(faixa_furos * 0.5)),
        "passo_furo": max(8, int(largura_furo * 1.9)),
    }


def desenhar_tracos_do_numero(largura, altura, numero, fonte):
    """Camada fixa de cada quadro: cruz, dois círculos, número e borda (fundo transparente)."""
    camada = Image.new("RGBA", (largura, altura), (0, 0, 0, 0))
    lapis = ImageDraw.Draw(camada)
    centro_x, centro_y = largura // 2, altura // 2
    espessura = max(1, altura // 40)

    lapis.line([(0, centro_y), (largura, centro_y)], fill=COR_TRACO_CONTAGEM, width=espessura)
    lapis.line([(centro_x, 0), (centro_x, altura)], fill=COR_TRACO_CONTAGEM, width=espessura)
    for raio in (int(altura * 0.36), int(altura * 0.42)):
        lapis.ellipse(
            [centro_x - raio, centro_y - raio, centro_x + raio, centro_y + raio],
            outline=COR_TRACO_CONTAGEM, width=espessura
        )
    lapis.text((centro_x, centro_y), numero, font=fonte, fill=(15, 15, 15, 255), anchor="mm")
    lapis.rectangle([0, 0, largura - 1, altura - 1], outline=(20, 20, 20, 255), width=espessura)
    return camada


def desenhar_estrelinha(lapis, centro_x, centro_y, tamanho, cor):
    """Estrela de 4 pontas (✦) desenhada com um polígono."""
    fino = tamanho * 0.28
    pontos = [
        (centro_x, centro_y - tamanho), (centro_x + fino, centro_y - fino),
        (centro_x + tamanho, centro_y), (centro_x + fino, centro_y + fino),
        (centro_x, centro_y + tamanho), (centro_x - fino, centro_y + fino),
        (centro_x - tamanho, centro_y), (centro_x - fino, centro_y - fino),
    ]
    lapis.polygon(pontos, fill=cor)


def desenhar_quadro_animado(tracos, angulo):
    """Quadro cinza + ponteiro (setor escuro que cresce a partir do topo) + traços por cima."""
    largura, altura = tracos.size
    quadro = Image.new("RGBA", (largura, altura), COR_QUADRO_CLARO)
    lapis = ImageDraw.Draw(quadro)
    raio = int((largura ** 2 + altura ** 2) ** 0.5 / 2) + 2  # cobre o quadro inteiro
    centro_x, centro_y = largura // 2, altura // 2
    if angulo > 0.5:
        lapis.pieslice(
            [centro_x - raio, centro_y - raio, centro_x + raio, centro_y + raio],
            start=-90, end=-90 + angulo, fill=COR_QUADRO_ESCURO
        )
    quadro.alpha_composite(tracos)
    return quadro


class PeliculaAnimada:
    """
    O rolo passa devagar: 5, 4, 3, 2, 1. Quando o "1" cruza o meio, o projetor
    dá um clarão; logo depois chega o letreiro "CineAI", que fica parado no
    centro alguns segundos com as lâmpadas piscando. Aí tudo recomeça no 5.
    """

    def __init__(self, frame, label):
        self.frame = frame
        self.label = label
        self.largura = 0
        self.altura = 0
        self.fundo = None
        self.foto = None
        self.tracos = {}
        self.letreiro = []          # duas versões: lâmpadas acesas / apagadas
        self.medidas = None
        self.itens = []             # [(tipo, valor, inicio_no_ciclo, largura)]
        self.ciclo = 1
        self.fase_do_um = 0         # deslocamento em que o "1" está no meio da tela
        self.fase_do_letreiro = 0   # deslocamento em que o letreiro está no meio
        self.deslocamento = 0.0
        self.velocidade = VELOCIDADE_PELICULA
        self.agendamento = None
        self.inicio_ms = 0
        self.clarao_desde = None
        self.pausa_ate = 0

    def agora_ms(self):
        return int(janela.tk.call("clock", "milliseconds"))

    # ---------- montagem (quando a janela muda de tamanho) ----------
    def montar(self, largura, altura):
        self.largura, self.altura = largura, altura
        self.medidas = medidas_da_pelicula(altura)
        largura_quadro = self.medidas["largura_quadro"]
        altura_quadro = self.medidas["altura_quadro"]
        espaco = self.medidas["espaco_quadros"]

        fundo = Image.new("RGBA", (largura, altura), (16, 14, 13, 255))
        desenhar_arranhoes(fundo, largura, altura, random.Random(54321))
        self.fundo = fundo

        fonte = carregar_fonte_contagem(int(altura_quadro * 0.62))
        self.tracos = {
            numero: desenhar_tracos_do_numero(largura_quadro, altura_quadro, numero, fonte)
            for numero in NUMEROS_CONTAGEM
        }

        largura_letreiro = int(largura_quadro * LARGURA_LETREIRO)
        self.letreiro = [
            self.desenhar_letreiro(largura_letreiro, altura_quadro, acesas)
            for acesas in (True, False)
        ]

        # O ciclo: 5 4 3 2 1, um respiro, o letreiro e outro respiro
        self.itens = []
        posicao = 0
        for numero in NUMEROS_CONTAGEM:
            self.itens.append(("numero", numero, posicao, largura_quadro))
            posicao += largura_quadro + espaco
        posicao += espaco
        self.itens.append(("letreiro", None, posicao, largura_letreiro))
        posicao += largura_letreiro + espaco * 3
        self.ciclo = posicao

        centro = largura / 2
        _, _, inicio_um, largura_um = self.itens[len(NUMEROS_CONTAGEM) - 1]
        _, _, inicio_letreiro, _ = self.itens[-1]
        self.fase_do_um = (inicio_um + largura_um / 2 - centro) % self.ciclo
        self.fase_do_letreiro = (inicio_letreiro + largura_letreiro / 2 - centro) % self.ciclo

        # Começa com o 5 entrando pela direita
        self.deslocamento = -largura * 0.55

        self.foto = ImageTk.PhotoImage(Image.new("RGB", (largura, altura)))
        self.label.configure(image=self.foto)
        self.label.imagem = self.foto
        self.desenhar()

    def desenhar_letreiro(self, largura, altura, lampadas_acesas):
        """Quadro especial: letreiro vermelho "CineAI" com lâmpadas douradas em volta."""
        letreiro = Image.new("RGBA", (largura, altura), cor_rgb(COR_MENU) + (255,))
        lapis = ImageDraw.Draw(letreiro)
        margem = max(3, altura // 9)
        lapis.rectangle(
            [margem // 2, margem // 2, largura - margem // 2 - 1, altura - margem // 2 - 1],
            outline=cor_rgb(COR_DOURADO) + (255,), width=max(1, altura // 30)
        )

        # Lâmpadas: acesas = dourado claro; apagadas = dourado escuro (pisca alternando)
        raio = max(1, altura // 22)
        quantidade = max(6, largura // (raio * 5))
        for indice in range(quantidade):
            x = int(margem + indice * (largura - 2 * margem) / (quantidade - 1))
            acesa = (indice % 2 == 0) == lampadas_acesas
            cor = cor_rgb(COR_DOURADO_CLARO if acesa else COR_DOURADO) + (255,)
            for y in (margem, altura - margem):
                lapis.ellipse([x - raio, y - raio, x + raio, y + raio], fill=cor)

        fonte = fonte_pil(FONTES_CARIMBO_PIL, int(altura * 0.48))
        cor_texto = cor_rgb(COR_TEXTO_CAPA) + (255,)
        lapis.text((largura // 2, altura // 2), TEXTO_LETREIRO_PELICULA, font=fonte, fill=cor_texto, anchor="mm")

        # Estrelinhas de 4 pontas dos lados (desenhadas: a fonte de letreiro não tem ✦)
        meia_largura_texto = lapis.textlength(TEXTO_LETREIRO_PELICULA, font=fonte) / 2
        tamanho_estrela = max(3, int(altura * 0.13))
        for lado in (-1, 1):
            centro_x = largura / 2 + lado * (meia_largura_texto + tamanho_estrela * 2)
            desenhar_estrelinha(lapis, centro_x, altura / 2, tamanho_estrela, cor_rgb(COR_DOURADO_CLARO) + (255,))
        return letreiro

    # ---------- um passo da animação ----------
    def desenhar(self):
        if self.fundo is None:
            return
        medidas = self.medidas
        imagem = self.fundo.copy()
        lapis = ImageDraw.Draw(imagem)
        agora = self.agora_ms()

        # Furos andando com a fita
        passo_furo = medidas["passo_furo"]
        faixa, largura_furo, altura_furo = medidas["faixa_furos"], medidas["largura_furo"], medidas["altura_furo"]
        raio_furo = max(1, altura_furo // 4)
        x = -(self.deslocamento % passo_furo)
        while x < self.largura:
            for y in ((faixa - altura_furo) // 2, self.altura - faixa + (faixa - altura_furo) // 2):
                lapis.rounded_rectangle(
                    [int(x), y, int(x) + largura_furo, y + altura_furo],
                    radius=raio_furo, fill=COR_FURO_RGBA
                )
            x += passo_furo

        # Quadros do ciclo (o ciclo se repete, então desenhamos a volta atual e a próxima)
        y0 = (self.altura - medidas["altura_quadro"]) // 2
        angulo = ((agora - self.inicio_ms) % VOLTA_DO_PONTEIRO_MS) / VOLTA_DO_PONTEIRO_MS * 360
        lampadas_acesas = (agora // PISCA_LAMPADAS_MS) % 2 == 0
        inicio_volta = -(self.deslocamento % self.ciclo)

        for volta in (inicio_volta, inicio_volta + self.ciclo):
            for tipo, valor, inicio, largura_item in self.itens:
                x = volta + inicio
                if x > self.largura or x + largura_item < 0:
                    continue
                if tipo == "numero":
                    quadro = desenhar_quadro_animado(self.tracos[valor], angulo)
                else:
                    quadro = self.letreiro[0 if lampadas_acesas else 1]
                imagem.paste(quadro, (int(x), y0))

        # Clarão do projetor (luz creme que acende e vai apagando, com uma piscada)
        if self.clarao_desde is not None:
            tempo = agora - self.clarao_desde
            if tempo >= DURACAO_CLARAO_MS:
                self.clarao_desde = None
            else:
                forca = 1 - tempo / DURACAO_CLARAO_MS
                if 120 < tempo < 200:
                    forca *= 0.35  # a piscada
                luz = Image.new("RGBA", imagem.size, (255, 246, 222, int(215 * forca)))
                imagem.alpha_composite(luz)

        self.foto.paste(imagem.convert("RGB"))

    # ---------- relógio ----------
    def passou_por(self, anterior, atual, fase):
        """True se o deslocamento cruzou a "fase" (o ciclo dá a volta)."""
        voltas = int((atual - anterior) // self.ciclo) + 1
        for volta in range(-1, voltas + 1):
            alvo = fase + (anterior // self.ciclo + volta) * self.ciclo
            if anterior < alvo <= atual:
                return True
        return False

    def passo(self):
        self.agendamento = None
        if self.frame.winfo_ismapped() and self.fundo is not None:
            agora = self.agora_ms()
            if agora >= self.pausa_ate:
                anterior = self.deslocamento
                self.deslocamento += self.velocidade * escala_da_tela(self.frame)

                if self.passou_por(anterior, self.deslocamento, self.fase_do_um):
                    self.clarao_desde = agora
                if self.passou_por(anterior, self.deslocamento, self.fase_do_letreiro):
                    # Para com o letreiro no meio (se o CineAI estiver pensando, para menos)
                    pausa = PAUSA_NO_LETREIRO_MS if self.velocidade == VELOCIDADE_PELICULA else 600
                    self.pausa_ate = agora + pausa
            self.desenhar()
        self.agendamento = self.frame.after(INTERVALO_PELICULA_MS, self.passo)

    def comecar(self):
        if self.agendamento is None:
            self.inicio_ms = self.agora_ms()
            self.passo()

    def acelerar(self, pensando):
        self.velocidade = VELOCIDADE_PELICULA_PENSANDO if pensando else VELOCIDADE_PELICULA


pelicula_contagem = ctk.CTkFrame(
    pagina_inicio, fg_color=COR_PELICULA, corner_radius=0, height=ALTURA_PELICULA_CONTAGEM
)
pelicula_contagem.grid(row=1, column=0, sticky="ew", padx=42, pady=(14, 0))
pelicula_contagem.pack_propagate(False)

# Label simples do Tk: a imagem é trocada 25 vezes por segundo, no mesmo lugar.
imagem_contagem_label = tk.Label(pelicula_contagem, bg=COR_PELICULA, bd=0, highlightthickness=0)
imagem_contagem_label.pack(fill="both", expand=True)

pelicula_animada = PeliculaAnimada(pelicula_contagem, imagem_contagem_label)
estado_pelicula = {"agendamento": None}


def remontar_pelicula():
    estado_pelicula["agendamento"] = None
    largura = pelicula_contagem.winfo_width()
    altura = pelicula_contagem.winfo_height()
    if largura < 100 or altura < 20:
        return
    if (largura, altura) != (pelicula_animada.largura, pelicula_animada.altura):
        pelicula_animada.montar(largura, altura)
    pelicula_animada.comecar()


def agendar_remontagem_pelicula(event=None):
    """Espera a janela parar de mudar de tamanho para remontar uma vez só."""
    if estado_pelicula["agendamento"] is not None:
        pelicula_contagem.after_cancel(estado_pelicula["agendamento"])
    estado_pelicula["agendamento"] = pelicula_contagem.after(120, remontar_pelicula)


pelicula_contagem.bind("<Configure>", agendar_remontagem_pelicula)


# =========================================================
# PÁGINA INICIAL — BUSCA EM FORMA DE INGRESSO
# =========================================================
def criar_campo_ingresso(container, texto_canhoto, placeholder, texto_botao=None):
    """
    Campo de texto com cara de ingresso:
    [ ADMIT ONE ┆ campo .................... ┆ BOTÃO ]
    Devolve (frame, entrada, botao_ou_None).
    """
    ingresso = ctk.CTkFrame(
        container,
        fg_color=COR_INGRESSO,
        border_width=2,
        border_color=COR_INGRESSO_BORDA,
        corner_radius=8
    )
    ingresso.grid_columnconfigure(2, weight=1)

    canhoto = ctk.CTkLabel(
        ingresso,
        text=texto_canhoto,
        font=(FONTE_TITULO, 15),
        text_color=COR_VERMELHO,
        width=96
    )
    canhoto.grid(row=0, column=0, padx=(12, 0), pady=8)

    picote = ctk.CTkLabel(ingresso, text="┆\n┆\n┆", font=(FONTE_INTERFACE, 9), text_color=COR_INGRESSO_BORDA)
    picote.grid(row=0, column=1, padx=6)

    entrada = ctk.CTkEntry(
        ingresso,
        height=42,
        placeholder_text=placeholder,
        font=(FONTE, 15),
        fg_color=COR_PAPEL,
        text_color=COR_TEXTO,
        placeholder_text_color=COR_TEXTO_SUAVE,
        border_width=0,
        corner_radius=4
    )
    entrada.grid(row=0, column=2, sticky="ew", pady=8)

    botao = None
    if texto_botao:
        botao = ctk.CTkButton(
            ingresso,
            text=texto_botao,
            width=118,
            height=42,
            font=(FONTE_TITULO, 17),
            fg_color=COR_VERMELHO,
            hover_color=COR_VERMELHO_HOVER,
            text_color=COR_TEXTO_CAPA,
            corner_radius=4
        )
        botao.grid(row=0, column=3, padx=(10, 10), pady=8)
    else:
        entrada.grid(padx=(0, 12))

    return ingresso, entrada, botao


area_busca, entrada_busca, botao_busca = criar_campo_ingresso(
    pagina_inicio,
    "ADMIT\nONE",
    "Ex.: Quero uma comédia sobre o mundo da moda...",
    "BUSCAR ✦"
)
area_busca.grid(row=3, column=0, sticky="ew", padx=42, pady=(18, 24))


def criar_botao_surpresa(container, altura, texto="🎲 SURPREENDA-ME"):
    """Botão dourado que pede ao CineAI um filme sorteado entre os que combinam com você."""
    return ctk.CTkButton(
        container,
        text=texto,
        width=150,
        height=altura,
        font=(FONTE_TITULO, 15),
        fg_color=COR_SURPRESA,
        hover_color=COR_SURPRESA_HOVER,
        text_color=COR_VINHO,
        corner_radius=4,
        command=lambda: processar(MENSAGEM_SURPRESA)
    )


botao_surpresa_inicio = criar_botao_surpresa(area_busca, 42)
botao_surpresa_inicio.grid(row=0, column=4, padx=(0, 10), pady=8)


# =========================================================
# PÁGINA INICIAL — CARDS DE RECOMENDAÇÃO
# =========================================================
titulo_recomendacoes = criar_titulo_manuscrito(pagina_inicio, "recortes para a sua próxima sessão", "estrela")
titulo_recomendacoes.grid(row=4, column=0, sticky="w", padx=42, pady=(0, 6))

area_cards = ctk.CTkFrame(pagina_inicio, fg_color="transparent")
area_cards.grid(row=5, column=0, sticky="ew", padx=34, pady=(0, 22))

for coluna in range(COLUNAS_CARDS):
    area_cards.grid_columnconfigure(coluna, weight=1, uniform="cards")

cards_recomendacao = []
filmes_exibidos = []


TAMANHO_POSTER_INICIO = (int(ALTURA_POSTER_INICIO * 0.69), ALTURA_POSTER_INICIO)


def criar_card_recomendacao(coluna):
    """Espaço de um recorte na Home: começa como "cole aqui" e recebe o filme recomendado."""
    escala = escala_da_tela(area_cards)

    def px(valor):
        return int(valor * escala)

    # Cartão de papel creme com borda; vazio, ele some e fica só o "cole aqui"
    card = tk.Frame(area_cards, bg=COR_FUNDO, cursor="hand2", highlightthickness=1,
                    highlightbackground=COR_FUNDO)
    card.grid(row=0, column=coluna, padx=px(6), pady=(px(2), px(8)), sticky="nsew")

    imagem_label = tk.Label(card, bg=COR_FUNDO, bd=0, cursor="hand2")
    imagem_label.pack(pady=(px(4), 0))

    largura_texto = px(TAMANHO_POSTER_INICIO[0] + 20)
    nome_label = tk.Label(
        card, text="", font=(FONTE, -px(14), "bold"), fg=COR_TEXTO, bg=COR_FUNDO,
        anchor="w", justify="left", wraplength=largura_texto, cursor="hand2"
    )
    nome_label.pack(fill="x", padx=px(14))

    detalhes_label = tk.Label(
        card, text="", font=(FONTE, -px(11), "italic"), fg=COR_TEXTO_SECUNDARIO, bg=COR_FUNDO,
        anchor="w", justify="left", wraplength=largura_texto, cursor="hand2"
    )
    detalhes_label.pack(fill="x", padx=px(14), pady=(0, px(10)))

    dados_card = {
        "numero": coluna + 1,
        "escala": escala,
        "cartao": card,
        "imagem": imagem_label,
        "nome": nome_label,
        "detalhes": detalhes_label,
        "filme": None,
    }

    def clicar(event=None):
        abrir_detalhes(dados_card["filme"])

    vincular_clique([card, imagem_label, nome_label, detalhes_label], clicar)

    cards_recomendacao.append(dados_card)
    mostrar_card_vazio(dados_card)


def pintar_cartao(dados_card, cor_papel, cor_borda):
    """Cartão cheio = papel creme com borda; vazio = some na página."""
    dados_card["cartao"].configure(bg=cor_papel, highlightbackground=cor_borda)
    for parte in ("imagem", "nome", "detalhes"):
        dados_card[parte].configure(bg=cor_papel)


def mostrar_card_vazio(dados_card):
    pintar_cartao(dados_card, COR_FUNDO, COR_FUNDO)
    imagem = imagem_do_recorte_vazio(
        dados_card["numero"], dados_card["escala"], COR_FUNDO, TAMANHO_POSTER_INICIO
    )
    dados_card["imagem"].configure(image=imagem)
    dados_card["imagem"].foto = imagem
    dados_card["nome"].configure(text="")
    dados_card["detalhes"].configure(text="")
    dados_card["filme"] = None


def mostrar_filme_no_card(dados_card, filme):
    pintar_cartao(dados_card, COR_CARD, COR_BORDA_PAPEL)
    imagem = imagem_do_recorte(filme, dados_card["escala"], COR_CARD, TAMANHO_POSTER_INICIO)
    dados_card["imagem"].configure(image=imagem)
    dados_card["imagem"].foto = imagem
    dados_card["nome"].configure(text=filme["nome"])
    dados_card["detalhes"].configure(text=texto_resumo_filme(filme))
    dados_card["filme"] = filme


def limpar_cards():
    for dados_card in cards_recomendacao:
        mostrar_card_vazio(dados_card)


def atualizar_card(indice, filme):
    if indice >= len(cards_recomendacao):
        return
    mostrar_filme_no_card(cards_recomendacao[indice], filme)


def adicionar_filme_aos_cards(filme):
    if filme is None:
        return

    # Compara pelo id: os dois "O Rei Leão" (1994 e 2019) são filmes diferentes.
    for filme_existente in filmes_exibidos:
        if usuario.chave_filme(filme_existente) == usuario.chave_filme(filme):
            return

    filmes_exibidos.append(filme)

    # Cards cheios: o mais antigo sai e os outros andam uma casa,
    # como uma tira de película (em vez de apagar os 4 de uma vez).
    if len(filmes_exibidos) > COLUNAS_CARDS:
        del filmes_exibidos[0]
        for indice, filme_do_card in enumerate(filmes_exibidos):
            atualizar_card(indice, filme_do_card)
        return

    atualizar_card(len(filmes_exibidos) - 1, filme)


# Os 4 espaços são criados no fim do arquivo (INICIALIZAÇÃO), depois que as
# funções de desenho dos recortes já existem.


# =========================================================
# PÁGINA INICIAL — CHAT
# =========================================================
titulo_chat = criar_titulo_manuscrito(pagina_inicio, "anotações com o CineAI", "caneta")
titulo_chat.grid(row=6, column=0, sticky="w", padx=42, pady=(4, 6))


# =========================================================
# CHAT COMO TROCA DE BILHETES
# =========================================================
# Cada mensagem é um papelzinho de verdade (widgets simples do Tk, leves):
#   CineAI -> ficha de papel branco à esquerda, com faixa vermelha, fita e "✦ CineAI"
#   você   -> anotação em caneta azul, letra de mão, à direita, assinada "— você"
COR_BILHETE = "#FFFDF7"
PROPORCAO_BILHETE_IA = 0.80     # largura máxima do bilhete do CineAI (da área do chat)
PROPORCAO_ANOTACAO_VOCE = 0.68  # largura máxima da sua anotação


class MuralDeBilhetes(ctk.CTkScrollableFrame):

    def __init__(self, container, altura=None):
        opcoes = {"height": altura} if altura is not None else {}
        super().__init__(
            container,
            fg_color=COR_PAPEL,
            corner_radius=4,
            border_width=1,
            border_color=COR_BORDA_PAPEL,
            scrollbar_button_color=COR_ROLAGEM,
            scrollbar_button_hover_color=COR_ROLAGEM_HOVER,
            **opcoes
        )
        self.grid_columnconfigure(0, weight=1)
        self.textos = []   # (label do texto, proporção da largura) para ajustar a quebra de linha
        self.largura_atual = 0
        self.bind("<Configure>", self._ajustar_quebra_de_linha, add="+")  # "+" não apaga a rolagem do CTk

    # ---------- medidas ----------
    def _px(self, valor):
        return int(valor * escala_da_tela(self))

    def _largura_maxima(self, proporcao):
        largura = self.largura_atual or self._px(760)
        return max(self._px(220), int(largura * proporcao))

    def _ajustar_quebra_de_linha(self, event=None):
        largura = self.winfo_width()
        if largura < 50 or largura == self.largura_atual:
            return
        self.largura_atual = largura
        for label, proporcao in self.textos:
            if label.winfo_exists():
                label.configure(wraplength=self._largura_maxima(proporcao) - self._px(36))

    # ---------- mensagens ----------
    def adicionar(self, autor, texto=""):
        """Cria o bilhete e devolve o label do texto (para a digitação ir completando)."""
        if autor == NOME_IA:
            label_texto = self._bilhete_do_cineai(texto)
            self.textos.append((label_texto, PROPORCAO_BILHETE_IA))
        else:
            label_texto = self._anotacao_sua(texto)
            self.textos.append((label_texto, PROPORCAO_ANOTACAO_VOCE))
        self.ir_para_o_fim()
        return label_texto

    def _bilhete_do_cineai(self, texto):
        px = self._px
        linha = tk.Frame(self, bg=COR_PAPEL)
        linha.pack(fill="x", padx=px(10), pady=(px(10), px(2)), anchor="w")

        bilhete = tk.Frame(linha, bg=COR_BILHETE, highlightbackground=COR_BORDA_PAPEL, highlightthickness=1)
        bilhete.pack(side="left", anchor="w")

        faixa = tk.Frame(bilhete, bg=COR_VERMELHO, width=px(4))
        faixa.pack(side="left", fill="y")

        conteudo = tk.Frame(bilhete, bg=COR_BILHETE)
        conteudo.pack(side="left", fill="both", padx=(px(12), px(14)), pady=(px(10), px(10)))

        tk.Label(
            conteudo, text="✦ CINEAI", font=(FONTE_TITULO, -px(12)),
            fg=COR_VERMELHO, bg=COR_BILHETE, anchor="w"
        ).pack(anchor="w")

        label_texto = tk.Label(
            conteudo, text=texto, font=(FONTE, -px(14)), fg=COR_TEXTO, bg=COR_BILHETE,
            justify="left", anchor="w",
            wraplength=self._largura_maxima(PROPORCAO_BILHETE_IA) - px(36)
        )
        label_texto.pack(anchor="w", pady=(px(2), 0))

        # Pedacinho de fita segurando o bilhete
        fita = tk.Frame(bilhete, bg=COR_FITA, width=px(44), height=px(9))
        fita.place(relx=0.82, y=0, anchor="n")
        return label_texto

    def _anotacao_sua(self, texto):
        px = self._px
        linha = tk.Frame(self, bg=COR_PAPEL)
        linha.pack(fill="x", padx=px(14), pady=(px(10), px(2)))

        anotacao = tk.Frame(linha, bg=COR_PAPEL)
        anotacao.pack(side="right", anchor="e")

        label_texto = tk.Label(
            anotacao, text=texto, font=(FONTE_MANUSCRITA, -px(18)), fg=COR_AZUL_CANETA,
            bg=COR_PAPEL, justify="right", anchor="e",
            wraplength=self._largura_maxima(PROPORCAO_ANOTACAO_VOCE) - px(36)
        )
        label_texto.pack(anchor="e")

        tk.Label(
            anotacao, text="— você", font=(FONTE_MANUSCRITA, -px(13)),
            fg=COR_TEXTO_SUAVE, bg=COR_PAPEL, anchor="e"
        ).pack(anchor="e")
        return label_texto

    # ---------- utilidades ----------
    def limpar(self):
        for widget in self.winfo_children():
            widget.destroy()
        self.textos.clear()

    def ir_para_o_fim(self):
        """Rola até o último bilhete (espera a área de rolagem crescer antes)."""
        canvas = getattr(self, "_parent_canvas", None)
        if canvas is None:
            return
        self.update_idletasks()
        canvas.yview_moveto(1.0)
        self.after(30, lambda: canvas.yview_moveto(1.0))

    def see(self, indice="end"):
        """Compatível com o jeito antigo (caixa.see("end"))."""
        self.ir_para_o_fim()


def criar_caixa_chat(container, altura=None):
    """Área do chat: um mural onde as mensagens viram bilhetes."""
    return MuralDeBilhetes(container, altura)


def criar_entrada_chat(container, altura):
    return ctk.CTkEntry(
        container,
        height=altura,
        placeholder_text="Escreva uma anotação para o CineAI...",
        font=(FONTE, 14),
        fg_color=COR_PAPEL,
        text_color=COR_TEXTO,
        placeholder_text_color=COR_TEXTO_SUAVE,
        border_color=COR_BORDA_PAPEL,
        border_width=1,
        corner_radius=4
    )


def criar_botao_enviar(container, altura):
    return ctk.CTkButton(
        container,
        text="ENVIAR ✦",
        width=118,
        height=altura,
        font=(FONTE_TITULO, 16),
        fg_color=COR_VERMELHO,
        hover_color=COR_VERMELHO_HOVER,
        text_color=COR_TEXTO_CAPA,
        corner_radius=4
    )


def criar_status(container):
    return ctk.CTkLabel(
        container,
        text="",
        font=(FONTE_MANUSCRITA, 15),
        text_color=COR_VERMELHO,
        anchor="w"
    )


chat = criar_caixa_chat(pagina_inicio, altura=230)
chat.grid(row=7, column=0, sticky="ew", padx=42)

area_mensagem = ctk.CTkFrame(pagina_inicio, fg_color="transparent")
area_mensagem.grid(row=8, column=0, sticky="ew", padx=42, pady=(12, 35))
area_mensagem.grid_columnconfigure(0, weight=1)

entrada_chat = criar_entrada_chat(area_mensagem, 45)
entrada_chat.grid(row=0, column=0, sticky="ew", padx=(0, 10))

botao_enviar = criar_botao_enviar(area_mensagem, 45)
botao_enviar.grid(row=0, column=1)

# Mostra a contagem 5-4-3-2-1 enquanto a IA responde.
status_inicio = criar_status(area_mensagem)
status_inicio.grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))


# ---------------- Escrita no chat ----------------
def adicionar_mensagem(autor, mensagem):
    """Cola o bilhete inteiro de uma vez nas duas telas de chat."""
    for mural in caixas_chat:
        mural.adicionar(autor, mensagem)


def digitar_mensagem(autor, mensagem, ao_terminar=None):
    """Cola um bilhete vazio e vai escrevendo nele, como se fosse digitado."""
    labels_do_texto = [mural.adicionar(autor, "") for mural in caixas_chat]

    def escrever_nos_bilhetes(trecho):
        for mural, label in zip(caixas_chat, labels_do_texto):
            label.configure(text=label.cget("text") + trecho)
            mural.ir_para_o_fim()

    # Respostas longas andam mais rápido para não passar da duração máxima.
    total_passos_desejado = DURACAO_MAXIMA_DIGITACAO_MS // INTERVALO_DIGITACAO_MS
    caracteres_por_passo = max(1, len(mensagem) // total_passos_desejado + 1)

    def digitar_proximo_trecho(posicao):
        if posicao >= len(mensagem):
            if ao_terminar is not None:
                ao_terminar()
            return

        trecho = mensagem[posicao:posicao + caracteres_por_passo]
        escrever_nos_bilhetes(trecho)

        janela.after(
            INTERVALO_DIGITACAO_MS,
            digitar_proximo_trecho,
            posicao + caracteres_por_passo
        )

    digitar_proximo_trecho(0)


# ---------------- Animação de "pensando" ----------------
id_animacao = None
quadro_atual = 0


def animar_status():
    global id_animacao, quadro_atual

    simbolo = QUADROS_ANIMACAO[quadro_atual]
    texto_status = f"{simbolo}  {TEXTO_ANIMACAO}"
    status_inicio.configure(text=texto_status)
    status_chat_completo.configure(text=texto_status)

    quadro_atual = (quadro_atual + 1) % len(QUADROS_ANIMACAO)
    id_animacao = janela.after(INTERVALO_ANIMACAO_MS, animar_status)


def iniciar_animacao():
    pelicula_animada.acelerar(True)  # o rolo corre mais rápido enquanto o CineAI pensa
    if id_animacao is None:
        animar_status()


def parar_animacao():
    global id_animacao, quadro_atual

    pelicula_animada.acelerar(False)
    if id_animacao is not None:
        janela.after_cancel(id_animacao)
        id_animacao = None

    quadro_atual = 0
    status_inicio.configure(text="")
    status_chat_completo.configure(text="")


# ---------------- Controle do processamento ----------------
def alterar_estado_processamento(processando):
    """Bloqueia envios enquanto a IA pensa e enquanto a resposta é digitada."""
    estado = "disabled" if processando else "normal"

    for entrada in [entrada_busca, entrada_chat, entrada_chat_completo]:
        entrada.configure(state=estado)

    for botao in [botao_busca, botao_enviar, botao_chat_completo,
                  botao_surpresa_inicio, botao_surpresa_chat]:
        botao.configure(state=estado)

    # Não dá para trocar de conversa no meio de uma resposta.
    for controle in [seletor_conversas, botao_nova_conversa, botao_apagar_conversa]:
        controle.configure(state=estado)

    if processando:
        iniciar_animacao()
    else:
        parar_animacao()
        atualizar_lista_conversas()


def finalizar_processamento(resposta=None, erro=None):
    """Roda na thread principal quando a IA termina: digita a resposta."""
    parar_animacao()  # o spinner some assim que a resposta começa a aparecer

    if erro is not None:
        digitar_mensagem(
            NOME_IA,
            f"Ocorreu um erro ao processar sua mensagem:\n{erro}",
            ao_terminar=lambda: alterar_estado_processamento(False)
        )
        return

    # Salva a resposta no histórico (com o filme, se for uma recomendação).
    chave_filme_recomendado = None
    if resposta["tipo"] == "recomendacao" and resposta["filme"] is not None:
        chave_filme_recomendado = usuario.chave_filme(resposta["filme"])

    conversas.registrar_mensagem(
        conversa_atual,
        conversas.AUTOR_CINEAI,
        resposta["texto"],
        chave_filme_recomendado
    )

    def depois_de_digitar():
        if resposta["tipo"] == "recomendacao" and resposta["filme"] is not None:
            adicionar_filme_aos_cards(resposta["filme"])
            adicionar_ao_historico(resposta["filme"])

        # A nota foi dada pelo chat ("Dou 5 estrelas para Shrek") ou você
        # disse "Já vi esse": atualiza selos e a página Meus filmes.
        if resposta.get("atualizou_usuario") or resposta["tipo"] == "usuario_atualizado":
            ao_mudar_listas()

        atualizar_painel_rag()  # o caminho desta resposta aparece no Painel do RAG

        # "Interestelar ou Matrix?": abre os dois lado a lado
        if resposta["tipo"] == "comparacao":
            abrir_comparacao(resposta["comparacao"])

        # "Como foi meu ano no cinema?": abre as páginas da retrospectiva
        if resposta["tipo"] == "retrospectiva":
            abrir_retrospectiva(resposta.get("ano"))

        alterar_estado_processamento(False)

    digitar_mensagem(NOME_IA, resposta["texto"], ao_terminar=depois_de_digitar)


def processar_em_segundo_plano(mensagem):
    """Executa somente o trabalho pesado fora da thread da interface."""
    try:
        resposta = filmes.processar_mensagem(mensagem)
        janela.after(0, lambda: finalizar_processamento(resposta=resposta))
    except Exception as erro:
        janela.after(0, lambda erro=erro: finalizar_processamento(erro=erro))


def processar(mensagem):
    mensagem = mensagem.strip()
    if mensagem == "":
        return

    adicionar_mensagem(NOME_USUARIO, mensagem)
    conversas.registrar_mensagem(conversa_atual, conversas.AUTOR_VOCE, mensagem)
    alterar_estado_processamento(True)

    thread = threading.Thread(
        target=processar_em_segundo_plano,
        args=(mensagem,),
        daemon=True
    )
    thread.start()


def enviar_da_entrada(entrada):
    mensagem = entrada.get()
    entrada.delete(0, "end")
    processar(mensagem)


def buscar(event=None):
    enviar_da_entrada(entrada_busca)


def enviar_chat(event=None):
    enviar_da_entrada(entrada_chat)


botao_busca.configure(command=buscar)
botao_enviar.configure(command=enviar_chat)
entrada_busca.bind("<Return>", buscar)
entrada_chat.bind("<Return>", enviar_chat)


# =========================================================
# PÁGINA CATÁLOGO — CABEÇALHO E PESQUISA
# =========================================================
cabecalho_catalogo = criar_cabecalho_pagina(
    pagina_catalogo,
    "Catálogo",
    "filmes e séries da estante do CineAI"
)

# Todos | Filmes | Séries — no canto direito do cabeçalho, ao lado do título
seletor_tipo_catalogo = ctk.CTkSegmentedButton(
    cabecalho_catalogo,
    values=list(filmes.TIPOS_DO_CATALOGO),
    height=34,
    font=(FONTE_TITULO, 15),
    fg_color=COR_PAPEL_ESCURO,
    selected_color=COR_VERMELHO,
    selected_hover_color=COR_VERMELHO_HOVER,
    unselected_color=COR_PAPEL_ESCURO,
    unselected_hover_color=COR_BOTAO_NEUTRO_HOVER,
    text_color=COR_TEXTO_CAPA,
    corner_radius=4,
    command=lambda valor: (pintar_seletor_tipo(), atualizar_catalogo())
)
seletor_tipo_catalogo.set(filmes.TODOS)
seletor_tipo_catalogo.place(relx=1.0, y=34, anchor="ne")


def pintar_seletor_tipo():
    """Texto creme na opção escolhida e vinho nas outras (o CTk usa uma cor só)."""
    escolhido = seletor_tipo_catalogo.get()
    for valor, botao in getattr(seletor_tipo_catalogo, "_buttons_dict", {}).items():
        botao.configure(text_color=COR_TEXTO_CAPA if valor == escolhido else COR_VINHO)


pintar_seletor_tipo()

area_pesquisa_catalogo, entrada_catalogo, _ = criar_campo_ingresso(
    pagina_catalogo,
    "BUSCAR",
    "Pesquisar por filme, gênero, ano, diretor ou ator..."
)
area_pesquisa_catalogo.grid(row=1, column=0, sticky="ew", padx=42, pady=(4, 12))

def criar_seta_pagina(texto):
    return ctk.CTkButton(
        area_pesquisa_catalogo,
        text=texto,
        width=38,
        height=34,
        font=(FONTE_SIMBOLOS, 15, "bold"),
        fg_color=COR_VERMELHO,
        hover_color=COR_VERMELHO_HOVER,
        text_color=COR_TEXTO_CAPA,
        text_color_disabled=COR_INGRESSO_BORDA,
        corner_radius=4
    )


botao_pagina_anterior = criar_seta_pagina("◀")
botao_pagina_anterior.grid(row=0, column=3, padx=(10, 0))

# "21–40 de 500": quais filmes desta página, e quantos existem no total
contador_catalogo = ctk.CTkLabel(
    area_pesquisa_catalogo,
    text="",
    width=150,
    font=(FONTE_MANUSCRITA, 15),
    text_color=COR_VINHO
)
contador_catalogo.grid(row=0, column=4, padx=4)

botao_proxima_pagina = criar_seta_pagina("▶")
botao_proxima_pagina.grid(row=0, column=5, padx=(0, 14))


# ---------------- Busca avançada: filtros clicáveis ----------------
# Faixa de papel kraft com os filtros. Todos funcionam juntos com a pesquisa:
# "nolan" + Gênero "Ação" + Ordem "Crítica (Rotten)", por exemplo.
barra_filtros = ctk.CTkFrame(
    pagina_catalogo,
    fg_color=COR_PAPEL_ESCURO,
    border_width=1,
    border_color=COR_BORDA_PAPEL,
    corner_radius=6
)
barra_filtros.grid(row=2, column=0, sticky="ew", padx=42, pady=(0, 12))


def criar_filtro(coluna, titulo, opcoes, largura=110):
    """Rótulo em letreiro + menu de opções, um embaixo do outro."""
    caixa = ctk.CTkFrame(barra_filtros, fg_color="transparent")
    caixa.grid(row=0, column=coluna, padx=(14 if coluna == 0 else 6, 6), pady=(8, 10), sticky="ew")
    # Os 4 filtros dividem o espaço que sobrar: nada fica cortado em telas menores.
    barra_filtros.grid_columnconfigure(coluna, weight=1, uniform="filtros")

    ctk.CTkLabel(
        caixa, text=titulo, font=(FONTE_TITULO, 13), text_color=COR_VERMELHO, height=18, anchor="w"
    ).pack(anchor="w")

    menu_opcoes = ctk.CTkOptionMenu(
        caixa,
        values=opcoes,
        width=largura,
        height=30,
        font=(FONTE, 12),
        dropdown_font=(FONTE, 12),
        fg_color=COR_PAPEL,
        button_color=COR_VERMELHO,
        button_hover_color=COR_VERMELHO_HOVER,
        text_color=COR_TEXTO,
        dropdown_fg_color=COR_PAPEL,
        dropdown_hover_color=COR_PAPEL_ESCURO,
        dropdown_text_color=COR_TEXTO,
        corner_radius=4,
        dynamic_resizing=False,
        command=lambda valor: atualizar_catalogo()
    )
    menu_opcoes.pack(fill="x")
    return menu_opcoes


filtro_genero = criar_filtro(0, "GÊNERO", [filmes.TODOS] + filmes.generos_do_catalogo())
filtro_decada = criar_filtro(1, "DÉCADA", [filmes.TODOS] + filmes.decadas_do_catalogo())
filtro_nota = criar_filtro(2, "NOTA", list(filmes.NOTAS_MINIMAS_DO_CATALOGO))
filtro_ordem = criar_filtro(3, "ORDEM", filmes.ORDENS_DO_CATALOGO)

STREAMING_TODOS = filmes.TODOS
STREAMING_MEUS = "✓ Que eu assino"
filtro_streaming = criar_filtro(4, "STREAMING", [STREAMING_TODOS, STREAMING_MEUS] + streamings.NOMES_DOS_STREAMINGS)


def streaming_escolhido_no_catalogo():
    escolha = filtro_streaming.get()
    if escolha == STREAMING_TODOS:
        return None
    if escolha == STREAMING_MEUS:
        return streamings.MEUS_STREAMINGS
    return escolha


def abrir_meus_streamings(event=None):
    """Bilhetinho com caixinhas: quais streamings você assina."""
    editor = ctk.CTkToplevel(janela)
    editor.title("Meus streamings")
    editor.resizable(False, False)
    editor.configure(fg_color=COR_PAPEL)
    editor.transient(janela)
    janela.update_idletasks()
    editor.geometry(f"+{janela.winfo_rootx() + 420}+{janela.winfo_rooty() + 180}")
    editor.after(50, editor.grab_set)

    ctk.CTkLabel(
        editor, text="quais streamings você assina?", font=(FONTE_MANUSCRITA, 22, "bold"),
        text_color=COR_TITULO_MANUSCRITO
    ).pack(padx=24, pady=(18, 2))
    ctk.CTkLabel(
        editor, text='eles ganham ✓ nos selinhos e valem no filtro "os que eu assino"',
        font=(FONTE_MANUSCRITA, 14), text_color=COR_TEXTO_SUAVE
    ).pack(padx=24, pady=(0, 10))

    grade = ctk.CTkFrame(editor, fg_color="transparent")
    grade.pack(padx=24)
    meus = set(usuario.obter_meus_streamings())
    caixas = {}
    for posicao, nome in enumerate(streamings.NOMES_DOS_STREAMINGS):
        variavel = ctk.BooleanVar(value=nome in meus)
        ctk.CTkCheckBox(
            grade, text=nome, variable=variavel, font=(FONTE_INTERFACE, 13, "bold"),
            text_color=COR_TEXTO, fg_color=streamings.cor_do_streaming(nome),
            hover_color=COR_VERMELHO_HOVER, border_color=COR_VINHO, corner_radius=3
        ).grid(row=posicao // 2, column=posicao % 2, sticky="w", padx=10, pady=5)
        caixas[nome] = variavel

    def salvar():
        usuario.definir_meus_streamings([nome for nome, variavel in caixas.items() if variavel.get()])
        editor.destroy()
        atualizar_catalogo(manter_pagina=True)

    ctk.CTkButton(
        editor, text="salvar ✓", width=130, height=34, corner_radius=4, fg_color=COR_VERMELHO,
        hover_color=COR_VERMELHO_HOVER, text_color=COR_TEXTO_CAPA, font=(FONTE_MANUSCRITA, 16, "bold"),
        command=salvar
    ).pack(pady=(14, 18))


# Link "✎ quais eu assino" colado no título do filtro STREAMING
link_meus_streamings = ctk.CTkLabel(
    filtro_streaming.master, text="✎ quais eu assino", font=(FONTE_MANUSCRITA, 13),
    text_color=COR_AZUL_CANETA, height=18, cursor="hand2"
)
link_meus_streamings.place(relx=1.0, y=0, anchor="ne")
link_meus_streamings.bind("<Button-1>", abrir_meus_streamings)

esconder_assistidos_var = ctk.BooleanVar(value=False)
caixa_esconder = ctk.CTkCheckBox(
    barra_filtros,
    text="esconder vistos",
    variable=esconder_assistidos_var,
    font=(FONTE_MANUSCRITA, 14),
    text_color=COR_VINHO,
    fg_color=COR_VERMELHO,
    hover_color=COR_VERMELHO_HOVER,
    border_color=COR_VINHO,
    checkmark_color=COR_TEXTO_CAPA,
    corner_radius=3,
    command=lambda: atualizar_catalogo()
)
caixa_esconder.grid(row=0, column=5, padx=(10, 6), pady=(26, 10), sticky="w")


def limpar_filtros():
    entrada_catalogo.delete(0, "end")
    filtro_genero.set(filmes.TODOS)
    filtro_decada.set(filmes.TODOS)
    filtro_nota.set(list(filmes.NOTAS_MINIMAS_DO_CATALOGO)[0])
    filtro_ordem.set(filmes.ORDENS_DO_CATALOGO[0])
    filtro_streaming.set(STREAMING_TODOS)
    esconder_assistidos_var.set(False)
    seletor_tipo_catalogo.set(filmes.TODOS)
    pintar_seletor_tipo()
    atualizar_catalogo()


botao_limpar_filtros = ctk.CTkButton(
    barra_filtros,
    text="✕ LIMPAR",
    width=90,
    height=30,
    font=(FONTE_INTERFACE, 11, "bold"),
    fg_color=COR_VINHO,
    hover_color=COR_VERMELHO,
    text_color=COR_TEXTO_CAPA,
    corner_radius=4,
    command=limpar_filtros
)
botao_limpar_filtros.grid(row=0, column=6, padx=(6, 14), pady=(26, 10), sticky="e")


# =========================================================
# GRADE DE FILMES (usada pelo Catálogo e pelas Recomendações)
# =========================================================
def criar_area_grade(pagina, linha):
    """Cria uma área com rolagem e 4 colunas para exibir cards de filmes."""
    area_grade = ctk.CTkScrollableFrame(
        pagina,
        corner_radius=0,
        fg_color=COR_FUNDO,
        scrollbar_button_color=COR_ROLAGEM,
        scrollbar_button_hover_color=COR_ROLAGEM_HOVER
    )
    area_grade.grid(
        row=linha,
        column=0,
        sticky="nsew",
        padx=(32, 20),
        pady=(0, 16)
    )

    for coluna in range(COLUNAS_CARDS):
        area_grade.grid_columnconfigure(coluna, weight=1, uniform="grade")

    return area_grade


# Os cards das grades usam widgets simples do Tk (tk.Frame / tk.Label) em vez
# dos do customtkinter: cada widget do customtkinter é um "canvas" redesenhado
# a cada movimento, e com dezenas de cards a rolagem deixava rastros na tela.
LARGURA_POSTER_CARD, ALTURA_POSTER_CARD = 185, 270


def escala_da_tela(widget):
    """Zoom do Windows (125%, 150%...) que o customtkinter aplica."""
    try:
        return ctk.ScalingTracker.get_widget_scaling(widget)
    except Exception:
        return 1.0


# =========================================================
# RECORTES: cada card é uma polaroide desenhada como imagem
# =========================================================
# O Tkinter não gira widgets, mas gira imagens. Então o card inteiro
# (papel, pôster, fita, anotação à mão e carimbo WATCHED) é desenhado com o
# Pillow e levemente inclinado. Cada filme sempre ganha a MESMA inclinação e
# a mesma fita (o sorteio usa o id dele), então nada "pula" ao recarregar.
INCLINACAO_MAXIMA_RECORTE = 2.2       # graus
BORDA_POLAROIDE = 9                   # papel branco em volta do pôster
BASE_POLAROIDE = 40                   # faixa de baixo, onde fica a anotação
COR_PAPEL_POLAROIDE = (255, 253, 247, 255)
COR_TINTA_AZUL = (47, 79, 160, 255)
COR_TINTA_VERMELHA = (179, 38, 30, 255)   # coração e "favorito"
COR_TINTA_SUAVE = (143, 122, 102, 255)
COR_CARIMBO = (179, 38, 30, 200)
CORES_FITA = [
    (228, 207, 156, 215),   # bege
    (206, 182, 140, 215),   # kraft
    (241, 230, 204, 225),   # creme
]
MESES_EM_INGLES = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
                   "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
FONTES_MANUSCRITAS_PIL = [
    "Inkfree.ttf", "inkfree.ttf", "segoepr.ttf",
    "/root/.fonts/Caveat[wght].ttf", "DejaVuSans.ttf",
]
FONTES_CARIMBO_PIL = [
    "impact.ttf", "Impact.ttf", "/root/.fonts/Anton-Regular.ttf", "DejaVuSans-Bold.ttf",
]

cache_fontes_pil = {}
cache_recortes = {}
recortes_em_tela = []  # (label, filme, escala, cor_fundo) para redesenhar ao mudar notas/favoritos


def fonte_pil(candidatas, tamanho):
    chave = (tuple(candidatas), tamanho)
    if chave not in cache_fontes_pil:
        fonte_escolhida = None
        for nome_fonte in candidatas:
            try:
                fonte_escolhida = ImageFont.truetype(nome_fonte, tamanho)
                break
            except OSError:
                continue
        if fonte_escolhida is None:
            try:
                fonte_escolhida = ImageFont.load_default(size=tamanho)
            except TypeError:
                fonte_escolhida = ImageFont.load_default()
        cache_fontes_pil[chave] = fonte_escolhida
    return cache_fontes_pil[chave]


def data_que_assistiu(filme):
    """'2026-10-03' (guardado pelo usuario.py) -> '03 OCT 2026'."""
    registro = usuario.dados_usuario.get("assistidos", {}).get(usuario.chave_filme(filme)) or {}
    data_texto = registro.get("adicionado_em") or ""
    try:
        ano, mes, dia = (int(parte) for parte in data_texto.split("-"))
        return f"{dia:02d} {MESES_EM_INGLES[mes - 1]} {ano}"
    except (ValueError, IndexError):
        return ""


def desenhar_coracao(lapis, x, y, tamanho, cor):
    """Coraçãozinho feito à mão (duas bolinhas + um triângulo)."""
    raio = tamanho // 4
    lapis.ellipse([x, y, x + 2 * raio, y + 2 * raio], fill=cor)
    lapis.ellipse([x + 2 * raio, y, x + 4 * raio, y + 2 * raio], fill=cor)
    lapis.polygon([(x, y + raio + 1), (x + 4 * raio, y + raio + 1), (x + 2 * raio, y + tamanho)], fill=cor)


def desenhar_carimbo_watched(largura, escala, data_texto):
    """Carimbo vermelho "WATCHED" com a data, já inclinado."""
    def px(valor):
        return max(1, int(valor * escala))

    fonte_grande = fonte_pil(FONTES_CARIMBO_PIL, px(17))
    fonte_data = fonte_pil(FONTES_CARIMBO_PIL, px(9))
    altura = px(40) if data_texto else px(28)
    carimbo = Image.new("RGBA", (largura, altura), (0, 0, 0, 0))
    lapis = ImageDraw.Draw(carimbo)
    lapis.rounded_rectangle(
        [px(2), px(2), largura - px(2), altura - px(2)],
        radius=px(5), outline=COR_CARIMBO, width=px(2)
    )
    lapis.text((largura // 2, px(15)), "WATCHED", font=fonte_grande, fill=COR_CARIMBO, anchor="mm")
    if data_texto:
        lapis.text((largura // 2, px(30)), data_texto, font=fonte_data, fill=COR_CARIMBO, anchor="mm")
    return carimbo.rotate(-13, resample=Image.BICUBIC, expand=True)


# ---------- adesivo de coração (favoritos) ----------
COR_ADESIVO_CORACAO = (190, 36, 30, 255)
COR_BORDA_ADESIVO = (255, 253, 247, 255)
TAMANHO_ADESIVO = {"cartao": 46, "diario": 46, "compacto": 22}
INCLINACAO_ADESIVO = 14            # graus
QUADROS_CARIMBO_ADESIVO = [1.45, 1.22, 0.92, 1.04, 1.0]   # "cai" e assenta
INTERVALO_CARIMBO_MS = 55


def desenhar_adesivo_coracao(tamanho):
    """
    Adesivo de coração: borda branca de papel recortado, coração vermelho,
    um brilho no canto e uma sombrinha. Desenhado 4× maior e reduzido (bordas lisas).
    """
    lupa = 4
    grande = tamanho * lupa
    adesivo = Image.new("RGBA", (grande, grande), (0, 0, 0, 0))
    lapis = ImageDraw.Draw(adesivo)

    margem_branca = int(grande * 0.10)
    sombra = (60, 40, 25, 70)
    desenhar_coracao(lapis, margem_branca // 2 + lupa * 2, margem_branca // 2 + lupa * 3,
                     grande - margem_branca, sombra)
    desenhar_coracao(lapis, margem_branca // 2, margem_branca // 2, grande - margem_branca, COR_BORDA_ADESIVO)
    desenhar_coracao(lapis, margem_branca, margem_branca, grande - 2 * margem_branca, COR_ADESIVO_CORACAO)
    brilho = int(grande * 0.13)
    lapis.ellipse(
        [int(grande * 0.24), int(grande * 0.20), int(grande * 0.24) + brilho, int(grande * 0.20) + int(brilho * 0.7)],
        fill=(255, 255, 255, 150)
    )
    adesivo = adesivo.resize((tamanho, tamanho), Image.LANCZOS)
    return adesivo.rotate(-INCLINACAO_ADESIVO, resample=Image.BICUBIC, expand=True)


def anotacao_do_recorte(filme):
    """O que vai escrito à mão embaixo da foto: nota, favorito ou o ano."""
    nota = usuario.obter_nota(filme)
    favorito = usuario.eh_favorito(filme)
    if nota is not None:
        return f"nota {nota}/{usuario.NOTA_MAXIMA}", COR_TINTA_AZUL, False
    if favorito:
        return "favorito", COR_TINTA_VERMELHA, False   # o coração agora é o adesivo no canto
    if usuario.quer_assistir(filme):
        return "pra ver depois", COR_TINTA_AZUL, False
    return "", COR_TINTA_SUAVE, False  # sem nota nem coração: polaroide limpa (o ano já vai embaixo)


def desenhar_recorte(filme, escala, cor_fundo_pagina, tamanho_poster=None, modo="cartao",
                     escala_adesivo=1.0, escala_carimbo=1.0):
    """
    A polaroide inteira, inclinada, já "colada" na cor da página.
    modo "cartao":   anotação embaixo = nota / favorito (Catálogo, Home...)
    modo "diario":   anotação embaixo = data em que viu ♥, ou "movie night ✦" (tela de detalhes)
    modo "compacto": mini polaroide, sem anotação nem carimbo ("Se você gostou...")
    """
    def px(valor):
        return max(1, int(valor * escala))

    compacto = modo == "compacto"
    sorteio = random.Random(usuario.chave_filme(filme))
    largura_base, altura_base = tamanho_poster or (LARGURA_POSTER_CARD, ALTURA_POSTER_CARD)
    largura_poster, altura_poster = px(largura_base), px(altura_base)
    borda = px(5) if compacto else px(BORDA_POLAROIDE)
    base = px(14) if compacto else px(BASE_POLAROIDE)
    largura, altura = largura_poster + 2 * borda, altura_poster + borda + base

    # ---------- papel + pôster ----------
    papel = Image.new("RGBA", (largura, altura), COR_PAPEL_POLAROIDE)
    lapis = ImageDraw.Draw(papel)

    caminho_poster = obter_caminho_poster(filme)
    poster = None
    if caminho_poster.exists():
        try:
            with Image.open(caminho_poster) as arquivo_imagem:
                poster = arquivo_imagem.convert("RGBA").resize((largura_poster, altura_poster), Image.LANCZOS)
        except Exception:
            poster = None

    if poster is not None:
        papel.paste(poster, (borda, borda))
    else:
        lapis.rectangle([borda, borda, borda + largura_poster, borda + altura_poster], fill=cor_rgb(COR_POSTER))
        lapis.text(
            (largura // 2, borda + altura_poster // 2), "SEM PÔSTER",
            font=fonte_pil(FONTES_CARIMBO_PIL, px(16)), fill=cor_rgb(COR_DOURADO_CLARO), anchor="mm"
        )

    # ---------- carimbo WATCHED ----------
    if usuario.foi_assistido(filme) and not compacto:
        carimbo = desenhar_carimbo_watched(
            int(px(108) * escala_carimbo), escala * escala_carimbo, data_que_assistiu(filme)
        )
        papel.alpha_composite(
            carimbo,
            (max(0, borda + largura_poster - carimbo.width + px(6)),
             max(0, borda + altura_poster - carimbo.height - px(6)))
        )

    # ---------- anotação à mão ----------
    if not compacto:
        if modo == "diario":
            data_vista = data_que_assistiu(filme)
            texto = data_vista or "movie night"
            cor_tinta = COR_TINTA_AZUL
            com_coracao = False   # o coração agora é o adesivo no canto
            com_estrela = not data_vista
        else:
            texto, cor_tinta, com_coracao = anotacao_do_recorte(filme)
            com_estrela = False
        texto = texto or " "
        fonte_mao = fonte_pil(FONTES_MANUSCRITAS_PIL, px(17))
        meio_base = borda + altura_poster + base // 2
        largura_texto = lapis.textlength(texto, font=fonte_mao)
        x_texto = (largura - largura_texto) / 2
        if modo == "cartao" and com_coracao and texto != "favorito":
            x_texto += px(9)
        if com_coracao:
            tamanho_coracao = px(12)
            if modo == "diario":   # no diário o coração vem DEPOIS da data: "03 OCT 2026 ♥"
                x_coracao = int(x_texto + largura_texto + px(6))
            else:
                x_coracao = int(x_texto - tamanho_coracao - px(5))
            desenhar_coracao(lapis, x_coracao, meio_base - tamanho_coracao // 2, tamanho_coracao, COR_TINTA_VERMELHA)
        if com_estrela:
            desenhar_estrelinha(lapis, x_texto + largura_texto + px(10), meio_base, px(6), cor_rgb(COR_DOURADO) + (255,))
        lapis.text((x_texto, meio_base), texto, font=fonte_mao, fill=cor_tinta, anchor="lm")

    # ---------- sombra + inclinação ----------
    folga = px(6) if compacto else px(10)
    com_sombra = Image.new("RGBA", (largura + 2 * folga, altura + 2 * folga), (0, 0, 0, 0))
    sombra = Image.new("RGBA", (largura, altura), (60, 40, 25, 70))
    com_sombra.alpha_composite(sombra, (folga + px(3), folga + px(4)))
    com_sombra = com_sombra.filter(ImageFilter.GaussianBlur(px(3)))
    com_sombra.alpha_composite(papel, (folga, folga))

    # ---------- adesivo de coração no canto (favoritos) ----------
    if usuario.eh_favorito(filme):
        tamanho_adesivo = max(8, int(px(TAMANHO_ADESIVO[modo]) * escala_adesivo))
        adesivo = desenhar_adesivo_coracao(tamanho_adesivo)
        centro_x = folga + largura - px(TAMANHO_ADESIVO[modo] * 0.38)
        centro_y = folga + px(TAMANHO_ADESIVO[modo] * 0.38)
        com_sombra.alpha_composite(
            adesivo,
            (max(0, int(centro_x - adesivo.width / 2)), max(0, int(centro_y - adesivo.height / 2)))
        )

    inclinacao = sorteio.uniform(-INCLINACAO_MAXIMA_RECORTE, INCLINACAO_MAXIMA_RECORTE)
    recorte = com_sombra.rotate(inclinacao, resample=Image.BICUBIC, expand=True)

    # ---------- fita adesiva (meio do topo ou dois cantos) ----------
    cor_fita = sorteio.choice(CORES_FITA)
    largura_fita, altura_fita = int(largura * 0.36), (px(9) if compacto else px(17))

    def colar_fita(centro_x, centro_y, angulo):
        fita = Image.new("RGBA", (largura_fita, altura_fita), cor_fita)
        fita = fita.rotate(angulo, resample=Image.BICUBIC, expand=True)
        recorte.alpha_composite(fita, (int(centro_x - fita.width / 2), int(centro_y - fita.height / 2)))

    # Favorito: fita sempre no meio do topo, para não cobrir o adesivo de coração.
    fita_no_meio = sorteio.random() < 0.65
    if fita_no_meio or usuario.eh_favorito(filme):
        colar_fita(recorte.width / 2, folga + px(3), sorteio.uniform(-6, 6))
    else:
        colar_fita(folga + px(14), folga + px(10), 38)
        colar_fita(recorte.width - folga - px(14), folga + px(10), -38)

    # ---------- "cola" na página (o Tk não tem transparência) ----------
    pagina = Image.new("RGBA", recorte.size, cor_rgb(cor_fundo_pagina) + (255,))
    pagina.alpha_composite(recorte)
    return pagina.convert("RGB")


def imagem_do_recorte(filme, escala, cor_fundo_pagina, tamanho_poster=None, modo="cartao"):
    """PhotoImage do recorte, com cache (refaz só se nota/favorito/assistido mudar)."""
    chave = (
        usuario.chave_filme(filme), round(escala, 2), cor_fundo_pagina, tamanho_poster, modo,
        usuario.eh_favorito(filme), usuario.obter_nota(filme), usuario.foi_assistido(filme),
        data_que_assistiu(filme), usuario.quer_assistir(filme),
    )
    if chave not in cache_recortes:
        cache_recortes[chave] = ImageTk.PhotoImage(
            desenhar_recorte(filme, escala, cor_fundo_pagina, tamanho_poster, modo)
        )
    return cache_recortes[chave]


def desenhar_recorte_vazio(numero, escala, cor_fundo_pagina, tamanho_poster):
    """
    Espaço ainda sem filme: um contorno tracejado na página, com dois pedaços
    de fita esperando e "cole aqui" escrito à mão.
    """
    def px(valor):
        return max(1, int(valor * escala))

    sorteio = random.Random(f"vazio{numero}")
    largura = px(tamanho_poster[0]) + 2 * px(BORDA_POLAROIDE)
    altura = px(tamanho_poster[1]) + px(BORDA_POLAROIDE) + px(BASE_POLAROIDE)
    folga = px(10)

    espaco = Image.new("RGBA", (largura + 2 * folga, altura + 2 * folga), (0, 0, 0, 0))
    lapis = ImageDraw.Draw(espaco)
    cor_contorno = cor_rgb(COR_TEXTO_SUAVE) + (170,)

    # Contorno tracejado (tracinhos desenhados um a um)
    tamanho_traco, vao = px(9), px(6)
    x0, y0, x1, y1 = folga, folga, folga + largura, folga + altura
    for inicio_x in range(x0, x1, tamanho_traco + vao):
        fim_x = min(inicio_x + tamanho_traco, x1)
        lapis.line([(inicio_x, y0), (fim_x, y0)], fill=cor_contorno, width=px(2))
        lapis.line([(inicio_x, y1), (fim_x, y1)], fill=cor_contorno, width=px(2))
    for inicio_y in range(y0, y1, tamanho_traco + vao):
        fim_y = min(inicio_y + tamanho_traco, y1)
        lapis.line([(x0, inicio_y), (x0, fim_y)], fill=cor_contorno, width=px(2))
        lapis.line([(x1, inicio_y), (x1, fim_y)], fill=cor_contorno, width=px(2))

    # "cole aqui" à mão + número do recorte
    fonte_mao = fonte_pil(FONTES_MANUSCRITAS_PIL, px(22))
    fonte_numero = fonte_pil(FONTES_MANUSCRITAS_PIL, px(15))
    centro_x, centro_y = espaco.width // 2, espaco.height // 2
    lapis.text((centro_x, centro_y - px(10)), "cole aqui", font=fonte_mao, fill=cor_contorno, anchor="mm")
    lapis.text((centro_x, centro_y + px(16)), f"recorte nº {numero:02d}", font=fonte_numero,
               fill=cor_contorno, anchor="mm")
    desenhar_estrelinha(lapis, centro_x, centro_y + px(42), px(6), cor_rgb(COR_DOURADO) + (200,))

    espaco = espaco.rotate(sorteio.uniform(-1.5, 1.5), resample=Image.BICUBIC, expand=True)

    # Dois pedaços de fita esperando o filme
    cor_fita = sorteio.choice(CORES_FITA)
    for centro_fita_x, angulo in ((folga + px(20), 35), (espaco.width - folga - px(20), -35)):
        fita = Image.new("RGBA", (int(largura * 0.3), px(15)), cor_fita[:3] + (150,))
        fita = fita.rotate(angulo, resample=Image.BICUBIC, expand=True)
        espaco.alpha_composite(fita, (int(centro_fita_x - fita.width / 2), int(folga + px(8) - fita.height / 2)))

    pagina = Image.new("RGBA", espaco.size, cor_rgb(cor_fundo_pagina) + (255,))
    pagina.alpha_composite(espaco)
    return pagina.convert("RGB")


def imagem_do_recorte_vazio(numero, escala, cor_fundo_pagina, tamanho_poster):
    chave = ("vazio", numero, round(escala, 2), cor_fundo_pagina, tamanho_poster)
    if chave not in cache_recortes:
        cache_recortes[chave] = ImageTk.PhotoImage(
            desenhar_recorte_vazio(numero, escala, cor_fundo_pagina, tamanho_poster)
        )
    return cache_recortes[chave]


def atualizar_recortes_em_tela():
    """Depois de dar nota/favoritar: redesenha só os recortes que ainda estão na tela."""
    vivos = []
    for label, filme, escala, cor_fundo in recortes_em_tela:
        if label.winfo_exists():
            imagem = imagem_do_recorte(filme, escala, cor_fundo)
            label.configure(image=imagem)
            label.imagem = imagem
            vivos.append((label, filme, escala, cor_fundo))
    recortes_em_tela[:] = vivos


def criar_card_filme(container, filme, linha, coluna, widgets, imagens):
    """Card de filme: polaroide inclinada colada na página + título escrito embaixo."""
    escala = escala_da_tela(container)
    cor_pagina = COR_CARD  # a polaroide fica colada DENTRO do cartão de papel

    def px(valor):
        return int(valor * escala)

    # Cartão de papel creme com borda (as informações ficam dentro dele)
    card = tk.Frame(
        container, bg=cor_pagina, cursor="hand2",
        highlightbackground=COR_BORDA_PAPEL, highlightthickness=1
    )
    card.grid(row=linha, column=coluna, sticky="nsew", padx=px(8), pady=px(9))

    imagem = imagem_do_recorte(filme, escala, cor_pagina)
    imagens.append(imagem)  # mantém a referência
    recorte_label = tk.Label(card, image=imagem, bg=cor_pagina, bd=0, cursor="hand2")
    recorte_label.imagem = imagem
    recorte_label.pack(pady=(px(4), 0))
    recortes_em_tela.append((recorte_label, filme, escala, cor_pagina))

    # ---------- etiquetas e textos (fora da foto, como anotação na página) ----------
    largura_texto = px(LARGURA_POSTER_CARD + 10)

    linha_etiquetas = tk.Frame(card, bg=cor_pagina, cursor="hand2")
    linha_etiquetas.pack(anchor="w", padx=px(14), pady=(px(2), px(2)))

    etiqueta_ano = tk.Label(
        linha_etiquetas,
        text=f' {filmes.periodo_de_exibicao(filme)} ',
        font=(FONTE_INTERFACE, -px(10), "bold"),
        fg=COR_TEXTO_CAPA,
        bg=COR_VERMELHO,
        cursor="hand2"
    )
    etiqueta_ano.pack(side="left")

    etiquetas_clicaveis = [linha_etiquetas, etiqueta_ano]
    if filmes.eh_serie(filme):
        etiqueta_serie = tk.Label(
            linha_etiquetas,
            text=" SÉRIE ",
            font=(FONTE_INTERFACE, -px(10), "bold"),
            fg=COR_TEXTO_CAPA,
            bg=COR_SERIE,
            cursor="hand2"
        )
        etiqueta_serie.pack(side="left", padx=(px(4), 0))
        etiquetas_clicaveis.append(etiqueta_serie)

    nome_label = tk.Label(
        card,
        text=filme["nome"],
        font=(FONTE, -px(14), "bold"),
        fg=COR_TEXTO,
        bg=cor_pagina,
        anchor="w",
        justify="left",
        wraplength=largura_texto,
        cursor="hand2"
    )
    nome_label.pack(fill="x", padx=px(14))

    informacoes_label = tk.Label(
        card,
        text=texto_resumo_filme(filme),
        font=(FONTE, -px(11), "italic"),
        fg=COR_TEXTO_SECUNDARIO,
        bg=cor_pagina,
        anchor="w",
        justify="left",
        wraplength=largura_texto,
        cursor="hand2"
    )
    informacoes_label.pack(fill="x", padx=px(14), pady=(0, px(12)))

    def clicar(event=None):
        abrir_detalhes(filme)

    vincular_clique(
        [card, recorte_label, nome_label, informacoes_label] + etiquetas_clicaveis,
        clicar
    )

    widgets.append(card)


TAMANHO_ESPACO_VAZIO = (110, 160)


def mostrar_mensagem_vazia(container, texto, widgets):
    """Página quase vazia: um espaço tracejado "cole aqui" e um recado escrito à mão."""
    escala = escala_da_tela(container)
    cor_pagina = COR_FUNDO

    area_vazia = tk.Frame(container, bg=cor_pagina)
    area_vazia.grid(row=0, column=0, columnspan=COLUNAS_CARDS, pady=int(50 * escala))

    imagem = imagem_do_recorte_vazio(1, escala, cor_pagina, TAMANHO_ESPACO_VAZIO)
    espaco = tk.Label(area_vazia, image=imagem, bg=cor_pagina, bd=0)
    espaco.imagem = imagem
    espaco.pack()

    tk.Label(
        area_vazia,
        text=texto,
        font=(FONTE_MANUSCRITA, -int(20 * escala)),
        fg=COR_TEXTO_SECUNDARIO,
        bg=cor_pagina,
        justify="center"
    ).pack(pady=(int(14 * escala), 0))
    widgets.append(area_vazia)


def limpar_grade(widgets, imagens):
    for widget in widgets:
        widget.destroy()
    widgets.clear()
    imagens.clear()


def preencher_grade(container, lista_filmes, widgets, imagens, texto_vazio,
                    inicio=0, quantidade=LIMITE_CARDS_GRADE):
    """
    Apaga a grade e desenha os filmes da lista (ou a mensagem de vazio).
    Desenha só lista_filmes[inicio : inicio + quantidade], para a tela não travar.
    """
    limpar_grade(widgets, imagens)

    if len(lista_filmes) == 0:
        mostrar_mensagem_vazia(container, texto_vazio, widgets)
        return

    filmes_visiveis = lista_filmes[inicio:inicio + quantidade]

    for posicao, filme in enumerate(filmes_visiveis):
        linha = posicao // COLUNAS_CARDS
        coluna = posicao % COLUNAS_CARDS
        criar_card_filme(container, filme, linha, coluna, widgets, imagens)

    # Volta a rolagem para o topo a cada nova busca.
    # (_parent_canvas é interno do customtkinter; se mudar, só pulamos.)
    canvas_rolagem = getattr(container, "_parent_canvas", None)
    if canvas_rolagem is not None:
        canvas_rolagem.yview_moveto(0)


# =========================================================
# PÁGINA CATÁLOGO — GRADE E FILTRO
# =========================================================
scroll_catalogo = criar_area_grade(pagina_catalogo, 3)

widgets_catalogo = []
imagens_catalogo = []


estado_catalogo = {"filmes": [], "inicio": 0}


def desenhar_pagina_catalogo():
    """Mostra a página atual do catálogo e atualiza o "1–20 de 500" e as setas."""
    lista = estado_catalogo["filmes"]
    inicio = estado_catalogo["inicio"]
    total = len(lista)
    fim = min(inicio + CARDS_POR_PAGINA, total)

    if total == 0:
        contador_catalogo.configure(text="0 títulos")
    elif total <= CARDS_POR_PAGINA:
        contador_catalogo.configure(text=f"{total} títulos")
    elif fim == inicio + 1:
        contador_catalogo.configure(text=f"{fim} de {total}")
    else:
        contador_catalogo.configure(text=f"{inicio + 1}–{fim} de {total}")

    botao_pagina_anterior.configure(state="normal" if inicio > 0 else "disabled")
    botao_proxima_pagina.configure(state="normal" if fim < total else "disabled")

    preencher_grade(
        scroll_catalogo,
        lista,
        widgets_catalogo,
        imagens_catalogo,
        (
            "Nada colado nesta página...\n\n"
            "tente outro nome, gênero, ano, diretor ou ator."
        ),
        inicio=inicio,
        quantidade=CARDS_POR_PAGINA
    )


def mudar_pagina_catalogo(direcao):
    novo_inicio = estado_catalogo["inicio"] + direcao * CARDS_POR_PAGINA
    if 0 <= novo_inicio < len(estado_catalogo["filmes"]):
        estado_catalogo["inicio"] = novo_inicio
        desenhar_pagina_catalogo()


botao_pagina_anterior.configure(command=lambda: mudar_pagina_catalogo(-1))
botao_proxima_pagina.configure(command=lambda: mudar_pagina_catalogo(+1))


def atualizar_catalogo(event=None, manter_pagina=False):
    """Aplica a pesquisa + os filtros da busca avançada e redesenha a grade."""
    estado_catalogo["filmes"] = filmes.filtrar_catalogo(
        texto=entrada_catalogo.get(),
        genero=filtro_genero.get(),
        decada=filtro_decada.get(),
        nota_minima=filmes.NOTAS_MINIMAS_DO_CATALOGO.get(filtro_nota.get()),
        ordem=filtro_ordem.get(),
        esconder_assistidos=esconder_assistidos_var.get(),
        tipo=filmes.TIPOS_DO_CATALOGO.get(seletor_tipo_catalogo.get()),
        streaming=streaming_escolhido_no_catalogo()
    )

    if not manter_pagina or estado_catalogo["inicio"] >= len(estado_catalogo["filmes"]):
        estado_catalogo["inicio"] = 0  # nova pesquisa: volta para a primeira página
    desenhar_pagina_catalogo()


# Atualiza enquanto digita, mas só quando a pessoa pausa por um instante.
# Assim "interestelar" faz 1 busca em vez de 12 (uma por letra).
id_busca_agendada = None


def agendar_atualizacao_catalogo(event=None):
    global id_busca_agendada

    if id_busca_agendada is not None:
        janela.after_cancel(id_busca_agendada)

    id_busca_agendada = janela.after(ATRASO_BUSCA_CATALOGO_MS, executar_busca_agendada)


def executar_busca_agendada():
    global id_busca_agendada
    id_busca_agendada = None
    atualizar_catalogo()


entrada_catalogo.bind("<KeyRelease>", agendar_atualizacao_catalogo)


# =========================================================
# PÁGINA RECOMENDAÇÕES
# =========================================================
criar_cabecalho_pagina(
    pagina_recomendacoes,
    "Recomendações",
    "os filmes que o CineAI separou para você nesta conversa"
)

scroll_recomendacoes = criar_area_grade(pagina_recomendacoes, 1)

historico_recomendacoes = []
widgets_recomendacoes = []
imagens_recomendacoes = []


def atualizar_recomendacoes():
    preencher_grade(
        scroll_recomendacoes,
        historico_recomendacoes,
        widgets_recomendacoes,
        imagens_recomendacoes,
        (
            "Nenhuma recomendação guardada ainda...\n\n"
            "peça um filme ao CineAI e ele vem parar aqui."
        )
    )


def adicionar_ao_historico(filme):
    """Guarda a recomendação (sem repetir) e redesenha a página."""
    # Compara pelo id: os dois "O Rei Leão" (1994 e 2019) são filmes diferentes.
    for filme_existente in historico_recomendacoes:
        if usuario.chave_filme(filme_existente) == usuario.chave_filme(filme):
            return

    historico_recomendacoes.append(filme)
    atualizar_recomendacoes()


# =========================================================
# PÁGINA CHAT CINEAI
# =========================================================
cabecalho_chat = criar_cabecalho_pagina(
    pagina_chat,
    "Chat CineAI",
    "cada conversa vira uma página do seu diário"
)

# ---------------- Barra de conversas salvas ----------------
SEM_CONVERSAS = "Nenhuma conversa salva ainda"
CONVERSA_ATUAL_NOVA = "✦ Página nova (ainda em branco)"

barra_conversas = ctk.CTkFrame(cabecalho_chat, fg_color="transparent")
barra_conversas.pack(fill="x", pady=(12, 0))

rotulo_conversas = ctk.CTkLabel(
    barra_conversas,
    text="PÁGINAS DO DIÁRIO:",
    font=(FONTE_TITULO, 15),
    text_color=COR_VERMELHO
)
rotulo_conversas.pack(side="left", padx=(0, 8))

seletor_conversas = ctk.CTkOptionMenu(
    barra_conversas,
    values=[SEM_CONVERSAS],
    width=380,
    height=32,
    font=(FONTE, 12),
    dropdown_font=(FONTE, 12),
    fg_color=COR_PAPEL_ESCURO,
    button_color=COR_VERMELHO,
    button_hover_color=COR_VERMELHO_HOVER,
    text_color=COR_TEXTO,
    dropdown_fg_color=COR_PAPEL,
    dropdown_hover_color=COR_PAPEL_ESCURO,
    dropdown_text_color=COR_TEXTO,
    corner_radius=4,
    dynamic_resizing=False,
    command=lambda rotulo_escolhido: abrir_conversa_pelo_rotulo(rotulo_escolhido)
)
seletor_conversas.pack(side="left")

botao_nova_conversa = ctk.CTkButton(
    barra_conversas,
    text="＋ NOVA PÁGINA",
    width=140,
    height=32,
    font=(FONTE_INTERFACE, 12, "bold"),
    fg_color=COR_VERMELHO,
    hover_color=COR_VERMELHO_HOVER,
    text_color=COR_TEXTO_CAPA,
    corner_radius=4,
    command=lambda: iniciar_nova_conversa()
)
botao_nova_conversa.pack(side="left", padx=(10, 0))

botao_apagar_conversa = ctk.CTkButton(
    barra_conversas,
    text="🗑 APAGAR",
    width=100,
    height=32,
    font=(FONTE_INTERFACE, 12, "bold"),
    fg_color=COR_BOTAO_NEUTRO,
    hover_color=COR_BOTAO_NEUTRO_HOVER,
    text_color=COR_VINHO,
    corner_radius=4,
    command=lambda: apagar_conversa_atual()
)
botao_apagar_conversa.pack(side="left", padx=(8, 0))

chat_completo = criar_caixa_chat(pagina_chat)
chat_completo.grid(row=1, column=0, sticky="nsew", padx=42, pady=(0, 12))

area_chat_completo = ctk.CTkFrame(pagina_chat, fg_color="transparent")
area_chat_completo.grid(row=2, column=0, sticky="ew", padx=42, pady=(0, 30))
area_chat_completo.grid_columnconfigure(0, weight=1)

entrada_chat_completo = criar_entrada_chat(area_chat_completo, 48)
entrada_chat_completo.grid(row=0, column=0, sticky="ew", padx=(0, 10))


def enviar_chat_completo(event=None):
    enviar_da_entrada(entrada_chat_completo)


botao_chat_completo = criar_botao_enviar(area_chat_completo, 48)
botao_chat_completo.configure(command=enviar_chat_completo)
botao_chat_completo.grid(row=0, column=1)
entrada_chat_completo.bind("<Return>", enviar_chat_completo)

botao_surpresa_chat = criar_botao_surpresa(area_chat_completo, 48, texto="🎲")
botao_surpresa_chat.configure(width=56, font=(FONTE_SIMBOLOS, 22))
botao_surpresa_chat.grid(row=0, column=2, padx=(10, 0))

status_chat_completo = criar_status(area_chat_completo)
status_chat_completo.grid(row=1, column=0, columnspan=3, sticky="w", pady=(6, 0))

# As duas telas de chat recebem as mesmas mensagens.
caixas_chat = [chat, chat_completo]


adicionar_mensagem(NOME_IA, MENSAGEM_BOAS_VINDAS)


# ---------------- Histórico: abrir, nova, apagar ----------------
conversa_atual = conversas.nova_conversa()
rotulo_para_id = {}
filmes_por_chave = {usuario.chave_filme(filme): filme for filme in filmes.filmes}


def atualizar_lista_conversas():
    """Recarrega a lista do seletor e deixa marcada a conversa atual."""
    rotulo_para_id.clear()
    rotulos = []

    if not conversa_atual["mensagens"]:
        rotulos.append(CONVERSA_ATUAL_NOVA)

    rotulo_da_atual = None
    for conversa in conversas.conversas_salvas():
        rotulo = conversas.rotulo(conversa)
        while rotulo in rotulo_para_id:  # dois títulos iguais no mesmo minuto
            rotulo += " "
        rotulo_para_id[rotulo] = conversa["id"]
        rotulos.append(rotulo)

        if conversa["id"] == conversa_atual["id"]:
            rotulo_da_atual = rotulo

    if not rotulos:
        rotulos = [SEM_CONVERSAS]

    seletor_conversas.configure(values=rotulos)
    seletor_conversas.set(rotulo_da_atual or rotulos[0])


def limpar_caixas_chat():
    for mural in caixas_chat:
        mural.limpar()


def limpar_recomendacoes_da_tela():
    historico_recomendacoes.clear()
    atualizar_recomendacoes()
    filmes_exibidos.clear()
    limpar_cards()


def preparar_tela_vazia():
    filmes.reiniciar_conversa()
    limpar_caixas_chat()
    adicionar_mensagem(NOME_IA, MENSAGEM_BOAS_VINDAS)
    limpar_recomendacoes_da_tela()
    atualizar_lista_conversas()
    entrada_chat_completo.focus()


def iniciar_nova_conversa():
    global conversa_atual

    if conversa_atual["mensagens"]:
        conversa_atual = conversas.nova_conversa()

    preparar_tela_vazia()


def abrir_conversa_pelo_rotulo(rotulo_escolhido):
    global conversa_atual

    id_escolhido = rotulo_para_id.get(rotulo_escolhido)
    if id_escolhido is None or id_escolhido == conversa_atual["id"]:
        return

    conversa = conversas.buscar_por_id(id_escolhido)
    if conversa is None:
        return

    conversa_atual = conversa

    # Mostra as mensagens de uma vez (sem o efeito de digitação)
    limpar_caixas_chat()
    for mensagem in conversa["mensagens"]:
        if mensagem["autor"] == conversas.AUTOR_VOCE:
            adicionar_mensagem(NOME_USUARIO, mensagem["texto"])
        else:
            adicionar_mensagem(NOME_IA, mensagem["texto"])

    # O CineAI volta a lembrar do último filme ("Quem dirigiu ele?" funciona)
    filmes.restaurar_contexto(conversa["filmes_recomendados"])

    limpar_recomendacoes_da_tela()
    for chave in conversa["filmes_recomendados"]:
        filme = filmes_por_chave.get(chave)
        if filme is not None:
            adicionar_ao_historico(filme)
            adicionar_filme_aos_cards(filme)

    atualizar_lista_conversas()
    entrada_chat_completo.focus()


def apagar_conversa_atual():
    global conversa_atual

    if not conversa_atual["mensagens"]:
        return  # conversa nova, ainda não salva: nada para apagar

    confirmou = messagebox.askyesno(
        "Apagar conversa",
        f'Apagar a conversa "{conversa_atual["titulo"]}"?\n\nIsso não pode ser desfeito.'
    )
    if not confirmou:
        return

    conversas.apagar(conversa_atual["id"])
    conversa_atual = conversas.nova_conversa()
    preparar_tela_vazia()


atualizar_lista_conversas()


# =========================================================
# PÁGINA MEUS FILMES (favoritos e já assistidos)
# =========================================================
criar_cabecalho_pagina(
    pagina_meus_filmes,
    "Meu diário",
    "os filmes que fizeram parte da sua história"
)

ABA_CAPA = "📖  Capa"
ABA_DIARIO = "✎  Diário"
ABA_FAVORITOS = "❤  Favoritos"
ABA_QUERO_VER = "📌  Quero assistir"

# Abas como marcadores de couro: marrom, e vermelho na aba aberta.
ESTILO_ABAS = {
    "fg_color": "#7A5A4A",
    "selected_color": COR_VERMELHO,
    "selected_hover_color": COR_VERMELHO_HOVER,
    "unselected_color": "#8C6A58",
    "unselected_hover_color": "#7A5A4A",
    "text_color": COR_TEXTO_CAPA,
    "corner_radius": 4,
}

ORDEM_RECENTES = "Mais recentes"
ORDEM_ANTIGOS = "Mais antigos"
ORDEM_MINHA_NOTA = "★ Minha nota"
ORDENS_DO_DIARIO = {
    ORDEM_RECENTES: usuario.ORDEM_DIARIO_RECENTES,
    ORDEM_ANTIGOS: usuario.ORDEM_DIARIO_ANTIGOS,
    ORDEM_MINHA_NOTA: usuario.ORDEM_DIARIO_NOTA,
}

area_abas = ctk.CTkFrame(pagina_meus_filmes, fg_color="transparent")
area_abas.grid(row=1, column=0, sticky="ew", padx=42, pady=(2, 10))
area_abas.grid_columnconfigure(2, weight=1)

seletor_aba = ctk.CTkSegmentedButton(
    area_abas,
    values=[ABA_CAPA, ABA_DIARIO, ABA_FAVORITOS, ABA_QUERO_VER],
    height=38,
    font=(FONTE_INTERFACE, 13, "bold"),
    **ESTILO_ABAS,
    command=lambda aba_escolhida: atualizar_meus_filmes()
)
seletor_aba.set(ABA_CAPA)
seletor_aba.grid(row=0, column=0, sticky="w")

# Ordenação: só aparece na aba do diário.
seletor_ordem = ctk.CTkSegmentedButton(
    area_abas,
    values=list(ORDENS_DO_DIARIO),
    height=32,
    font=(FONTE_INTERFACE, 11, "bold"),
    **ESTILO_ABAS,
    command=lambda ordem_escolhida: mudar_ordem_do_diario()
)
seletor_ordem.set(ORDEM_RECENTES)

contador_meus_filmes = ctk.CTkLabel(
    area_abas,
    text="",
    font=(FONTE_MANUSCRITA, 16),
    text_color=COR_VINHO,
    anchor="e"
)
contador_meus_filmes.grid(row=0, column=2, sticky="e")

scroll_meus_filmes = criar_area_grade(pagina_meus_filmes, 2)

widgets_meus_filmes = []
imagens_meus_filmes = []


# =========================================================
# DIÁRIO AUTOMÁTICO — uma entrada para cada título visto
# =========================================================
# As entradas vêm prontas do usuario.entradas_do_diario() (número, data, nota
# e anotação). Aqui só desenhamos: separador do mês, data na margem, polaroide,
# estrelas e a anotação, que dá para escrever ali mesmo (salva sozinha).
MESES_EM_PORTUGUES = [
    "JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO",
    "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO",
]
ENTRADAS_POR_VEZ = 30                  # o resto aparece com "ver entradas mais antigas"
TAMANHO_POSTER_ENTRADA = (88, 130)
LARGURA_TEXTO_ENTRADA = 560
COR_LINHA_DIARIO = COR_PAUTA_CADERNO

estado_diario = {"quantidade": ENTRADAS_POR_VEZ}
edicao_no_diario = {"filme": None, "sessao": None, "caixa": None, "agendamento": None}


def titulo_do_grupo(entrada, ordem):
    """Separador das entradas: o mês ('OUTUBRO DE 2026') ou, na ordem por nota, as estrelas."""
    if ordem == usuario.ORDEM_DIARIO_NOTA:
        nota = entrada["nota"]
        if nota is None:
            return "ainda sem nota"
        return f"{usuario.texto_estrelas(nota)}  {nota} estrela{'s' if nota > 1 else ''}"

    data_vista = entrada["data"]
    if data_vista is None:
        return "sem data"
    return f"{MESES_EM_PORTUGUES[data_vista.month - 1]} DE {data_vista.year}"


def criar_separador_do_grupo(container, texto, imagens):
    """'✦ OUTUBRO DE 2026' à mão, em vermelho, com a passada de marca-texto dourado."""
    escala = escala_da_tela(container)

    def px(valor):
        return int(valor * escala)

    caixa = tk.Frame(container, bg=COR_FUNDO)
    caixa.pack(fill="x", padx=px(10), pady=(px(18), px(4)))

    linha = tk.Frame(caixa, bg=COR_FUNDO)
    linha.pack(anchor="w")

    desenho = desenhar_icone("estrela", cor_rgb(COR_RABISCO) + (255,)).resize(
        (px(22), px(22)), Image.LANCZOS
    )
    fundo = Image.new("RGBA", desenho.size, cor_rgb(COR_FUNDO) + (255,))
    fundo.alpha_composite(desenho.convert("RGBA"))
    icone = ImageTk.PhotoImage(fundo.convert("RGB"))
    imagens.append(icone)
    tk.Label(linha, image=icone, bg=COR_FUNDO, bd=0).pack(side="left", padx=(0, px(6)))

    tk.Label(
        linha, text=texto, font=(FONTE_MANUSCRITA, -px(23), "bold"),
        fg=COR_TITULO_MANUSCRITO, bg=COR_FUNDO
    ).pack(side="left")

    tk.Frame(
        caixa, bg=COR_MARCA_TEXTO, height=px(6), width=px(min(380, 12 * len(texto)))
    ).pack(anchor="w", padx=(px(30), 0))


def salvar_edicao_do_diario():
    """Grava o que está escrito na caixa aberta numa entrada (se houver)."""
    if edicao_no_diario["agendamento"] is not None:
        janela.after_cancel(edicao_no_diario["agendamento"])
        edicao_no_diario["agendamento"] = None

    caixa = edicao_no_diario["caixa"]
    if caixa is not None and caixa.winfo_exists():
        usuario.definir_anotacao(edicao_no_diario["filme"], caixa.get("1.0", "end"), sessao=edicao_no_diario["sessao"])


def fechar_edicao_do_diario():
    salvar_edicao_do_diario()
    edicao_no_diario.update({"filme": None, "sessao": None, "caixa": None, "agendamento": None})


def montar_anotacao_da_entrada(area, filme, escala, editando=False, sessao=None):
    """
    A anotação da entrada: o texto à mão (caneta azul) com '✎ editar', ou um
    convite para escrever. Clicando, a própria entrada vira um caderninho.
    """
    def px(valor):
        return int(valor * escala)

    for widget in area.winfo_children():
        widget.destroy()

    if editando:
        fechar_edicao_do_diario()  # só uma caixa aberta por vez

        caixa = ctk.CTkTextbox(
            area, height=px(90), wrap="word", corner_radius=2,
            fg_color=COR_BILHETE, text_color=COR_AZUL_CANETA, border_width=1,
            border_color=COR_BORDA_PAPEL, font=(FONTE_MANUSCRITA, 17)
        )
        caixa.pack(fill="x", pady=(px(4), px(2)))
        caixa.insert("1.0", usuario.obter_anotacao(filme, sessao))
        caixa.focus_set()

        rodape = tk.Frame(area, bg=COR_CARD)
        rodape.pack(fill="x")
        aviso = tk.Label(
            rodape, text="escreva à vontade: salva sozinho",
            font=(FONTE_MANUSCRITA, -px(13)), fg=COR_TEXTO_SUAVE, bg=COR_CARD
        )
        aviso.pack(side="left")

        def salvar_agora():
            edicao_no_diario["agendamento"] = None
            if caixa.winfo_exists():
                usuario.definir_anotacao(filme, caixa.get("1.0", "end"), sessao=sessao)
                if aviso.winfo_exists():
                    aviso.configure(text="salvo no seu diário ✓")
                atualizar_contador_meus_filmes()

        def agendar_salvamento(event=None):
            if edicao_no_diario["agendamento"] is not None:
                janela.after_cancel(edicao_no_diario["agendamento"])
            aviso.configure(text="escrevendo…")
            edicao_no_diario["agendamento"] = janela.after(ATRASO_SALVAR_ANOTACAO_MS, salvar_agora)

        def terminar(event=None):
            fechar_edicao_do_diario()
            atualizar_contador_meus_filmes()
            montar_anotacao_da_entrada(area, filme, escala, sessao=sessao)

        caixa.bind("<KeyRelease>", agendar_salvamento)
        edicao_no_diario.update({"filme": filme, "sessao": sessao, "caixa": caixa, "agendamento": None})

        botao_pronto = tk.Label(
            rodape, text="  pronto ✓  ", font=(FONTE_MANUSCRITA, -px(15), "bold"),
            fg=COR_TEXTO_CAPA, bg=COR_VERMELHO, cursor="hand2"
        )
        botao_pronto.pack(side="right", pady=(px(2), 0))
        botao_pronto.bind("<Button-1>", terminar)
        return

    texto = usuario.obter_anotacao(filme, sessao)

    def abrir_edicao(event=None):
        montar_anotacao_da_entrada(area, filme, escala, editando=True, sessao=sessao)

    if texto:
        rotulo = tk.Label(
            area, text=f"“{texto}”", font=(FONTE_MANUSCRITA, -px(17)),
            fg=COR_AZUL_CANETA, bg=COR_CARD, justify="left", anchor="w",
            wraplength=px(LARGURA_TEXTO_ENTRADA), cursor="hand2"
        )
        rotulo.pack(fill="x")
        editar = tk.Label(
            area, text="✎ editar", font=(FONTE_MANUSCRITA, -px(14)),
            fg=COR_TEXTO_SUAVE, bg=COR_CARD, cursor="hand2"
        )
        editar.pack(anchor="e")
        vincular_clique([rotulo, editar], abrir_edicao)
    else:
        convite = tk.Label(
            area, text="✎ o que mudou desta vez?" if sessao is not None else "✎ escrever o que você achou...", font=(FONTE_MANUSCRITA, -px(16)),
            fg=COR_TEXTO_SUAVE, bg=COR_CARD, anchor="w", cursor="hand2"
        )
        convite.pack(anchor="w")
        vincular_clique([convite], abrir_edicao)


ANO_MAIS_ANTIGO_NO_EDITOR = 1930


def abrir_editor_de_data(filme, sessao=None):
    """
    Bilhetinho para corrigir quando você assistiu (dia / mês / ano).
    Útil para o que você marcou hoje, mas viu anos atrás.
    sessao=None corrige a 1ª vez; 0, 1... corrigem cada "vi de novo".
    """
    data_atual = usuario.data_da_sessao(usuario.chave_filme(filme), sessao) or date.today()

    editor = ctk.CTkToplevel(janela)
    editor.title("Quando você assistiu?")
    editor.geometry("360x250")
    editor.resizable(False, False)
    editor.configure(fg_color=COR_PAPEL)
    editor.transient(janela)
    janela.update_idletasks()
    editor.geometry(f"+{janela.winfo_rootx() + 380}+{janela.winfo_rooty() + 220}")  # perto do diário
    editor.after(50, editor.grab_set)   # só depois de a janela aparecer

    ctk.CTkLabel(
        editor, text="quando você assistiu?", font=(FONTE_MANUSCRITA, 24, "bold"),
        text_color=COR_TITULO_MANUSCRITO
    ).pack(pady=(18, 0))
    ctk.CTkLabel(
        editor, text=filme["nome"], font=(FONTE, 13, "italic"), text_color=COR_TEXTO_SECUNDARIO
    ).pack()

    linha_campos = ctk.CTkFrame(editor, fg_color="transparent")
    linha_campos.pack(pady=(14, 4))

    estilo_menu = {
        "fg_color": COR_BILHETE, "button_color": COR_VERMELHO, "button_hover_color": COR_VERMELHO_HOVER,
        "text_color": COR_TEXTO, "dropdown_fg_color": COR_PAPEL, "dropdown_text_color": COR_TEXTO,
        "font": (FONTE_INTERFACE, 13, "bold"), "dropdown_font": (FONTE_INTERFACE, 12),
    }
    nomes_meses = [mes[:3] for mes in MESES_EM_PORTUGUES]
    anos = [str(ano) for ano in range(date.today().year, ANO_MAIS_ANTIGO_NO_EDITOR - 1, -1)]

    menu_dia = ctk.CTkOptionMenu(linha_campos, values=[f"{dia:02d}" for dia in range(1, 32)], width=70, **estilo_menu)
    menu_mes = ctk.CTkOptionMenu(linha_campos, values=nomes_meses, width=80, **estilo_menu)
    caixa_ano = ctk.CTkComboBox(
        linha_campos, values=anos, width=95, fg_color=COR_BILHETE, border_color=COR_BORDA_PAPEL,
        button_color=COR_VERMELHO, button_hover_color=COR_VERMELHO_HOVER, text_color=COR_TEXTO,
        dropdown_fg_color=COR_PAPEL, dropdown_text_color=COR_TEXTO, font=(FONTE_INTERFACE, 13, "bold")
    )
    for campo in (menu_dia, menu_mes, caixa_ano):
        campo.pack(side="left", padx=4)

    def preencher(data_escolhida):
        menu_dia.set(f"{data_escolhida.day:02d}")
        menu_mes.set(nomes_meses[data_escolhida.month - 1])
        caixa_ano.set(str(data_escolhida.year))

    preencher(data_atual)

    aviso = ctk.CTkLabel(editor, text="", font=(FONTE_MANUSCRITA, 15), text_color=COR_VERMELHO)
    aviso.pack(pady=(2, 0))

    def salvar():
        try:
            nova_data = date(int(caixa_ano.get()), nomes_meses.index(menu_mes.get()) + 1, int(menu_dia.get()))
        except ValueError:
            aviso.configure(text="esse dia não existe nesse mês (ou o ano está estranho)")
            return
        try:
            usuario.definir_data_assistido(filme, nova_data, sessao=sessao)
        except ValueError as erro:
            aviso.configure(text=str(erro))
            return
        editor.destroy()
        ao_mudar_listas()   # diário, capa e carimbo WATCHED das polaroides mudam juntos

    linha_botoes = ctk.CTkFrame(editor, fg_color="transparent")
    linha_botoes.pack(pady=(8, 0))
    ctk.CTkButton(
        linha_botoes, text="hoje", width=90, height=34, corner_radius=4, fg_color=COR_PAPEL_ESCURO,
        hover_color=COR_BOTAO_NEUTRO_HOVER, text_color=COR_VINHO, font=(FONTE_MANUSCRITA, 16, "bold"),
        command=lambda: preencher(date.today())
    ).pack(side="left", padx=6)
    ctk.CTkButton(
        linha_botoes, text="salvar ✓", width=120, height=34, corner_radius=4, fg_color=COR_VERMELHO,
        hover_color=COR_VERMELHO_HOVER, text_color=COR_TEXTO_CAPA, font=(FONTE_MANUSCRITA, 16, "bold"),
        command=salvar
    ).pack(side="left", padx=6)


def criar_entrada_do_diario(container, entrada, imagens):
    """
    Uma entrada:  [03 / OUT / 2026] [polaroide] ENTRADA #012 · SÉRIE
                                                Nome do filme (2021)
                                                ★★★★☆   ✓ WATCHED
                                                “sua anotação...”   ✎ editar
    """
    filme = entrada["filme"]
    sessao = entrada.get("sessao")          # None = 1ª vez | 0, 1... = "vi de novo"
    revisita = sessao is not None
    escala = escala_da_tela(container)

    def px(valor):
        return int(valor * escala)

    folha = tk.Frame(
        container, bg=COR_CARD, highlightbackground=COR_BORDA_PAPEL,
        highlightcolor=COR_BORDA_PAPEL, highlightthickness=1
    )
    folha.pack(fill="x", padx=px(10), pady=px(6))

    # ---------- margem com a data (como a de um caderno) ----------
    margem = tk.Frame(folha, bg=COR_CARD, width=px(78))
    margem.pack(side="left", fill="y")
    margem.pack_propagate(False)
    tk.Frame(folha, bg=COR_VERMELHO, width=max(1, px(2))).pack(side="left", fill="y", pady=px(8))

    data_vista = entrada["data"]
    rotulos_da_data = []
    if data_vista is not None:
        rotulos_da_data.append(tk.Label(
            margem, text=f"{data_vista.day:02d}", font=(FONTE_TITULO, -px(34)),
            fg=COR_VERMELHO, bg=COR_CARD, cursor="hand2"
        ))
        rotulos_da_data.append(tk.Label(
            margem, text=MESES_EM_PORTUGUES[data_vista.month - 1][:3],
            font=(FONTE_INTERFACE, -px(12), "bold"), fg=COR_VINHO, bg=COR_CARD, cursor="hand2"
        ))
        rotulos_da_data.append(tk.Label(
            margem, text=str(data_vista.year), font=(FONTE_INTERFACE, -px(10)),
            fg=COR_TEXTO_SUAVE, bg=COR_CARD, cursor="hand2"
        ))
    else:
        rotulos_da_data.append(tk.Label(
            margem, text="?", font=(FONTE_TITULO, -px(30)), fg=COR_TEXTO_SUAVE, bg=COR_CARD, cursor="hand2"
        ))
    rotulos_da_data.append(tk.Label(
        margem, text="✎ data", font=(FONTE_MANUSCRITA, -px(12)), fg=COR_TEXTO_SUAVE, bg=COR_CARD, cursor="hand2"
    ))
    for posicao, rotulo in enumerate(rotulos_da_data):
        rotulo.pack(pady=(px(16), 0) if posicao == 0 else (px(2) if rotulo.cget("text") == "✎ data" else 0, 0))
    vincular_clique(rotulos_da_data + [margem], lambda event: abrir_editor_de_data(filme, sessao))

    # ---------- polaroide pequena ----------
    imagem = imagem_do_recorte(filme, escala, COR_CARD, TAMANHO_POSTER_ENTRADA, modo="compacto")
    imagens.append(imagem)
    foto = tk.Label(folha, image=imagem, bg=COR_CARD, bd=0, cursor="hand2")
    foto.imagem = imagem
    foto.pack(side="left", padx=(px(10), px(6)), pady=px(8), anchor="n")

    # ---------- textos ----------
    textos = tk.Frame(folha, bg=COR_CARD)
    textos.pack(side="left", fill="both", expand=True, padx=(px(8), px(16)), pady=(px(12), px(10)))

    linha_etiqueta = tk.Frame(textos, bg=COR_CARD)
    linha_etiqueta.pack(anchor="w")
    tipo = "SÉRIE" if filmes.eh_serie(filme) else "FILME"
    tk.Label(
        linha_etiqueta, text=f"ENTRADA #{entrada['numero']:03d}  ·  {tipo}",
        font=(FONTE_INTERFACE, -px(10), "bold"),
        fg=COR_SERIE if filmes.eh_serie(filme) else COR_TEXTO_SUAVE, bg=COR_CARD
    ).pack(side="left")
    if entrada.get("vez", 1) > 1:
        tk.Label(
            linha_etiqueta, text=f"  ↻ {entrada['vez']}ª VEZ ", font=(FONTE_INTERFACE, -px(10), "bold"),
            fg=COR_TEXTO_CAPA, bg=COR_DOURADO
        ).pack(side="left", padx=(px(8), 0))
    if usuario.eh_favorito(filme):
        tk.Label(
            linha_etiqueta, text="  ♥ favorito", font=(FONTE_MANUSCRITA, -px(13), "bold"),
            fg=COR_VERMELHO, bg=COR_CARD
        ).pack(side="left")
    if revisita:
        apagar = tk.Label(
            linha_etiqueta, text="   ✕ apagar esta sessão", font=(FONTE_MANUSCRITA, -px(13)),
            fg=COR_TEXTO_SUAVE, bg=COR_CARD, cursor="hand2"
        )
        apagar.pack(side="left")

        def apagar_sessao(event=None):
            if messagebox.askyesno(
                "Apagar sessão",
                f"Apagar a sessão em que você viu {filme['nome']} de novo?\n"
                "(A primeira vez continua no diário.)",
                parent=janela
            ):
                fechar_edicao_do_diario()
                usuario.apagar_revisita(filme, sessao)
                ao_mudar_listas()

        apagar.bind("<Button-1>", apagar_sessao)

    nome = tk.Label(
        textos, text=f"{filme['nome']}  ({filmes.periodo_de_exibicao(filme)})",
        font=(FONTE, -px(17), "bold"), fg=COR_TEXTO, bg=COR_CARD, anchor="w",
        justify="left", wraplength=px(LARGURA_TEXTO_ENTRADA), cursor="hand2"
    )
    nome.pack(fill="x", pady=(px(2), px(2)))

    linha_nota = tk.Frame(textos, bg=COR_CARD)
    linha_nota.pack(anchor="w", pady=(0, px(6)))
    if entrada["nota"] is not None:
        tk.Label(
            linha_nota, text=usuario.texto_estrelas(entrada["nota"]),
            font=(FONTE_SIMBOLOS, -px(17)), fg=COR_ESTRELA_ACESA, bg=COR_CARD
        ).pack(side="left")
    else:
        tk.Label(
            linha_nota, text="sem nota ainda", font=(FONTE_MANUSCRITA, -px(14)),
            fg=COR_TEXTO_SUAVE, bg=COR_CARD
        ).pack(side="left")
    tk.Label(
        linha_nota, text=" ↻ WATCHED AGAIN " if revisita else " ✓ WATCHED ", font=(FONTE_TITULO, -px(12)),
        fg=COR_VERMELHO, bg=COR_CARD, highlightbackground=COR_VERMELHO, highlightthickness=1
    ).pack(side="left", padx=(px(12), 0))

    tk.Frame(textos, bg=COR_LINHA_DIARIO, height=1).pack(fill="x", pady=(0, px(6)))

    area_anotacao = tk.Frame(textos, bg=COR_CARD)
    area_anotacao.pack(fill="x")
    montar_anotacao_da_entrada(area_anotacao, filme, escala, sessao=sessao)

    def abrir(event=None):
        abrir_detalhes(filme)

    vincular_clique([foto, nome], abrir)


def mostrar_mais_entradas(event=None):
    estado_diario["quantidade"] += ENTRADAS_POR_VEZ
    atualizar_meus_filmes(voltar_ao_topo=False)


def mudar_ordem_do_diario():
    estado_diario["quantidade"] = ENTRADAS_POR_VEZ
    atualizar_meus_filmes()


def desenhar_diario(voltar_ao_topo=True):
    """Desenha as entradas do diário (no lugar da grade de pôsteres)."""
    fechar_edicao_do_diario()  # salva o que estava sendo escrito antes de redesenhar
    limpar_grade(widgets_meus_filmes, imagens_meus_filmes)

    ordem = ORDENS_DO_DIARIO[seletor_ordem.get()]
    entradas = usuario.entradas_do_diario(filmes.filmes, ordem)

    if not entradas:
        mostrar_mensagem_vazia(scroll_meus_filmes, TEXTO_DIARIO_VAZIO, widgets_meus_filmes)
        return

    folha_do_diario = tk.Frame(scroll_meus_filmes, bg=COR_FUNDO)
    folha_do_diario.grid(row=0, column=0, columnspan=COLUNAS_CARDS, sticky="ew")
    widgets_meus_filmes.append(folha_do_diario)

    grupo_anterior = None
    for entrada in entradas[:estado_diario["quantidade"]]:
        grupo = titulo_do_grupo(entrada, ordem)
        if grupo != grupo_anterior:
            criar_separador_do_grupo(folha_do_diario, grupo, imagens_meus_filmes)
            grupo_anterior = grupo
        criar_entrada_do_diario(folha_do_diario, entrada, imagens_meus_filmes)

    faltam = len(entradas) - estado_diario["quantidade"]
    if faltam > 0:
        botao_mais = tk.Label(
            folha_do_diario,
            text=f"  ↓ ver entradas mais antigas ({faltam})  ",
            font=(FONTE_MANUSCRITA, -int(17 * escala_da_tela(folha_do_diario)), "bold"),
            fg=COR_VERMELHO, bg=COR_PAPEL_ESCURO, cursor="hand2"
        )
        botao_mais.pack(pady=(14, 20))
        botao_mais.bind("<Button-1>", mostrar_mais_entradas)
    else:
        tk.Label(
            folha_do_diario, text="✦ fim do diário (por enquanto) ✦",
            font=(FONTE_MANUSCRITA, -int(15 * escala_da_tela(folha_do_diario))),
            fg=COR_TEXTO_SUAVE, bg=COR_FUNDO
        ).pack(pady=(14, 20))

    canvas_rolagem = getattr(scroll_meus_filmes, "_parent_canvas", None)
    if voltar_ao_topo and canvas_rolagem is not None:
        canvas_rolagem.yview_moveto(0)


# =========================================================
# QUERO ASSISTIR — checklist presa na página
# =========================================================
# Marcar o ☐ conta como "vi": o título sai da lista e vira entrada no diário.
TAMANHO_POSTER_CHECKLIST = (44, 64)
COR_FOLHA_CHECKLIST = COR_BILHETE
ATRASO_RISCAR_MS = 280  # dá tempo de ver o ☑ antes do título sair da lista


def criar_item_da_checklist(folha, filme, escala, imagens):
    def px(valor):
        return int(valor * escala)

    linha = tk.Frame(folha, bg=COR_FOLHA_CHECKLIST)
    linha.pack(fill="x", padx=px(22), pady=(px(4), 0))

    caixinha = tk.Label(
        linha, text="☐", font=(FONTE_SIMBOLOS, -px(24)), fg=COR_VINHO,
        bg=COR_FOLHA_CHECKLIST, cursor="hand2"
    )
    caixinha.pack(side="left", padx=(0, px(8)))

    imagem = imagem_do_recorte(filme, escala, COR_FOLHA_CHECKLIST, TAMANHO_POSTER_CHECKLIST, modo="compacto")
    imagens.append(imagem)
    foto = tk.Label(linha, image=imagem, bg=COR_FOLHA_CHECKLIST, bd=0, cursor="hand2")
    foto.imagem = imagem
    foto.pack(side="left", padx=(0, px(10)))

    textos = tk.Frame(linha, bg=COR_FOLHA_CHECKLIST)
    textos.pack(side="left", fill="x", expand=True)

    tipo = "série" if filmes.eh_serie(filme) else "filme"
    nome = tk.Label(
        textos, text=f"{filme['nome']}  ({filmes.periodo_de_exibicao(filme)} · {tipo})",
        font=(FONTE, -px(15), "bold"), fg=COR_TEXTO, bg=COR_FOLHA_CHECKLIST,
        anchor="w", justify="left", wraplength=px(LARGURA_TEXTO_ENTRADA), cursor="hand2"
    )
    nome.pack(fill="x")

    guardado_em = usuario.data_em_que_guardou(filme)
    detalhe = f"guardado em {guardado_em.strftime('%d/%m/%Y')}" if guardado_em else "guardado pra depois"
    if usuario.foi_assistido(filme):
        detalhe += "  ·  pra rever"
    tk.Label(
        textos, text=detalhe, font=(FONTE_MANUSCRITA, -px(14)), fg=COR_TEXTO_SUAVE,
        bg=COR_FOLHA_CHECKLIST, anchor="w"
    ).pack(fill="x")

    tirar = tk.Label(
        linha, text="✕ tirar", font=(FONTE_MANUSCRITA, -px(14)), fg=COR_TEXTO_SUAVE,
        bg=COR_FOLHA_CHECKLIST, cursor="hand2"
    )
    tirar.pack(side="right", padx=(px(10), 0))

    tk.Frame(folha, bg=COR_LINHA_DIARIO, height=1).pack(fill="x", padx=px(22), pady=(px(4), 0))

    def marcar_como_visto(event=None):
        caixinha.configure(text="☑", fg=COR_ASSISTIDO)
        nome.configure(fg=COR_TEXTO_SUAVE, font=(FONTE, -px(15), "bold overstrike"))

        def concluir():
            if usuario.foi_assistido(filme):
                usuario.registrar_revisita(filme)        # era "pra rever": vira uma sessão nova no diário
            else:
                usuario.alternar_assistido(filme)        # vira entrada no diário
            ao_mudar_listas()
        janela.after(ATRASO_RISCAR_MS, concluir)

    def tirar_da_lista(event=None):
        usuario.alternar_quero_assistir(filme)
        ao_mudar_listas()

    def abrir(event=None):
        abrir_detalhes(filme)

    caixinha.bind("<Button-1>", marcar_como_visto)
    tirar.bind("<Button-1>", tirar_da_lista)
    vincular_clique([foto, nome], abrir)


def desenhar_quero_assistir():
    limpar_grade(widgets_meus_filmes, imagens_meus_filmes)
    guardados = usuario.filmes_da_lista("quero_assistir", filmes.filmes)

    if not guardados:
        mostrar_mensagem_vazia(scroll_meus_filmes, TEXTO_QUERO_VER_VAZIO, widgets_meus_filmes)
        return

    escala = escala_da_tela(scroll_meus_filmes)

    def px(valor):
        return int(valor * escala)

    area = tk.Frame(scroll_meus_filmes, bg=COR_FUNDO)
    area.grid(row=0, column=0, columnspan=COLUNAS_CARDS, sticky="ew")
    widgets_meus_filmes.append(area)

    # A folha da checklist, com um pedaço de fita prendendo em cima
    folha = tk.Frame(
        area, bg=COR_FOLHA_CHECKLIST, highlightbackground=COR_BORDA_PAPEL,
        highlightcolor=COR_BORDA_PAPEL, highlightthickness=1
    )
    folha.pack(fill="x", padx=(px(10), px(60)), pady=(px(16), px(20)))
    tk.Frame(folha, bg=COR_FITA, width=px(110), height=px(18)).place(relx=0.5, y=-px(2), anchor="n")

    tk.Label(
        folha, text="pra assistir ✦", font=(FONTE_MANUSCRITA, -px(26), "bold"),
        fg=COR_TITULO_MANUSCRITO, bg=COR_FOLHA_CHECKLIST
    ).pack(anchor="w", padx=px(22), pady=(px(22), 0))
    tk.Frame(folha, bg=COR_MARCA_TEXTO, height=px(6), width=px(170)).pack(anchor="w", padx=px(26))
    tk.Label(
        folha, text="marque ☐ quando assistir: o título vai direto para o seu diário",
        font=(FONTE_MANUSCRITA, -px(14)), fg=COR_TEXTO_SUAVE, bg=COR_FOLHA_CHECKLIST
    ).pack(anchor="w", padx=px(22), pady=(px(4), px(8)))

    for filme in guardados[:LIMITE_CARDS_GRADE]:
        criar_item_da_checklist(folha, filme, escala, imagens_meus_filmes)

    tk.Frame(folha, bg=COR_FOLHA_CHECKLIST, height=px(16)).pack()

    canvas_rolagem = getattr(scroll_meus_filmes, "_parent_canvas", None)
    if canvas_rolagem is not None:
        canvas_rolagem.yview_moveto(0)


# =========================================================
# CAPA INTERNA — "este diário pertence a..." + estatísticas
# =========================================================
# Os números vêm prontos do usuario.estatisticas_do_diario(); aqui eles viram
# carimbos de papel (os mesmos das notas na janela do filme) e anotações à mão.
LARGURA_LINHA_DO_NOME = 380


def data_por_extenso(data):
    """date(2026, 9, 12) -> '12 de setembro de 2026'"""
    return f"{data.day} de {MESES_EM_PORTUGUES[data.month - 1].lower()} de {data.year}"


def plural(quantidade, singular, plural_da_palavra):
    return f"{quantidade} {singular if quantidade == 1 else plural_da_palavra}"


def formatar_numero_br(valor):
    return f"{valor:,}".replace(",", ".")


def selos_da_capa(numeros):
    """[(título, valor grande, legenda)] dos carimbos da capa."""
    horas = f"≈{formatar_numero_br(numeros['horas'])}h" if numeros["horas_estimadas"] else f"{formatar_numero_br(numeros['horas'])}h"
    if numeros["nota_media"] is None:
        nota, legenda_nota = "–", "ainda sem notas"
    else:
        nota = f"{numeros['nota_media']:.1f}".replace(".", ",")
        legenda_nota = f"de 5 · {plural(numeros['avaliados'], 'nota', 'notas')}"
    return [
        ("FILMES", str(numeros["filmes"]), "vistos"),
        ("SÉRIES", str(numeros["series"]), "vistas"),
        ("NOTA MÉDIA", nota, legenda_nota),
        ("HORAS", horas, "na frente da tela"),
        ("ANOTAÇÕES", str(numeros["anotacoes"]), "escritas"),
    ]


def linhas_anotadas_da_capa(numeros):
    """[(rótulo em vermelho, texto em azul, filme clicável ou None)] das anotações à mão."""
    linhas = []
    if numeros["genero"]:
        genero, quantidade = numeros["genero"]
        linhas.append(("gênero que mais aparece:", f"{genero} ({plural(quantidade, 'título', 'títulos')})", None))
    if numeros["pessoa"]:
        pessoa, quantidade = numeros["pessoa"]
        linhas.append(("diretor (ou criador) que mais aparece:", f"{pessoa} ({quantidade})", None))
    if numeros["mes"]:
        mes, quantidade = numeros["mes"]
        nome_mes = f"{MESES_EM_PORTUGUES[mes.month - 1].lower()} de {mes.year}"
        linhas.append(("mês com mais sessões:", f"{nome_mes} ({plural(quantidade, 'título', 'títulos')})", None))
    if numeros["melhor"]:
        melhor = numeros["melhor"]
        linhas.append((
            "o mais bem avaliado:",
            f"{melhor['filme']['nome']}  {usuario.texto_estrelas(melhor['nota'])}",
            melhor["filme"],
        ))
    if numeros.get("revistos"):
        linhas.append((
            "vi de novo:",
            f"{plural(numeros['revistos'], 'título', 'títulos')} ({numeros['sessoes']} sessões no total) ↻",
            None,
        ))
    if numeros["favoritos"]:
        linhas.append(("favoritos colados:", plural(numeros["favoritos"], "título", "títulos") + " ♥", None))
    if numeros["quero_assistir"]:
        linhas.append(("esperando na lista:", plural(numeros["quero_assistir"], "título", "títulos") + " 📌", None))
    return linhas


def criar_linha_do_nome(folha, escala):
    """O nome escrito à mão. Clicando, vira um campo; Enter (ou sair do campo) salva."""
    def px(valor):
        return int(valor * escala)

    area_nome = tk.Frame(folha, bg=COR_PAPEL)
    area_nome.pack(pady=(px(2), 0))

    def mostrar_nome():
        for widget in area_nome.winfo_children():
            widget.destroy()
        nome = usuario.obter_nome_do_dono()
        rotulo = tk.Label(
            area_nome,
            text=nome or "✎ escreva seu nome aqui",
            font=(FONTE_MANUSCRITA, -px(38 if nome else 22), "bold" if nome else "normal"),
            fg=COR_AZUL_CANETA if nome else COR_TEXTO_SUAVE,
            bg=COR_PAPEL, cursor="hand2"
        )
        rotulo.pack()
        rotulo.bind("<Button-1>", editar_nome)

    def editar_nome(event=None):
        for widget in area_nome.winfo_children():
            widget.destroy()
        campo = tk.Entry(
            area_nome, font=(FONTE_MANUSCRITA, -px(32), "bold"), fg=COR_AZUL_CANETA,
            bg=COR_BILHETE, relief="flat", justify="center", width=22,
            insertbackground=COR_AZUL_CANETA, highlightthickness=1,
            highlightbackground=COR_BORDA_PAPEL, highlightcolor=COR_VERMELHO
        )
        campo.insert(0, usuario.obter_nome_do_dono())
        campo.pack(ipady=px(2))
        campo.focus_set()
        campo.select_range(0, "end")

        def salvar(event=None):
            if campo.winfo_exists():
                usuario.definir_nome_do_dono(campo.get())
            mostrar_nome()

        campo.bind("<Return>", salvar)
        campo.bind("<FocusOut>", salvar)
        campo.bind("<Escape>", lambda event: mostrar_nome())

    mostrar_nome()
    tk.Frame(folha, bg=COR_VERMELHO, height=max(1, px(2)), width=px(LARGURA_LINHA_DO_NOME)).pack(pady=(0, px(4)))


# ---------- Backup do diário (rodapé da Capa) ----------
def texto_do_ultimo_backup():
    ultimo = usuario.ultimo_backup()
    if ultimo is None:
        return "💾 nenhum backup ainda"
    return f"💾 último backup: {ultimo.strftime('%d/%m/%Y às %H:%M')}  ·  automático toda semana"


def abrir_pasta_de_backups(event=None):
    usuario.PASTA_BACKUPS.mkdir(parents=True, exist_ok=True)
    if sys.platform.startswith("win"):
        os.startfile(usuario.PASTA_BACKUPS)   # abre no Explorador de Arquivos
    else:
        webbrowser.open(usuario.PASTA_BACKUPS.as_uri())


def fazer_backup_agora(event=None):
    caminho = usuario.fazer_backup()
    messagebox.showinfo(
        "Backup feito",
        f"Uma cópia do seu diário foi guardada em:\n{caminho}\n\n"
        "Se algo der errado, use  ↺ restaurar  na Capa.",
        parent=janela
    )
    atualizar_meus_filmes(voltar_ao_topo=False)


def abrir_restaurar_backup(event=None):
    """Lista os backups (do mais novo ao mais antigo); cada um pode ser restaurado."""
    backups = usuario.listar_backups()
    if not backups:
        messagebox.showinfo("Restaurar", "Ainda não há nenhum backup guardado.", parent=janela)
        return

    janela_backups = ctk.CTkToplevel(janela)
    janela_backups.title("Restaurar um backup")
    janela_backups.resizable(False, False)
    janela_backups.configure(fg_color=COR_PAPEL)
    janela_backups.transient(janela)
    janela.update_idletasks()
    janela_backups.geometry(f"+{janela.winfo_rootx() + 360}+{janela.winfo_rooty() + 160}")
    janela_backups.after(50, janela_backups.grab_set)

    ctk.CTkLabel(
        janela_backups, text="voltar o diário para qual dia?", font=(FONTE_MANUSCRITA, 22, "bold"),
        text_color=COR_TITULO_MANUSCRITO
    ).pack(padx=24, pady=(18, 2))
    ctk.CTkLabel(
        janela_backups, text="antes de restaurar, o CineAI guarda uma cópia de como está agora",
        font=(FONTE_MANUSCRITA, 14), text_color=COR_TEXTO_SUAVE
    ).pack(padx=24, pady=(0, 10))

    def restaurar(caminho, momento):
        if not messagebox.askyesno(
            "Restaurar backup",
            f"Voltar o diário para como estava em {momento.strftime('%d/%m/%Y às %H:%M')}?\n\n"
            "O que você fez depois disso sai do diário (mas fica guardado num backup novo).",
            parent=janela_backups
        ):
            return
        fechar_edicao_do_diario()
        usuario.restaurar_backup(caminho)
        conversas.recarregar()
        janela_backups.destroy()
        atualizar_lista_conversas()
        ao_mudar_listas()
        messagebox.showinfo("Pronto", "Diário restaurado. ✓", parent=janela)

    lista = ctk.CTkScrollableFrame(janela_backups, width=440, height=260, fg_color=COR_BILHETE)
    lista.pack(padx=20, pady=(0, 16))
    for caminho, momento in backups:
        linha = ctk.CTkFrame(lista, fg_color="transparent")
        linha.pack(fill="x", pady=4)
        ctk.CTkLabel(
            linha, text=momento.strftime("%d/%m/%Y  %H:%M"), font=(FONTE_INTERFACE, 13, "bold"),
            text_color=COR_TEXTO, width=130, anchor="w"
        ).pack(side="left", padx=(6, 6))
        ctk.CTkLabel(
            linha, text=usuario.resumo_do_backup(caminho), font=(FONTE_MANUSCRITA, 14),
            text_color=COR_TEXTO_SECUNDARIO, anchor="w"
        ).pack(side="left")
        ctk.CTkButton(
            linha, text="↺ restaurar", width=90, height=28, corner_radius=4, fg_color=COR_VINHO,
            hover_color=COR_VERMELHO, text_color=COR_TEXTO_CAPA, font=(FONTE_MANUSCRITA, 14, "bold"),
            command=lambda caminho=caminho, momento=momento: restaurar(caminho, momento)
        ).pack(side="right", padx=6)


def criar_area_de_backup(folha, escala):
    """
    Rodapé da Capa: a data do último backup numa linha e, embaixo, os três botões
    grandes (antes ficava tudo numa linha só e o primeiro botão era cortado).
    """
    def px(valor):
        return int(valor * escala)

    tk.Frame(folha, bg=COR_PAUTA_CADERNO, height=1).pack(fill="x", padx=px(70), pady=(0, px(14)))

    area = tk.Frame(folha, bg=COR_PAPEL)
    area.pack(pady=(0, px(28)))
    tk.Label(
        area, text=texto_do_ultimo_backup(), font=(FONTE_MANUSCRITA, -px(17)),
        fg=COR_TEXTO_SECUNDARIO, bg=COR_PAPEL
    ).pack(pady=(0, px(10)))

    linha_botoes = tk.Frame(area, bg=COR_PAPEL)
    linha_botoes.pack()
    for texto, acao, cor in (
        ("💾  fazer backup agora", fazer_backup_agora, COR_VERMELHO),
        ("↺  restaurar um backup…", abrir_restaurar_backup, COR_VINHO),
        ("📂  abrir a pasta", abrir_pasta_de_backups, COR_VINHO),
    ):
        botao = tk.Label(
            linha_botoes, text=texto, font=(FONTE_MANUSCRITA, -px(18), "bold"),
            fg=COR_TEXTO_CAPA, bg=cor, cursor="hand2", padx=px(16), pady=px(7)
        )
        botao.pack(side="left", padx=px(6))
        botao.bind("<Button-1>", acao)


def desenhar_capa():
    limpar_grade(widgets_meus_filmes, imagens_meus_filmes)
    numeros = usuario.estatisticas_do_diario(filmes.filmes)
    escala = escala_da_tela(scroll_meus_filmes)

    def px(valor):
        return int(valor * escala)

    area = tk.Frame(scroll_meus_filmes, bg=COR_FUNDO)
    area.grid(row=0, column=0, columnspan=COLUNAS_CARDS, sticky="ew")
    widgets_meus_filmes.append(area)

    folha = tk.Frame(
        area, bg=COR_PAPEL, highlightbackground=COR_BORDA_PAPEL,
        highlightcolor=COR_BORDA_PAPEL, highlightthickness=1
    )
    folha.pack(fill="x", padx=(px(10), px(60)), pady=(px(16), px(20)))

    # ---------- "este diário pertence a" ----------
    tk.Label(
        folha, text="  ✦ MOVIE JOURNAL ✦  ", font=(FONTE_INTERFACE, -px(11), "bold"),
        fg=COR_TEXTO_CAPA, bg=COR_VERMELHO
    ).pack(pady=(px(26), px(14)))
    tk.Label(
        folha, text="ESTE DIÁRIO PERTENCE A", font=(FONTE_TITULO, -px(17)),
        fg=COR_TEXTO_SECUNDARIO, bg=COR_PAPEL
    ).pack()
    criar_linha_do_nome(folha, escala)

    if numeros["primeira_data"] is not None:
        desde = f"primeira página escrita em {data_por_extenso(numeros['primeira_data'])}"
    else:
        desde = "a primeira página ainda está esperando o primeiro filme..."
    tk.Label(
        folha, text=desde, font=(FONTE_MANUSCRITA, -px(16)), fg=COR_TEXTO_SECUNDARIO, bg=COR_PAPEL
    ).pack(pady=(0, px(18)))

    if numeros["total"] == 0:
        tk.Label(
            folha,
            text="Os números deste diário aparecem aqui quando você marcar\n"
                 "o primeiro título como visto (ou der estrelas a ele). ✎",
            font=(FONTE_MANUSCRITA, -px(17)), fg=COR_TEXTO_SUAVE, bg=COR_PAPEL, justify="center"
        ).pack(pady=(px(6), px(20)))
        criar_area_de_backup(folha, escala)
        return

    # ---------- carimbos com os números ----------
    linha_selos = tk.Frame(folha, bg=COR_PAPEL)
    linha_selos.pack(pady=(0, px(14)))
    for indice, (titulo, valor, legenda) in enumerate(selos_da_capa(numeros)):
        selo = desenhar_selo_de_nota(titulo, valor, legenda, escala, indice, COR_PAPEL)
        imagens_meus_filmes.append(selo)
        tk.Label(linha_selos, image=selo, bg=COR_PAPEL, bd=0).grid(
            row=0, column=indice, padx=px(4), pady=(px((indice % 2) * 8), 0), sticky="n"
        )

    # ---------- anotações à mão, em linhas de caderno ----------
    anotacoes = tk.Frame(folha, bg=COR_PAPEL)
    anotacoes.pack(fill="x", padx=px(70), pady=(px(4), px(30)))
    tk.Frame(anotacoes, bg=COR_PAUTA_CADERNO, height=1).pack(fill="x")

    for rotulo, texto, filme_da_linha in linhas_anotadas_da_capa(numeros):
        linha = tk.Frame(anotacoes, bg=COR_PAPEL)
        linha.pack(fill="x", pady=(px(7), px(5)))
        tk.Label(
            linha, text="✎ " + rotulo, font=(FONTE_MANUSCRITA, -px(17), "bold"),
            fg=COR_VERMELHO, bg=COR_PAPEL
        ).pack(side="left")
        valor = tk.Label(
            linha, text=texto, font=(FONTE_MANUSCRITA, -px(18)), fg=COR_AZUL_CANETA, bg=COR_PAPEL,
            cursor="hand2" if filme_da_linha else ""
        )
        valor.pack(side="left", padx=(px(8), 0))
        if filme_da_linha is not None:
            valor.bind("<Button-1>", lambda event, filme=filme_da_linha: abrir_detalhes(filme))
        tk.Frame(anotacoes, bg=COR_PAUTA_CADERNO, height=1).pack(fill="x")

    criar_botao_retrospectiva(folha, escala)
    criar_area_de_backup(folha, escala)

    canvas_rolagem = getattr(scroll_meus_filmes, "_parent_canvas", None)
    if canvas_rolagem is not None:
        canvas_rolagem.yview_moveto(0)


# =========================================================
# RETROSPECTIVA DO ANO — páginas do diário, uma de cada vez
# =========================================================
# Os números vêm do usuario.retrospectiva_do_ano(). Cada página é uma função
# que desenha UMA ideia (o ano em números, o mês, o gosto, o melhor...).
# Páginas sem dado (ex.: nenhuma anotação no ano) simplesmente não aparecem.
LARGURA_RETROSPECTIVA, ALTURA_RETROSPECTIVA = 820, 640
TAMANHO_POSTER_RETROSPECTIVA = (170, 250)
TAMANHO_POSTER_RETROSPECTIVA_PEQUENO = (125, 184)
LETRAS_DOS_MESES = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]
QUADROS_VIRAR_RETROSPECTIVA = 8
INTERVALO_VIRAR_RETROSPECTIVA_MS = 22


def titulo_manuscrito_da_retrospectiva(pagina, texto, px, cor_fundo=COR_PAPEL):
    """Título à mão, em vermelho, com o marca-texto dourado embaixo."""
    tk.Label(
        pagina, text=texto, font=(FONTE_MANUSCRITA, -px(30), "bold"),
        fg=COR_TITULO_MANUSCRITO, bg=cor_fundo
    ).pack()
    tk.Frame(pagina, bg=COR_MARCA_TEXTO, height=px(6), width=px(220)).pack(pady=(0, px(18)))


def polaroide_da_retrospectiva(container, filme, px, escala, tamanho, imagens, cor_fundo=COR_PAPEL):
    """Polaroide torta do filme (clicável: abre a página dele)."""
    foto = ImageTk.PhotoImage(desenhar_recorte(filme, escala, cor_fundo, tamanho, modo="cartao"))
    imagens.append(foto)
    rotulo = tk.Label(container, image=foto, bg=cor_fundo, bd=0, cursor="hand2")
    rotulo.bind("<Button-1>", lambda event: abrir_detalhes(filme))
    return rotulo


def pagina_capa_da_retrospectiva(pagina, numeros, px, escala, imagens):
    pagina.configure(bg=COR_MENU)
    tk.Label(
        pagina, text="  ✦ RETROSPECTIVA ✦  ", font=(FONTE_INTERFACE, -px(13), "bold"),
        fg=COR_VERMELHO, bg=COR_TEXTO_CAPA
    ).pack(pady=(0, px(16)))
    tk.Label(
        pagina, text=str(numeros["ano"]), font=(FONTE_TITULO, -px(130)),
        fg=COR_TEXTO_CAPA, bg=COR_MENU
    ).pack()
    nome = usuario.obter_nome_do_dono()
    tk.Label(
        pagina, text=f"o ano de {nome} no cinema" if nome else "o seu ano no cinema",
        font=(FONTE_MANUSCRITA, -px(30), "bold"), fg=COR_DOURADO_CLARO, bg=COR_MENU
    ).pack(pady=(px(4), px(10)))
    tk.Label(
        pagina, text=f"{plural(numeros['sessoes'], 'página nova', 'páginas novas')} no diário",
        font=(FONTE_MANUSCRITA, -px(19)), fg=COR_TEXTO_CAPA, bg=COR_MENU
    ).pack()
    tk.Label(
        pagina, text="vire a página  ›", font=(FONTE_MANUSCRITA, -px(17)),
        fg=COR_DOURADO_CLARO, bg=COR_MENU
    ).pack(pady=(px(60), 0))


def selos_da_retrospectiva(numeros):
    horas = ("≈" if numeros["horas_estimadas"] else "") + f"{formatar_numero_br(numeros['horas'])}h"
    if numeros["nota_media"] is None:
        nota, legenda_nota = "–", "sem notas"
    else:
        nota, legenda_nota = f"{numeros['nota_media']:.1f}".replace(".", ","), "de 5"
    return [
        ("TÍTULOS", str(numeros["titulos"]), "no ano"),
        ("FILMES", str(numeros["filmes"]), "vistos"),
        ("SÉRIES", str(numeros["series"]), "vistas"),
        ("HORAS", horas, "de tela"),
        ("NOTA MÉDIA", nota, legenda_nota),
    ]


def pagina_numeros_da_retrospectiva(pagina, numeros, px, escala, imagens):
    titulo_manuscrito_da_retrospectiva(pagina, "o ano em números", px)
    linha = tk.Frame(pagina, bg=COR_PAPEL)
    linha.pack(pady=(px(10), px(30)))
    for indice, (titulo, valor, legenda) in enumerate(selos_da_retrospectiva(numeros)):
        selo = desenhar_selo_de_nota(titulo, valor, legenda, escala * 1.15, indice, COR_PAPEL)
        imagens.append(selo)
        tk.Label(linha, image=selo, bg=COR_PAPEL, bd=0).grid(
            row=0, column=indice, padx=px(3), pady=(px((indice % 2) * 10), 0), sticky="n"
        )

    frases = [f"✎ {plural(numeros['novos'], 'título visto', 'títulos vistos')} pela primeira vez"]
    if numeros["revistos"]:
        frases.append(f"↻ {plural(len(numeros['revistos']), 'reencontro', 'reencontros')} com velhos conhecidos")
    if numeros["anotacoes"]:
        frases.append(f"✍ {plural(numeros['anotacoes'], 'anotação escrita', 'anotações escritas')}")
    for frase in frases:
        tk.Label(
            pagina, text=frase, font=(FONTE_MANUSCRITA, -px(21)), fg=COR_AZUL_CANETA, bg=COR_PAPEL
        ).pack(pady=px(4))


def pagina_mes_da_retrospectiva(pagina, numeros, px, escala, imagens):
    numero_mes, quantidade = numeros["mes"]
    titulo_manuscrito_da_retrospectiva(pagina, "o mês mais cinéfilo foi...", px)
    tk.Label(
        pagina, text=MESES_EM_PORTUGUES[numero_mes - 1], font=(FONTE_TITULO, -px(64)),
        fg=COR_TEXTO, bg=COR_PAPEL
    ).pack()
    tk.Label(
        pagina, text=f"{plural(quantidade, 'sessão', 'sessões')} naquele mês",
        font=(FONTE_MANUSCRITA, -px(20)), fg=COR_AZUL_CANETA, bg=COR_PAPEL
    ).pack(pady=(0, px(16)))

    # Barrinhas dos 12 meses, como um gráfico rabiscado no caderno
    largura_barra, espaco, altura_maxima = px(30), px(14), px(150)
    largura_total = 12 * largura_barra + 11 * espaco
    grafico = tk.Canvas(
        pagina, width=largura_total, height=altura_maxima + px(30), bg=COR_PAPEL, highlightthickness=0
    )
    grafico.pack()
    maior = max(numeros["meses"]) or 1
    base = altura_maxima
    grafico.create_line(0, base, largura_total, base, fill=COR_PAUTA_CADERNO, width=max(1, px(2)))
    for indice, contagem in enumerate(numeros["meses"]):
        x = indice * (largura_barra + espaco)
        altura = int(altura_maxima * contagem / maior)
        cor = COR_VERMELHO if indice == numero_mes - 1 else COR_PAPEL_ESCURO
        if altura:
            grafico.create_rectangle(x, base - altura, x + largura_barra, base, fill=cor, outline="")
            grafico.create_text(
                x + largura_barra / 2, base - altura - px(10), text=str(contagem),
                font=(FONTE_MANUSCRITA, -px(14)), fill=COR_AZUL_CANETA
            )
        grafico.create_text(
            x + largura_barra / 2, base + px(15), text=LETRAS_DOS_MESES[indice],
            font=(FONTE_TITULO, -px(14)), fill=COR_TEXTO_SECUNDARIO
        )

    if numeros["dia"]:
        dia, quantidade_no_dia = numeros["dia"]
        tk.Label(
            pagina,
            text=f"✎ dia mais cheio: {data_por_extenso(dia)} ({plural(quantidade_no_dia, 'título', 'títulos')} de uma vez!)",
            font=(FONTE_MANUSCRITA, -px(18)), fg=COR_VERMELHO, bg=COR_PAPEL
        ).pack(pady=(px(16), 0))


def pagina_gosto_da_retrospectiva(pagina, numeros, px, escala, imagens):
    titulo_manuscrito_da_retrospectiva(pagina, f"o seu gosto em {numeros['ano']}", px)
    for posicao, (genero, quantidade) in enumerate(numeros["generos"], start=1):
        linha = tk.Frame(pagina, bg=COR_PAPEL)
        linha.pack(pady=px(5))
        tk.Label(
            linha, text=f"{posicao}º", font=(FONTE_TITULO, -px(34 if posicao == 1 else 26)),
            fg=COR_VERMELHO, bg=COR_PAPEL
        ).pack(side="left", padx=(0, px(12)))
        tk.Label(
            linha, text=genero, font=(FONTE_MANUSCRITA, -px(42 if posicao == 1 else 30), "bold"),
            fg=COR_AZUL_CANETA, bg=COR_MARCA_TEXTO if posicao == 1 else COR_PAPEL, padx=px(6)
        ).pack(side="left")
        tk.Label(
            linha, text=f"  {plural(quantidade, 'título', 'títulos')}", font=(FONTE_MANUSCRITA, -px(17)),
            fg=COR_TEXTO_SECUNDARIO, bg=COR_PAPEL
        ).pack(side="left")

    if numeros["pessoa"]:
        pessoa, quantidade = numeros["pessoa"]
        tk.Frame(pagina, bg=COR_PAUTA_CADERNO, height=1, width=px(420)).pack(pady=(px(26), px(14)))
        tk.Label(
            pagina, text="DIRETOR (OU CRIADOR) DO ANO", font=(FONTE_TITULO, -px(16)),
            fg=COR_TEXTO_SECUNDARIO, bg=COR_PAPEL
        ).pack()
        tk.Label(
            pagina, text=f"{pessoa}", font=(FONTE_MANUSCRITA, -px(34), "bold"),
            fg=COR_VERMELHO, bg=COR_PAPEL
        ).pack()
        tk.Label(
            pagina, text=f"{plural(quantidade, 'título', 'títulos')} no seu ano",
            font=(FONTE_MANUSCRITA, -px(17)), fg=COR_AZUL_CANETA, bg=COR_PAPEL
        ).pack()


def pagina_melhor_da_retrospectiva(pagina, numeros, px, escala, imagens):
    melhor = numeros["melhor"]
    titulo_manuscrito_da_retrospectiva(pagina, "a nota mais alta do ano", px)
    polaroide_da_retrospectiva(
        pagina, melhor["filme"], px, escala, TAMANHO_POSTER_RETROSPECTIVA, imagens
    ).pack()
    tk.Label(
        pagina, text=melhor["filme"]["nome"], font=(FONTE_TITULO, -px(28)),
        fg=COR_TEXTO, bg=COR_PAPEL, wraplength=px(600)
    ).pack(pady=(px(10), 0))
    tk.Label(
        pagina, text=usuario.texto_estrelas(melhor["nota"]), font=(FONTE_SIMBOLOS, -px(24)),
        fg=COR_ESTRELA_ACESA, bg=COR_PAPEL
    ).pack()


def pagina_anotacao_da_retrospectiva(pagina, numeros, px, escala, imagens):
    escolhida = numeros["anotacao"]
    titulo_manuscrito_da_retrospectiva(pagina, "nas suas palavras", px)
    sombra = tk.Frame(pagina, bg=COR_SOMBRA_PAPEL)
    sombra.pack(padx=px(90), pady=(px(10), px(14)), fill="x")
    papel = tk.Frame(sombra, bg=COR_BILHETE, highlightbackground=COR_BORDA_PAPEL, highlightthickness=1)
    papel.pack(fill="x", padx=(0, px(4)), pady=(0, px(4)))
    tk.Frame(papel, bg=COR_FITA, width=px(90), height=px(16)).place(relx=0.5, y=0, anchor="n")
    tk.Label(
        papel, text=f"“{escolhida['anotacao'].strip()}”", font=(FONTE_MANUSCRITA, -px(25)),
        fg=COR_AZUL_CANETA, bg=COR_BILHETE, wraplength=px(520), justify="center"
    ).pack(padx=px(26), pady=(px(34), px(28)))

    data = escolhida["data"]
    sobre = f"— sobre {escolhida['filme']['nome']}"
    if data is not None:
        sobre += f", {data.day:02d}/{data.month:02d}"
    rotulo = tk.Label(
        pagina, text=sobre, font=(FONTE_MANUSCRITA, -px(19), "bold"), fg=COR_VERMELHO,
        bg=COR_PAPEL, cursor="hand2"
    )
    rotulo.pack()
    rotulo.bind("<Button-1>", lambda event: abrir_detalhes(escolhida["filme"]))


def pagina_comeco_e_fim_da_retrospectiva(pagina, numeros, px, escala, imagens):
    titulo_manuscrito_da_retrospectiva(pagina, "começo e fim", px)
    linha = tk.Frame(pagina, bg=COR_PAPEL)
    linha.pack()
    for coluna, (rotulo, entrada) in enumerate((
        ("abriu o ano", numeros["primeira"]),
        ("a última página", numeros["ultima"]),
    )):
        bloco = tk.Frame(linha, bg=COR_PAPEL)
        bloco.grid(row=0, column=coluna, padx=px(40), sticky="n")
        tk.Label(
            bloco, text=rotulo, font=(FONTE_MANUSCRITA, -px(21), "bold"), fg=COR_VERMELHO, bg=COR_PAPEL
        ).pack(pady=(0, px(6)))
        polaroide_da_retrospectiva(
            bloco, entrada["filme"], px, escala, TAMANHO_POSTER_RETROSPECTIVA_PEQUENO, imagens
        ).pack()
        tk.Label(
            bloco, text=entrada["filme"]["nome"], font=(FONTE_TITULO, -px(18)), fg=COR_TEXTO,
            bg=COR_PAPEL, wraplength=px(230)
        ).pack(pady=(px(6), 0))
        tk.Label(
            bloco, text=data_por_extenso(entrada["data"]), font=(FONTE_MANUSCRITA, -px(16)),
            fg=COR_AZUL_CANETA, bg=COR_PAPEL
        ).pack()


def pagina_revistos_da_retrospectiva(pagina, numeros, px, escala, imagens):
    titulo_manuscrito_da_retrospectiva(pagina, "vistos de novo ↻", px)
    tk.Label(
        pagina, text="tem filme que a gente não cansa...", font=(FONTE_MANUSCRITA, -px(18)),
        fg=COR_TEXTO_SECUNDARIO, bg=COR_PAPEL
    ).pack(pady=(0, px(14)))
    lista = tk.Frame(pagina, bg=COR_PAPEL)
    lista.pack(fill="x", padx=px(150))
    tk.Frame(lista, bg=COR_PAUTA_CADERNO, height=1).pack(fill="x")
    for entrada in numeros["revistos"][:8]:
        linha = tk.Frame(lista, bg=COR_PAPEL)
        linha.pack(fill="x", pady=(px(6), px(4)))
        tk.Label(
            linha, text=f"{entrada['vez']}ª VEZ", font=(FONTE_TITULO, -px(15)),
            fg=COR_TEXTO_CAPA, bg=COR_VERMELHO, padx=px(6)
        ).pack(side="left")
        nome = tk.Label(
            linha, text=entrada["filme"]["nome"], font=(FONTE_MANUSCRITA, -px(21)),
            fg=COR_AZUL_CANETA, bg=COR_PAPEL, cursor="hand2"
        )
        nome.pack(side="left", padx=(px(10), 0))
        nome.bind("<Button-1>", lambda event, filme=entrada["filme"]: abrir_detalhes(filme))
        tk.Label(
            linha, text=f"{entrada['data'].day:02d}/{entrada['data'].month:02d}",
            font=(FONTE_MANUSCRITA, -px(16)), fg=COR_TEXTO_SUAVE, bg=COR_PAPEL
        ).pack(side="right")
        tk.Frame(lista, bg=COR_PAUTA_CADERNO, height=1).pack(fill="x")
    if len(numeros["revistos"]) > 8:
        tk.Label(
            pagina, text=f"... e mais {len(numeros['revistos']) - 8}", font=(FONTE_MANUSCRITA, -px(16)),
            fg=COR_TEXTO_SUAVE, bg=COR_PAPEL
        ).pack(pady=px(6))


def pagina_fim_da_retrospectiva(pagina, numeros, px, escala, imagens):
    pagina.configure(bg=COR_PELICULA)
    ano = numeros["ano"]
    tk.Label(
        pagina, text="✦  FIM  ✦", font=(FONTE_TITULO, -px(70)), fg=COR_DOURADO_CLARO, bg=COR_PELICULA
    ).pack(pady=(0, px(10)))
    if ano == date.today().year:
        frase = f"...mas {ano} ainda não acabou. Ainda dá tempo de mais umas páginas!"
    else:
        frase = f"foi um bom ano, {ano}. Que venham os próximos filmes!"
    tk.Label(
        pagina, text=frase, font=(FONTE_MANUSCRITA, -px(23)), fg=COR_TEXTO_CAPA,
        bg=COR_PELICULA, wraplength=px(600), justify="center"
    ).pack(pady=(0, px(16)))
    tk.Label(
        pagina, text=f"{plural(numeros['sessoes'], 'sessão', 'sessões')}  ·  "
                     f"{plural(numeros['titulos'], 'título', 'títulos')}  ·  "
                     f"{plural(numeros['anotacoes'], 'anotação', 'anotações')}",
        font=(FONTE_MANUSCRITA, -px(18)), fg=COR_DOURADO_CLARO, bg=COR_PELICULA
    ).pack()


def paginas_da_retrospectiva(numeros):
    """As páginas que têm o que mostrar, em ordem."""
    paginas = [pagina_capa_da_retrospectiva, pagina_numeros_da_retrospectiva]
    if numeros["mes"]:
        paginas.append(pagina_mes_da_retrospectiva)
    if numeros["generos"]:
        paginas.append(pagina_gosto_da_retrospectiva)
    if numeros["melhor"]:
        paginas.append(pagina_melhor_da_retrospectiva)
    if numeros["anotacao"]:
        paginas.append(pagina_anotacao_da_retrospectiva)
    if numeros["titulos"] > 1 and numeros["primeira"]["filme"] is not numeros["ultima"]["filme"]:
        paginas.append(pagina_comeco_e_fim_da_retrospectiva)
    if numeros["revistos"]:
        paginas.append(pagina_revistos_da_retrospectiva)
    paginas.append(pagina_fim_da_retrospectiva)
    return paginas


def abrir_retrospectiva(ano=None):
    """Janela com as páginas da retrospectiva. ‹ › (ou as setas do teclado) viram a página."""
    anos = usuario.anos_do_diario(filmes.filmes)
    if not anos:
        messagebox.showinfo(
            "Retrospectiva",
            "O diário ainda não tem nenhuma sessão com data.\nMarque alguns títulos como vistos primeiro. ✎",
            parent=janela
        )
        return
    if ano not in anos:
        ano = usuario.ano_padrao_da_retrospectiva(filmes.filmes)

    janela_retro = ctk.CTkToplevel(janela)
    janela_retro.title("Retrospectiva do ano")
    janela_retro.resizable(False, False)
    janela_retro.configure(fg_color=COR_MESA)
    janela_retro.transient(janela)
    janela.update_idletasks()
    janela_retro.geometry(
        f"{LARGURA_RETROSPECTIVA}x{ALTURA_RETROSPECTIVA}"
        f"+{janela.winfo_rootx() + 120}+{janela.winfo_rooty() + 40}"
    )
    janela_retro.after(50, janela_retro.focus_force)

    escala = escala_da_tela(janela_retro)

    def px(valor):
        return max(1, int(valor * escala))

    estado = {"ano": ano, "numeros": None, "paginas": [], "pagina": 0, "imagens": []}

    # ---------- topo: título + escolha do ano ----------
    topo = tk.Frame(janela_retro, bg=COR_MESA)
    topo.pack(fill="x", padx=px(24), pady=(px(12), px(6)))
    tk.Label(
        topo, text="📖 MEU ANO NO CINEMA", font=(FONTE_TITULO, -px(20)), fg=COR_VINHO, bg=COR_MESA
    ).pack(side="left")
    seletor_ano = ctk.CTkOptionMenu(
        topo, values=[str(ano_do_diario) for ano_do_diario in anos], width=90, height=28,
        fg_color=COR_VINHO, button_color=COR_VERMELHO, button_hover_color=COR_VERMELHO_HOVER,
        dropdown_fg_color=COR_PAPEL, dropdown_text_color=COR_TEXTO, text_color=COR_TEXTO_CAPA,
        font=(FONTE_INTERFACE, 13, "bold"), command=lambda valor: trocar_ano(int(valor))
    )
    seletor_ano.set(str(ano))
    seletor_ano.pack(side="right")
    tk.Label(topo, text="ano:", font=(FONTE_MANUSCRITA, -px(17)), fg=COR_VINHO, bg=COR_MESA).pack(
        side="right", padx=(0, px(6))
    )

    # ---------- a folha ----------
    moldura = tk.Frame(janela_retro, bg=COR_BORDA_PAPEL)
    moldura.pack(fill="both", expand=True, padx=px(24))
    pagina = tk.Frame(moldura, bg=COR_PAPEL)
    pagina.pack(fill="both", expand=True, padx=1, pady=1)

    # ---------- rodapé: ‹ bolinhas › ----------
    rodape = tk.Frame(janela_retro, bg=COR_MESA)
    rodape.pack(fill="x", padx=px(24), pady=px(10))
    botao_anterior = tk.Label(
        rodape, text="‹  anterior", font=(FONTE_MANUSCRITA, -px(19), "bold"),
        fg=COR_TEXTO_CAPA, bg=COR_VINHO, padx=px(14), pady=px(4), cursor="hand2"
    )
    botao_anterior.pack(side="left")
    botao_proxima = tk.Label(
        rodape, text="próxima  ›", font=(FONTE_MANUSCRITA, -px(19), "bold"),
        fg=COR_TEXTO_CAPA, bg=COR_VERMELHO, padx=px(14), pady=px(4), cursor="hand2"
    )
    botao_proxima.pack(side="right")
    bolinhas = tk.Label(rodape, text="", font=(FONTE_SIMBOLOS, -px(14)), fg=COR_VINHO, bg=COR_MESA)
    bolinhas.pack()

    def desenhar_pagina():
        for widget in pagina.winfo_children():
            widget.destroy()
        estado["imagens"].clear()
        # O conteúdo fica no meio da folha (em altura); a folha pega a cor que a página escolher.
        conteudo = tk.Frame(pagina, bg=COR_PAPEL)
        conteudo.place(relx=0.5, rely=0.5, relwidth=1.0, anchor="center")
        funcao = estado["paginas"][estado["pagina"]]
        funcao(conteudo, estado["numeros"], px, escala, estado["imagens"])
        pagina.configure(bg=conteudo.cget("bg"))

        total = len(estado["paginas"])
        bolinhas.configure(text="  ".join(
            "●" if indice == estado["pagina"] else "○" for indice in range(total)
        ))
        primeira, ultima = estado["pagina"] == 0, estado["pagina"] == total - 1
        botao_anterior.configure(fg=COR_TEXTO_SUAVE if primeira else COR_TEXTO_CAPA,
                                 bg=COR_PAPEL_ESCURO if primeira else COR_VINHO)
        botao_proxima.configure(text="fechar  ✕" if ultima else "próxima  ›")

    def virar(direcao):
        """Uma folha cobre a página e corre para o lado, como no caderno."""
        janela_retro.update_idletasks()
        largura, altura = pagina.winfo_width(), pagina.winfo_height()
        if largura < 10 or altura < 10:
            return
        folha = tk.Frame(moldura, bg=COR_PAPEL_ESCURO, bd=0, highlightthickness=0)
        folha.place(x=1, y=1, width=largura, height=altura)
        folha.lift()

        def passo(numero):
            if not folha.winfo_exists():
                return
            progresso = numero / QUADROS_VIRAR_RETROSPECTIVA
            if numero >= QUADROS_VIRAR_RETROSPECTIVA:
                folha.destroy()
                return
            restante = max(1, int(largura * (1 - (1 - (1 - progresso) ** 3))))
            x = 1 if direcao > 0 else 1 + largura - restante
            folha.place_configure(x=x, width=restante)
            janela_retro.after(INTERVALO_VIRAR_RETROSPECTIVA_MS, lambda: passo(numero + 1))

        passo(0)

    def ir_para(indice, direcao):
        if not 0 <= indice < len(estado["paginas"]):
            return
        estado["pagina"] = indice
        desenhar_pagina()
        virar(direcao)

    def proxima(event=None):
        if estado["pagina"] == len(estado["paginas"]) - 1:
            janela_retro.destroy()
            return
        ir_para(estado["pagina"] + 1, 1)

    def anterior(event=None):
        ir_para(estado["pagina"] - 1, -1)

    def trocar_ano(novo_ano):
        estado["ano"] = novo_ano
        estado["numeros"] = usuario.retrospectiva_do_ano(filmes.filmes, novo_ano)
        estado["paginas"] = paginas_da_retrospectiva(estado["numeros"])
        estado["pagina"] = 0
        desenhar_pagina()

    botao_anterior.bind("<Button-1>", anterior)
    botao_proxima.bind("<Button-1>", proxima)
    janela_retro.bind("<Right>", proxima)
    janela_retro.bind("<Left>", anterior)
    janela_retro.bind("<Escape>", lambda event: janela_retro.destroy())

    trocar_ano(ano)
    return janela_retro


def criar_botao_retrospectiva(folha, escala):
    """Botões grandes na Capa: a retrospectiva do ano (dourado) e o diário em PDF."""
    def px(valor):
        return int(valor * escala)

    ano = usuario.ano_padrao_da_retrospectiva(filmes.filmes)
    if ano is None:
        return
    linha = tk.Frame(folha, bg=COR_PAPEL)
    linha.pack(pady=(0, px(28)))
    botao = tk.Label(
        linha, text=f"✨  minha retrospectiva de {ano}  ›", font=(FONTE_MANUSCRITA, -px(22), "bold"),
        fg=COR_TEXTO, bg=COR_DOURADO_CLARO, cursor="hand2", padx=px(22), pady=px(9),
        highlightbackground=COR_DOURADO, highlightthickness=max(1, px(2))
    )
    botao.pack(side="left", padx=px(8))
    botao.bind("<Button-1>", lambda event: abrir_retrospectiva(ano))

    botao_pdf = tk.Label(
        linha, text="📄  diário em PDF", font=(FONTE_MANUSCRITA, -px(22), "bold"),
        fg=COR_TEXTO_CAPA, bg=COR_VINHO, cursor="hand2", padx=px(22), pady=px(9),
        highlightbackground=COR_VINHO, highlightthickness=max(1, px(2))
    )
    botao_pdf.pack(side="left", padx=px(8))
    botao_pdf.bind("<Button-1>", abrir_exportar_pdf)


# ---------- Diário em PDF ----------
OPCAO_PDF_TUDO = "o diário inteiro"


def abrir_arquivo_no_computador(caminho):
    """Abre o PDF no leitor padrão (no Windows, o mesmo que dar dois cliques)."""
    if sys.platform.startswith("win"):
        os.startfile(caminho)
    else:
        webbrowser.open(caminho.as_uri())


def abrir_exportar_pdf(event=None):
    """Janelinha: escolher o diário inteiro ou um ano, e exportar."""
    anos = usuario.anos_do_diario(filmes.filmes)
    if not anos:
        messagebox.showinfo("Diário em PDF", "O diário ainda está em branco. ✎", parent=janela)
        return

    janela_pdf = ctk.CTkToplevel(janela)
    janela_pdf.title("Diário em PDF")
    janela_pdf.resizable(False, False)
    janela_pdf.configure(fg_color=COR_PAPEL)
    janela_pdf.transient(janela)
    janela.update_idletasks()
    janela_pdf.geometry(f"+{janela.winfo_rootx() + 420}+{janela.winfo_rooty() + 200}")
    janela_pdf.after(50, janela_pdf.grab_set)

    ctk.CTkLabel(
        janela_pdf, text="imprimir o diário 📄", font=(FONTE_MANUSCRITA, 24, "bold"),
        text_color=COR_TITULO_MANUSCRITO
    ).pack(padx=34, pady=(20, 2))
    ctk.CTkLabel(
        janela_pdf, text="capa, números e cada entrada com pôster, estrelas e anotação",
        font=(FONTE_MANUSCRITA, 15), text_color=COR_TEXTO_SUAVE
    ).pack(padx=34, pady=(0, 14))

    escolha = ctk.CTkSegmentedButton(
        janela_pdf, values=[OPCAO_PDF_TUDO] + [str(ano) for ano in anos],
        font=(FONTE_MANUSCRITA, 16, "bold"), fg_color=COR_VINHO,
        selected_color=COR_VERMELHO, selected_hover_color=COR_VERMELHO_HOVER,
        unselected_color=COR_VINHO, unselected_hover_color=COR_VERMELHO_HOVER,
        text_color=COR_TEXTO_CAPA
    )
    escolha.set(OPCAO_PDF_TUDO)
    escolha.pack(padx=34, pady=(0, 16))

    aviso = ctk.CTkLabel(janela_pdf, text="", font=(FONTE_MANUSCRITA, 15), text_color=COR_AZUL_CANETA)
    aviso.pack(pady=(0, 4))

    def exportar():
        ano = None if escolha.get() == OPCAO_PDF_TUDO else int(escolha.get())
        botao_exportar.configure(state="disabled", text="desenhando as páginas...")

        def ao_avancar(paginas_prontas):
            aviso.configure(text=f"✎ {plural(paginas_prontas, 'página pronta', 'páginas prontas')}...")
            janela_pdf.update()

        try:
            caminho = diario_pdf.exportar_diario_pdf(filmes.filmes, ano=ano, ao_avancar=ao_avancar)
        except (ValueError, OSError) as erro:
            botao_exportar.configure(state="normal", text="📄  exportar")
            aviso.configure(text=str(erro), text_color=COR_VERMELHO)
            return

        janela_pdf.destroy()
        abrir_arquivo_no_computador(caminho)
        messagebox.showinfo(
            "Diário em PDF",
            f"Pronto! O PDF foi guardado em:\n{caminho}\n\n"
            "Ele está na pasta dados/exportados do CineAI.",
            parent=janela
        )

    botao_exportar = ctk.CTkButton(
        janela_pdf, text="📄  exportar", height=38, corner_radius=4, fg_color=COR_VERMELHO,
        hover_color=COR_VERMELHO_HOVER, text_color=COR_TEXTO_CAPA, font=(FONTE_MANUSCRITA, 18, "bold"),
        command=exportar
    )
    botao_exportar.pack(padx=34, pady=(4, 8), fill="x")

    link_pasta = ctk.CTkLabel(
        janela_pdf, text="📂 abrir a pasta dos PDFs", font=(FONTE_MANUSCRITA, 15),
        text_color=COR_VINHO, cursor="hand2"
    )
    link_pasta.pack(pady=(0, 18))

    def abrir_pasta(event=None):
        diario_pdf.PASTA_EXPORTADOS.mkdir(parents=True, exist_ok=True)
        abrir_arquivo_no_computador(diario_pdf.PASTA_EXPORTADOS)

    link_pasta.bind("<Button-1>", abrir_pasta)


TEXTO_DIARIO_VAZIO = (
    "Este diário ainda está em branco...\n\n"
    "marque um filme como visto (ou dê estrelas a ele)\n"
    "e a primeira entrada aparece aqui, com a data de hoje."
)
TEXTO_QUERO_VER_VAZIO = (
    "Nenhum título preso aqui ainda...\n\n"
    "abra um filme e toque em  📌 quero ver,\n"
    "ou diga ao CineAI: \"salva esse pra depois\"."
)
TEXTO_FAVORITOS_VAZIO = (
    "Ainda não colei nenhum favorito aqui...\n\n"
    "quando um filme te conquistar, abra a página dele\n"
    "e toque em  ♡ favoritar."
)


def atualizar_contador_meus_filmes():
    quantidade_favoritos = len(usuario.filmes_da_lista("favoritos", filmes.filmes))
    quantidade_assistidos = len(usuario.filmes_da_lista("assistidos", filmes.filmes))
    quantidade_anotacoes = len(usuario.dados_usuario.get("anotacoes", {}))
    quantidade_quero_ver = len(usuario.filmes_da_lista("quero_assistir", filmes.filmes))

    contador_meus_filmes.configure(
        text=(
            f"✎ {quantidade_assistidos} entradas   ❤ {quantidade_favoritos} favoritos   "
            f"📌 {quantidade_quero_ver} pra ver   ✍ {quantidade_anotacoes} anotações"
        )
    )


def atualizar_meus_filmes(voltar_ao_topo=True):
    atualizar_contador_meus_filmes()

    aba_diario_aberta = seletor_aba.get() == ABA_DIARIO

    if aba_diario_aberta:
        seletor_ordem.grid(row=0, column=1, sticky="w", padx=(15, 0))
    else:
        seletor_ordem.grid_remove()

    # Só redesenha se a página estiver aberta (evita trabalho à toa).
    if not pagina_meus_filmes.winfo_ismapped() and widgets_meus_filmes:
        return

    if aba_diario_aberta:
        desenhar_diario(voltar_ao_topo)
        return

    fechar_edicao_do_diario()

    if seletor_aba.get() == ABA_CAPA:
        desenhar_capa()
        return

    if seletor_aba.get() == ABA_QUERO_VER:
        desenhar_quero_assistir()
        return
    preencher_grade(
        scroll_meus_filmes,
        usuario.filmes_da_lista("favoritos", filmes.filmes),
        widgets_meus_filmes,
        imagens_meus_filmes,
        TEXTO_FAVORITOS_VAZIO
    )


# =========================================================
# PÁGINA MEU PERFIL (gosto + recomendações "Para você")
# =========================================================
QUANTIDADE_GENEROS_NO_PERFIL = 5
QUANTIDADE_PARA_VOCE = 24

criar_cabecalho_pagina(
    pagina_perfil,
    "Meu perfil",
    "o que o CineAI aprendeu com as suas estrelas, favoritos e filmes vistos"
)

# A página inteira rola junto (resumo + "Para você"). Antes só a grade rolava,
# e com o resumo grande ela ficava espremida numa faixa pequena embaixo.
pagina_perfil.grid_rowconfigure(3, weight=0)
pagina_perfil.grid_rowconfigure(1, weight=1)

rolagem_perfil = ctk.CTkScrollableFrame(
    pagina_perfil,
    corner_radius=0,
    fg_color=COR_FUNDO,
    scrollbar_button_color=COR_ROLAGEM,
    scrollbar_button_hover_color=COR_ROLAGEM_HOVER
)
rolagem_perfil.grid(row=1, column=0, sticky="nsew", padx=(32, 20), pady=(0, 16))
rolagem_perfil.grid_columnconfigure(0, weight=1)

# Parte 1: resumo do gosto (gêneros à esquerda, pessoas à direita)
area_resumo_perfil = ctk.CTkFrame(
    rolagem_perfil,
    fg_color=COR_PAPEL,
    corner_radius=4,
    border_width=1,
    border_color=COR_BORDA_PAPEL
)
area_resumo_perfil.grid(row=0, column=0, sticky="ew", padx=(10, 14), pady=(2, 12))
area_resumo_perfil.grid_columnconfigure(0, weight=3, uniform="resumo")
area_resumo_perfil.grid_columnconfigure(1, weight=2, uniform="resumo")

# Parte 2: "o que o seu diário diz sobre você" (retrato escrito pela IA)
area_retrato = tk.Frame(
    rolagem_perfil, bg=COR_PAPEL, highlightbackground=COR_BORDA_PAPEL, highlightthickness=1
)
area_retrato.grid(row=1, column=0, sticky="ew", padx=(10, 14), pady=(0, 14))

# Parte 3: título da grade
cabecalho_para_voce = criar_titulo_secao(rolagem_perfil, "✦  PARA VOCÊ")
cabecalho_para_voce.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 4))

# Parte 4: grade de filmes recomendados (sem rolagem própria: rola com a página)
scroll_para_voce = tk.Frame(rolagem_perfil, bg=COR_FUNDO)
scroll_para_voce.grid(row=3, column=0, sticky="ew")
for coluna_grade in range(COLUNAS_CARDS):
    scroll_para_voce.grid_columnconfigure(coluna_grade, weight=1, uniform="grade")

widgets_resumo_perfil = []
widgets_para_voce = []
imagens_para_voce = []


def formatar_afinidade(valor):
    return f"{valor:+.1f}".replace(".", ",")


# Meu perfil no estilo do diário: em vez de barras de painel, anotações à mão.
#   gêneros   -> escritos em caneta azul, com uma passada de marca-texto do
#                tamanho do seu gosto (quanto mais curte, maior a passada)
#   pessoas   -> etiquetas de papel coladas (diretores e atores)
#   evitados  -> riscados à mão ("menos a sua praia")
LARGURA_MAXIMA_MARCA_TEXTO = 260
CORES_ETIQUETA_PESSOA = ["#FFFDF7", "#F3E6C8", "#FBF4E3"]
ETIQUETAS_POR_LINHA = 2


def criar_linha_genero(container, item, maior_afinidade, escala):
    def px(valor):
        return int(valor * escala)

    linha = tk.Frame(container, bg=COR_PAPEL)
    linha.pack(fill="x", padx=px(24), pady=(px(2), px(4)))

    tk.Label(
        linha, text=item["nome"], font=(FONTE_MANUSCRITA, -px(21), "bold"),
        fg=COR_AZUL_CANETA, bg=COR_PAPEL
    ).pack(side="left")
    quantidade = f'{item["quantidade"]} título{"s" if item["quantidade"] > 1 else ""}'
    tk.Label(
        linha, text=f"  ·  {quantidade}  ({formatar_afinidade(item['afinidade'])})",
        font=(FONTE_MANUSCRITA, -px(14)), fg=COR_TEXTO_SUAVE, bg=COR_PAPEL
    ).pack(side="left", pady=(px(4), 0))

    proporcao = item["afinidade"] / maior_afinidade if maior_afinidade > 0 else 0
    tk.Frame(
        container, bg=COR_MARCA_TEXTO, height=px(7),
        width=max(px(24), int(px(LARGURA_MAXIMA_MARCA_TEXTO) * proporcao))
    ).pack(anchor="w", padx=(px(28), 0), pady=(0, px(4)))


def criar_coluna_generos(perfil_atual):
    escala = escala_da_tela(area_resumo_perfil)

    def px(valor):
        return int(valor * escala)

    coluna = tk.Frame(area_resumo_perfil, bg=COR_PAPEL)
    coluna.grid(row=0, column=0, sticky="nsew", pady=px(16))
    widgets_resumo_perfil.append(coluna)

    tk.Label(
        coluna, text="✦ o que eu mais curto", font=(FONTE_MANUSCRITA, -px(25), "bold"),
        fg=COR_TITULO_MANUSCRITO, bg=COR_PAPEL
    ).pack(anchor="w", padx=px(20), pady=(0, px(8)))

    generos_top = perfil.itens_ordenados(perfil_atual["generos"], quantidade=QUANTIDADE_GENEROS_NO_PERFIL)

    if not generos_top:
        tk.Label(
            coluna, text="ainda não há um gênero que se destaque",
            font=(FONTE_MANUSCRITA, -px(16)), fg=COR_TEXTO_SECUNDARIO, bg=COR_PAPEL
        ).pack(anchor="w", padx=px(24))
        return

    maior_afinidade = generos_top[0]["afinidade"]
    for item in generos_top:
        criar_linha_genero(coluna, item, maior_afinidade, escala)


def criar_etiquetas(container, nomes, escala):
    """Etiquetas de papel coladas lado a lado (até 2 por linha, nomes longos cabem), cada uma de um papel."""
    def px(valor):
        return int(valor * escala)

    linha = None
    for posicao, nome in enumerate(nomes):
        if posicao % ETIQUETAS_POR_LINHA == 0:
            linha = tk.Frame(container, bg=COR_PAPEL)
            linha.pack(anchor="w", pady=(0, px(6)))
        tk.Label(
            linha, text=nome, font=(FONTE, -px(13), "bold"), fg=COR_TEXTO,
            bg=CORES_ETIQUETA_PESSOA[posicao % len(CORES_ETIQUETA_PESSOA)],
            highlightbackground=COR_BORDA_PAPEL, highlightthickness=1,
            padx=px(9), pady=px(4)
        ).pack(side="left", padx=(0, px(6)), pady=(px((posicao % 2) * 3), 0))


def criar_coluna_pessoas(perfil_atual):
    escala = escala_da_tela(area_resumo_perfil)

    def px(valor):
        return int(valor * escala)

    coluna = tk.Frame(area_resumo_perfil, bg=COR_PAPEL)
    coluna.grid(row=0, column=1, sticky="nsew", pady=px(16), padx=(0, px(20)))
    widgets_resumo_perfil.append(coluna)

    blocos = [
        ("diretores (e criadores) que eu sigo", perfil.itens_ordenados(perfil_atual["diretores"], quantidade=3)),
        ("atores que sempre me ganham", perfil.itens_ordenados(perfil_atual["atores"], quantidade=3)),
    ]
    for titulo_bloco, itens in blocos:
        if not itens:
            continue
        tk.Label(
            coluna, text="✎ " + titulo_bloco, font=(FONTE_MANUSCRITA, -px(17), "bold"),
            fg=COR_VERMELHO, bg=COR_PAPEL
        ).pack(anchor="w", pady=(0, px(4)))
        criar_etiquetas(coluna, [item["nome"] for item in itens], escala)
        tk.Frame(coluna, bg=COR_PAPEL, height=px(6)).pack()

    evitados = perfil.itens_ordenados(perfil_atual["generos"], positivos=False, quantidade=3)
    if evitados:
        tk.Label(
            coluna, text="✎ menos a minha praia", font=(FONTE_MANUSCRITA, -px(17), "bold"),
            fg=COR_VERMELHO, bg=COR_PAPEL
        ).pack(anchor="w", pady=(0, px(2)))
        linha = tk.Frame(coluna, bg=COR_PAPEL)
        linha.pack(anchor="w")
        for item in evitados:
            tk.Label(
                linha, text=item["nome"], font=(FONTE_MANUSCRITA, -px(18), "overstrike"),
                fg=COR_TEXTO_SUAVE, bg=COR_PAPEL
            ).pack(side="left", padx=(0, px(12)))


# ---------- "O que o seu diário diz sobre você" ----------
# A IA demora alguns segundos: ela escreve numa thread separada e a página
# mostra "lendo o seu diário..." enquanto isso. O retrato fica guardado e só
# é escrito de novo quando o diário muda (ou no "✎ escrever de novo").
estado_retrato = {"escrevendo": False, "rotulos": []}


def limpar_area_retrato():
    for widget in area_retrato.winfo_children():
        widget.destroy()
    estado_retrato["rotulos"].clear()


def cabecalho_do_retrato(escala):
    def px(valor):
        return int(valor * escala)

    tk.Label(
        area_retrato, text="✍ o que o seu diário diz sobre você", font=(FONTE_MANUSCRITA, -px(25), "bold"),
        fg=COR_TITULO_MANUSCRITO, bg=COR_PAPEL
    ).pack(anchor="w", padx=px(20), pady=(px(16), 0))
    tk.Frame(area_retrato, bg=COR_MARCA_TEXTO, height=px(6), width=px(300)).pack(
        anchor="w", padx=px(24), pady=(0, px(10))
    )


def ajustar_larguras_do_retrato(event=None):
    largura_area = area_retrato.winfo_width()
    for rotulo, margem in estado_retrato["rotulos"]:
        if rotulo.winfo_exists() and largura_area - margem > 100:
            rotulo.configure(wraplength=largura_area - margem)


def texto_que_acompanha_largura(rotulo, margem):
    """O texto quebra as linhas conforme a largura da página (a janela pode mudar de tamanho)."""
    estado_retrato["rotulos"].append((rotulo, margem))
    area_retrato.after(10, ajustar_larguras_do_retrato)


area_retrato.bind("<Configure>", ajustar_larguras_do_retrato)


def desenhar_retrato(resultado_retrato):
    limpar_area_retrato()
    escala = escala_da_tela(area_retrato)

    def px(valor):
        return int(valor * escala)

    cabecalho_do_retrato(escala)
    paragrafo = tk.Label(
        area_retrato, text=resultado_retrato["texto"], font=(FONTE_MANUSCRITA, -px(21)),
        fg=COR_AZUL_CANETA, bg=COR_PAPEL, justify="left", anchor="w", wraplength=px(800)
    )
    paragrafo.pack(fill="x", padx=px(26), pady=(0, px(12)))
    texto_que_acompanha_largura(paragrafo, px(60))

    filmes_por_nome = {filme["nome"]: filme for filme in filmes.filmes}
    if resultado_retrato["citacoes"]:
        tk.Label(
            area_retrato, text="✎ nas suas palavras:", font=(FONTE_MANUSCRITA, -px(17), "bold"),
            fg=COR_VERMELHO, bg=COR_PAPEL
        ).pack(anchor="w", padx=px(26), pady=(px(2), px(4)))
        for citacao in resultado_retrato["citacoes"]:
            bilhete = tk.Frame(area_retrato, bg=COR_BILHETE, highlightbackground=COR_BORDA_PAPEL, highlightthickness=1)
            bilhete.pack(fill="x", padx=(px(40), px(40)), pady=(0, px(6)))
            frase = tk.Label(
                bilhete, text=f"“{citacao['texto']}”", font=(FONTE_MANUSCRITA, -px(17)),
                fg=COR_TEXTO_CONTEUDO, bg=COR_BILHETE, justify="left", anchor="w", wraplength=px(700)
            )
            frase.pack(side="left", fill="x", expand=True, padx=(px(12), px(8)), pady=px(6))
            texto_que_acompanha_largura(frase, px(330))
            estrelas = f"  {usuario.texto_estrelas(citacao['nota'])}" if citacao["nota"] else ""
            nome = tk.Label(
                bilhete, text=f"— {citacao['filme']}{estrelas}", font=(FONTE_MANUSCRITA, -px(16), "bold"),
                fg=COR_VERMELHO, bg=COR_BILHETE, cursor="hand2"
            )
            nome.pack(side="right", padx=(0, px(12)))
            filme_citado = filmes_por_nome.get(citacao["filme"])
            if filme_citado is not None:
                nome.bind("<Button-1>", lambda event, filme=filme_citado: abrir_detalhes(filme))

    rodape_retrato = tk.Frame(area_retrato, bg=COR_PAPEL)
    rodape_retrato.pack(fill="x", padx=px(26), pady=(px(4), px(16)))
    try:
        dia = date.fromisoformat(resultado_retrato["criado_em"]).strftime("%d/%m/%Y")
    except (KeyError, ValueError):
        dia = ""
    if resultado_retrato["origem"] == retrato.ORIGEM_IA:
        assinatura = f"escrito pela IA local (Ollama) em {dia}, só com o que está no seu diário"
    else:
        assinatura = f"escrito sem a IA em {dia} (ela estava desligada ou a resposta não passou na conferência)"
    tk.Label(
        rodape_retrato, text=assinatura, font=(FONTE_MANUSCRITA, -px(14)), fg=COR_TEXTO_SUAVE, bg=COR_PAPEL
    ).pack(side="left")
    link = tk.Label(
        rodape_retrato, text="✎ escrever de novo", font=(FONTE_MANUSCRITA, -px(17), "bold"),
        fg=COR_TEXTO_CAPA, bg=COR_VINHO, padx=px(12), pady=px(3), cursor="hand2"
    )
    link.pack(side="right")
    link.bind("<Button-1>", lambda event: escrever_retrato(forcar=True))


def desenhar_retrato_sem_dados():
    limpar_area_retrato()
    escala = escala_da_tela(area_retrato)
    cabecalho_do_retrato(escala)
    tk.Label(
        area_retrato,
        text=f"Ainda estou lendo as primeiras páginas... marque pelo menos {retrato.MINIMO_TITULOS_RETRATO} "
             "títulos como vistos (e escreva anotações neles) que eu conto o que o seu diário diz sobre você.",
        font=(FONTE_MANUSCRITA, -int(17 * escala)), fg=COR_TEXTO_SECUNDARIO, bg=COR_PAPEL,
        justify="left", wraplength=int(800 * escala)
    ).pack(anchor="w", padx=int(26 * escala), pady=(0, int(18 * escala)))


def desenhar_retrato_escrevendo():
    limpar_area_retrato()
    escala = escala_da_tela(area_retrato)
    cabecalho_do_retrato(escala)
    tk.Label(
        area_retrato, text="✎ a IA está lendo o seu diário... (leva alguns segundos)",
        font=(FONTE_MANUSCRITA, -int(19 * escala)), fg=COR_TEXTO_SUAVE, bg=COR_PAPEL
    ).pack(anchor="w", padx=int(26 * escala), pady=(0, int(20 * escala)))


def escrever_retrato(forcar=False):
    """Mostra o retrato guardado ou pede um novo à IA (numa thread, sem travar a janela)."""
    fatos = retrato.fatos_do_diario(filmes.filmes)
    if fatos is None:
        desenhar_retrato_sem_dados()
        return
    guardado = None if forcar else retrato.retrato_guardado(fatos)
    if guardado is not None:
        desenhar_retrato(guardado)
        return
    if estado_retrato["escrevendo"]:
        return
    estado_retrato["escrevendo"] = True
    desenhar_retrato_escrevendo()

    def trabalho():
        texto_ia = retrato.escrever_com_ia(fatos, filmes.perguntar_ao_modelo)
        janela.after(0, lambda: terminar(texto_ia))

    def terminar(texto_ia):
        estado_retrato["escrevendo"] = False
        resultado_retrato = retrato.montar_retrato(fatos, texto_ia)
        if area_retrato.winfo_exists():
            desenhar_retrato(resultado_retrato)

    threading.Thread(target=trabalho, daemon=True).start()


def mostrar_perfil_incompleto(perfil_atual):
    faltam = perfil.MINIMO_FILMES_PARA_PERFIL - perfil_atual["quantidade_com_sinal"]
    aviso = ctk.CTkLabel(
        area_resumo_perfil,
        text=(
            "Ainda estou te conhecendo 🙂\n\n"
            f"Dê estrelas ou favorite mais {faltam} filme{'s' if faltam > 1 else ''} "
            "para eu montar o seu perfil.\n"
            "Abra um filme e use os botões ♡ e ★, ou diga no chat:  "
            "\"Dou 5 estrelas para Shrek\"."
        ),
        font=(FONTE_MANUSCRITA, 17),
        text_color=COR_TEXTO_CONTEUDO,
        justify="center"
    )
    aviso.grid(row=0, column=0, columnspan=2, pady=25, padx=20)
    widgets_resumo_perfil.append(aviso)


def atualizar_pagina_perfil():
    # Só redesenha se a página estiver aberta (evita trabalho à toa).
    if not pagina_perfil.winfo_ismapped():
        return

    for widget in widgets_resumo_perfil:
        widget.destroy()
    widgets_resumo_perfil.clear()

    perfil_atual = perfil.calcular_perfil(filmes.filmes)
    escrever_retrato()

    if not perfil_atual["suficiente"]:
        mostrar_perfil_incompleto(perfil_atual)
        cabecalho_para_voce.configure(text="✦  POPULARES PARA COMEÇAR")
        lista_para_voce = filmes.ordenar_sem_perfil(
            [filme for filme in filmes.filmes if not usuario.foi_assistido(filme)]
        )[:QUANTIDADE_PARA_VOCE]
    else:
        criar_coluna_generos(perfil_atual)
        criar_coluna_pessoas(perfil_atual)
        cabecalho_para_voce.configure(
            text=f"✦  PARA VOCÊ  •  com base em {perfil_atual['quantidade_filmes']} filmes"
        )
        lista_para_voce = perfil.recomendar(filmes.filmes, perfil_atual, QUANTIDADE_PARA_VOCE)

    preencher_grade(
        scroll_para_voce,
        lista_para_voce,
        widgets_para_voce,
        imagens_para_voce,
        "Você já assistiu a todos os filmes do catálogo! 🎉"
    )
    rolagem_perfil._parent_canvas.yview_moveto(0)  # volta para o topo da página


# =========================================================
# PÁGINA PAINEL DO RAG (modo desenvolvedor)
# =========================================================
# Mostra o caminho de cada resposta: rota escolhida, intenção, filtros,
# chamadas à IA, busca semântica com as similaridades, ranking e resultado,
# com o tempo de cada etapa. Os dados vêm do rastreio.py.
SEM_RASTROS = "Nenhuma mensagem ainda"
LARGURA_BARRA_TEMPO = 160
LARGURA_BARRA_PONTUACAO = 150

cabecalho_rag = criar_cabecalho_pagina(
    pagina_rag,
    "Painel do RAG",
    "o caminho de cada resposta, do seu pedido até o filme"
)

barra_rag = ctk.CTkFrame(cabecalho_rag, fg_color="transparent")
barra_rag.pack(fill="x", pady=(12, 0))

rotulo_rag = ctk.CTkLabel(
    barra_rag,
    text="MENSAGEM:",
    font=(FONTE_TITULO, 15),
    text_color=COR_VERMELHO
)
rotulo_rag.pack(side="left", padx=(0, 8))

seletor_rastros = ctk.CTkOptionMenu(
    barra_rag,
    values=[SEM_RASTROS],
    width=420,
    height=32,
    font=(FONTE, 12),
    dropdown_font=(FONTE, 12),
    fg_color=COR_PAPEL_ESCURO,
    button_color=COR_VERMELHO,
    button_hover_color=COR_VERMELHO_HOVER,
    text_color=COR_TEXTO,
    dropdown_fg_color=COR_PAPEL,
    dropdown_hover_color=COR_PAPEL_ESCURO,
    dropdown_text_color=COR_TEXTO,
    corner_radius=4,
    dynamic_resizing=False,
    command=lambda rotulo_escolhido: mostrar_rastro_pelo_rotulo(rotulo_escolhido)
)
seletor_rastros.pack(side="left")


def criar_chip_resumo(container):
    """Etiquetas de resumo (tempo total, chamadas à IA, etapas)."""
    chip = ctk.CTkLabel(
        container,
        text="",
        font=(FONTE_INTERFACE, 12, "bold"),
        text_color=COR_VINHO,
        fg_color=COR_INGRESSO,
        corner_radius=4,
        height=30
    )
    chip.pack(side="left", padx=(10, 0))
    return chip


chip_tempo_total = criar_chip_resumo(barra_rag)
chip_ia = criar_chip_resumo(barra_rag)
chip_etapas = criar_chip_resumo(barra_rag)

area_rastro = ctk.CTkScrollableFrame(
    pagina_rag,
    corner_radius=0,
    fg_color=COR_FUNDO,
    scrollbar_button_color=COR_ROLAGEM,
    scrollbar_button_hover_color=COR_ROLAGEM_HOVER
)
area_rastro.grid(row=1, column=0, sticky="nsew", padx=34, pady=(0, 20))
area_rastro.grid_columnconfigure(0, weight=1)

rotulo_para_rastro = {}


def rotulo_do_rastro(rastro_salvo):
    mensagem = rastro_salvo["mensagem"] or "(vazia)"
    if len(mensagem) > 42:
        mensagem = mensagem[:41] + "…"
    return f'{rastro_salvo["horario"]} • {mensagem} ({formatar_ms(rastro_salvo["total_ms"])})'


def limpar_area_rastro():
    for widget in area_rastro.winfo_children():
        widget.destroy()


def criar_tabela_da_etapa(container, tabela):
    """Ranking da etapa: posição, filme, valores e uma barra de pontuação."""
    grade = ctk.CTkFrame(container, fg_color=COR_FUNDO, corner_radius=4)
    grade.pack(fill="x", padx=(0, 14), pady=(6, 10))

    cabecalhos = ["#", "filme"] + tabela["colunas"] + [""]
    for coluna, texto in enumerate(cabecalhos):
        ctk.CTkLabel(
            grade,
            text=texto.upper(),
            font=(FONTE_INTERFACE, 10, "bold"),
            text_color=COR_TEXTO_SUAVE,
            anchor="w"
        ).grid(row=0, column=coluna, sticky="w", padx=8, pady=(6, 0))

    grade.grid_columnconfigure(1, weight=1)

    for linha, (nome_filme, valores, barra) in enumerate(tabela["linhas"], start=1):
        eh_primeiro = linha == 1
        cor_texto = COR_VERMELHO if eh_primeiro else COR_TEXTO_CONTEUDO
        peso = "bold" if eh_primeiro else "normal"

        ctk.CTkLabel(
            grade, text=f"{linha}º", font=(FONTE_TITULO, 14), text_color=cor_texto
        ).grid(row=linha, column=0, sticky="w", padx=8, pady=2)

        ctk.CTkLabel(
            grade, text=nome_filme, font=(FONTE, 13, peso), text_color=cor_texto, anchor="w"
        ).grid(row=linha, column=1, sticky="w", padx=8, pady=2)

        for posicao, valor in enumerate(valores):
            ctk.CTkLabel(
                grade, text=valor, font=("Consolas", 12, peso), text_color=cor_texto
            ).grid(row=linha, column=2 + posicao, sticky="w", padx=8, pady=2)

        barra_pontuacao = ctk.CTkProgressBar(
            grade,
            width=LARGURA_BARRA_PONTUACAO,
            height=10,
            corner_radius=2,
            fg_color=COR_PAPEL_ESCURO,
            progress_color=COR_VERMELHO if eh_primeiro else COR_DOURADO
        )
        barra_pontuacao.set(max(0.0, min(1.0, barra)))
        barra_pontuacao.grid(row=linha, column=2 + len(valores), sticky="w", padx=(8, 12), pady=2)

    ctk.CTkFrame(grade, height=6, fg_color="transparent").grid(row=len(tabela["linhas"]) + 1, column=0)


def criar_cartao_etapa(numero, etapa, maior_tempo_ms):
    """Uma etapa do caminho, em forma de ingresso: canhoto com o número + anotações."""
    cartao = ctk.CTkFrame(
        area_rastro,
        fg_color=COR_PAPEL,
        border_width=1,
        border_color=COR_BORDA_PAPEL,
        corner_radius=6
    )
    cartao.pack(fill="x", padx=8, pady=0)
    cartao.grid_columnconfigure(2, weight=1)

    # Canhoto: número da etapa + ícone
    canhoto = ctk.CTkFrame(cartao, fg_color=COR_INGRESSO, corner_radius=4, width=70)
    canhoto.grid(row=0, column=0, sticky="ns", padx=(6, 0), pady=6)
    canhoto.grid_propagate(False)

    ctk.CTkLabel(
        canhoto, text=f"{numero:02d}", font=(FONTE_TITULO, 22), text_color=COR_VERMELHO
    ).pack(pady=(8, 0))
    ctk.CTkLabel(
        canhoto, text=etapa["icone"], font=(FONTE_SIMBOLOS, 18), text_color=COR_VINHO
    ).pack(pady=(0, 8))

    ctk.CTkLabel(
        cartao, text="┆\n┆\n┆", font=(FONTE_INTERFACE, 9), text_color=COR_INGRESSO_BORDA
    ).grid(row=0, column=1, padx=6)

    conteudo = ctk.CTkFrame(cartao, fg_color="transparent")
    conteudo.grid(row=0, column=2, sticky="nsew", pady=8)
    conteudo.grid_columnconfigure(0, weight=1)

    # Título + tempo da etapa (com barrinha proporcional à etapa mais lenta)
    linha_titulo = ctk.CTkFrame(conteudo, fg_color="transparent")
    linha_titulo.pack(fill="x", padx=(0, 14))

    ctk.CTkLabel(
        linha_titulo,
        text=etapa["titulo"].upper(),
        font=(FONTE_TITULO, 16),
        text_color=COR_TEXTO,
        anchor="w"
    ).pack(side="left")

    barra_tempo = ctk.CTkProgressBar(
        linha_titulo,
        width=LARGURA_BARRA_TEMPO,
        height=8,
        corner_radius=2,
        fg_color=COR_PAPEL_ESCURO,
        progress_color=COR_VERMELHO
    )
    barra_tempo.set(etapa["ms"] / maior_tempo_ms if maior_tempo_ms else 0)
    barra_tempo.pack(side="right", padx=(10, 0))

    ctk.CTkLabel(
        linha_titulo,
        text=formatar_ms(etapa["ms"]),
        font=("Consolas", 12, "bold"),
        text_color=COR_VERMELHO
    ).pack(side="right")

    if etapa["detalhe"]:
        eh_ia = etapa["icone"] == "🤖"
        ctk.CTkLabel(
            conteudo,
            text=etapa["detalhe"],
            font=(FONTE, 13),
            text_color=COR_AZUL_CANETA if eh_ia else COR_TEXTO_CONTEUDO,
            anchor="w",
            justify="left",
            wraplength=720
        ).pack(fill="x", padx=(0, 14), pady=(2, 0))

    if etapa["tabela"] and etapa["tabela"]["linhas"]:
        criar_tabela_da_etapa(conteudo, etapa["tabela"])


def criar_seta_entre_etapas():
    ctk.CTkLabel(
        area_rastro, text="↓", font=(FONTE_SIMBOLOS, 18), text_color=COR_VERMELHO, height=22
    ).pack()


def mostrar_rastro(rastro_escolhido):
    limpar_area_rastro()

    if rastro_escolhido is None:
        chip_tempo_total.configure(text="")
        chip_ia.configure(text="")
        chip_etapas.configure(text="")
        ctk.CTkLabel(
            area_rastro,
            text="Mande uma mensagem no chat e volte aqui:\n"
                 "o caminho da resposta aparece passo a passo. ✦",
            font=(FONTE_MANUSCRITA, 18),
            text_color=COR_TEXTO_SECUNDARIO,
            justify="center"
        ).pack(pady=60)
        return

    chip_tempo_total.configure(text=f"  ⏱ {formatar_ms(rastro_escolhido['total_ms'])} no total  ")
    if rastro_escolhido["chamadas_ia"]:
        chip_ia.configure(
            text=f"  🤖 {rastro_escolhido['chamadas_ia']}× IA • "
                 f"{formatar_ms(rastro_escolhido['tempo_ia_ms'])}  "
        )
    else:
        chip_ia.configure(text="  🤖 sem IA: só regras  ")
    chip_etapas.configure(text=f"  {len(rastro_escolhido['etapas'])} etapas  ")

    # A pergunta, escrita "à mão" no topo
    ctk.CTkLabel(
        area_rastro,
        text=f'“{rastro_escolhido["mensagem"]}”',
        font=(FONTE_MANUSCRITA, 22),
        text_color=COR_AZUL_CANETA,
        anchor="w",
        justify="left",
        wraplength=820
    ).pack(fill="x", padx=12, pady=(8, 4))
    criar_seta_entre_etapas()

    maior_tempo_ms = max((etapa["ms"] for etapa in rastro_escolhido["etapas"]), default=0)

    for numero, etapa in enumerate(rastro_escolhido["etapas"], start=1):
        if numero > 1:
            criar_seta_entre_etapas()
        criar_cartao_etapa(numero, etapa, maior_tempo_ms)

    ctk.CTkFrame(area_rastro, height=20, fg_color="transparent").pack()
    area_rastro._parent_canvas.yview_moveto(0)


def mostrar_rastro_pelo_rotulo(rotulo_escolhido):
    mostrar_rastro(rotulo_para_rastro.get(rotulo_escolhido))


def atualizar_painel_rag():
    """Recarrega a lista de mensagens e mostra a mais recente."""
    rotulo_para_rastro.clear()
    rotulos = []
    for rastro_salvo in rastro.historico:
        rotulo = rotulo_do_rastro(rastro_salvo)
        rotulo_para_rastro[rotulo] = rastro_salvo
        rotulos.append(rotulo)

    if not rotulos:
        seletor_rastros.configure(values=[SEM_RASTROS])
        seletor_rastros.set(SEM_RASTROS)
        mostrar_rastro(None)
        return

    seletor_rastros.configure(values=rotulos)
    seletor_rastros.set(rotulos[0])
    mostrar_rastro(rastro.historico[0])


# =========================================================
# NAVEGAÇÃO
# =========================================================
todas_paginas = [
    pagina_inicio,
    pagina_catalogo,
    pagina_recomendacoes,
    pagina_meus_filmes,
    pagina_perfil,
    pagina_chat,
    pagina_rag
]


def mostrar_pagina(pagina, botao_ativo, entrada_foco=None):
    for pagina_existente in todas_paginas:
        pagina_existente.grid_forget()

    pagina.grid(row=0, column=0, sticky="nsew")

    # O botão da página aberta vira um "ingresso" creme com letra vermelha.
    for botao in botoes_menu:
        botao.configure(fg_color="transparent", text_color=COR_TEXTO_CAPA, hover_color=COR_MENU_HOVER)
    botao_ativo.configure(fg_color=COR_INGRESSO, text_color=COR_VERMELHO, hover_color=COR_INGRESSO)

    if entrada_foco is not None:
        entrada_foco.focus()


def mostrar_inicio():
    mostrar_pagina(pagina_inicio, botao_inicio, entrada_busca)


def mostrar_catalogo():
    mostrar_pagina(pagina_catalogo, botao_buscar_menu, entrada_catalogo)


def mostrar_recomendacoes():
    mostrar_pagina(pagina_recomendacoes, botao_recomendacoes)


def mostrar_meus_filmes():
    mostrar_pagina(pagina_meus_filmes, botao_meus_filmes_menu)
    pagina_meus_filmes.update_idletasks()  # garante que a página já está visível
    atualizar_meus_filmes()


def mostrar_perfil():
    mostrar_pagina(pagina_perfil, botao_perfil_menu)
    pagina_perfil.update_idletasks()  # garante que a página já está visível
    atualizar_pagina_perfil()


def mostrar_chat():
    mostrar_pagina(pagina_chat, botao_chat_menu, entrada_chat_completo)
    chat_completo.see("end")


botao_inicio.configure(command=mostrar_inicio)
botao_buscar_menu.configure(command=mostrar_catalogo)
botao_recomendacoes.configure(command=mostrar_recomendacoes)
botao_meus_filmes_menu.configure(command=mostrar_meus_filmes)
botao_perfil_menu.configure(command=mostrar_perfil)
botao_chat_menu.configure(command=mostrar_chat)
botao_rag_menu.configure(command=lambda: mostrar_pagina(pagina_rag, botao_rag_menu))


# =========================================================
# INICIALIZAÇÃO
# =========================================================
for coluna in range(COLUNAS_CARDS):
    criar_card_recomendacao(coluna)  # os 4 recortes da Home ("cole aqui")

# Backup automático (se o último tem mais de 7 dias) — silencioso
try:
    usuario.backup_automatico_se_precisar()
except OSError as erro_backup:
    print(f"Não consegui fazer o backup automático: {erro_backup}")

# Sugestão da noite: o primeiro recorte já vem colado, com um bilhete no chat
sugestao_da_noite, motivo_da_sugestao, _ = filmes.sugestao_da_noite()
if sugestao_da_noite is not None:
    adicionar_filme_aos_cards(sugestao_da_noite)
    adicionar_mensagem(
        NOME_IA,
        f"🌙 Sugestão da noite: {filmes.descrever_filme_curto(sugestao_da_noite)} — {motivo_da_sugestao}. "
        'Clique no recorte para abrir, ou me pergunte "o que eu vejo hoje?".'
    )

atualizar_catalogo()
atualizar_recomendacoes()
atualizar_meus_filmes()
atualizar_painel_rag()
mostrar_inicio()
def iniciar():
    """Abre a janela do CineAI (o main.py chama isto)."""
    janela.mainloop()


if __name__ == "__main__":
    iniciar()