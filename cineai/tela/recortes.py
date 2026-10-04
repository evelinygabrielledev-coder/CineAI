"""
tela/recortes.py — Polaroides desenhadas com o Pillow (os cards de filme), selinhos ❤/✅ e a grade de cards.

Parte da janela do CineAI (veja cineai/interface.py, que junta todas as partes).
"""
from cineai.tela.base import *  # noqa: F401,F403  (tudo das partes anteriores)
from cineai.tela.ponte import ponte


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
    for dados_card in ponte.cards_recomendacao:
        if dados_card["filme"] is not None:
            ponte.mostrar_filme_no_card(dados_card, dados_card["filme"])


def ao_mudar_listas():
    """Chamada sempre que um filme entra ou sai dos favoritos/assistidos."""
    atualizar_selos_em_tela()
    atualizar_recortes_em_tela()  # nota, coração e carimbo WATCHED nas polaroides

    # Com "esconder os que já vi" ou ordem "Combina comigo", o Catálogo muda junto.
    if ponte.esconder_assistidos_var.get() or ponte.filtro_ordem.get() == "Combina comigo":
        ponte.atualizar_catalogo(manter_pagina=True)
    ponte.atualizar_meus_filmes(voltar_ao_topo=False)
    ponte.atualizar_pagina_perfil()


def vincular_clique(widgets, funcao):
    for widget in widgets:
        widget.bind("<Button-1>", funcao)


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
        ponte.abrir_detalhes(filme)

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
