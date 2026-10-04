"""
tela/inicio.py — Página Início: letreiro, película 5-4-3-2-1, busca em forma de ingresso e os recortes recomendados.

Parte da janela do CineAI (veja cineai/interface.py, que junta todas as partes).
"""
from cineai.tela.menu_lateral import *  # noqa: F401,F403  (tudo das partes anteriores)
from cineai.tela.ponte import ponte


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
        command=lambda: ponte.processar(MENSAGEM_SURPRESA)
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


# Partes que vêm ANTES desta usam estes nomes pela ponte (veja tela/ponte.py).
ponte.registrar(
    cards_recomendacao=cards_recomendacao,
    mostrar_filme_no_card=mostrar_filme_no_card,
)
