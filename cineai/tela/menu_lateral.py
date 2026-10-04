"""
tela/menu_lateral.py — A capa vermelha do lado esquerdo, os ícones desenhados à mão e a área onde as páginas aparecem.

Parte da janela do CineAI (veja cineai/interface.py, que junta todas as partes).
"""
from cineai.tela.janela_detalhes import *  # noqa: F401,F403  (tudo das partes anteriores)
from cineai.tela.ponte import ponte


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
