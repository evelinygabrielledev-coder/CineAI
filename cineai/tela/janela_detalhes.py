"""
tela/janela_detalhes.py — A página de um filme (o diário aberto) e a janela que compara dois títulos.

Parte da janela do CineAI (veja cineai/interface.py, que junta todas as partes).
"""
from cineai.tela.recortes import *  # noqa: F401,F403  (tudo das partes anteriores)
from cineai.tela.ponte import ponte


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
        progresso = usuario.obter_progresso(filme) if filmes.eh_serie(filme) else None
        if progresso is not None:
            return f"  ✦ {tipo} JOURNAL  •  WATCHING {usuario.texto_do_episodio(*progresso)}  "
        return f"  ✦ {tipo} JOURNAL  •  TO WATCH  "
    return f"  ✦ {tipo} JOURNAL  •  ENTRY #{entrada:03d}  "


# ---------- Séries: "onde eu parei" (S02E05) ----------
MAXIMO_OPCOES_SEM_DADOS = 30   # sem saber os episódios, oferece até 30 em cada menu


def texto_onde_parei(serie):
    atual = usuario.obter_progresso(serie)
    if atual is None:
        return "já terminei ✓" if usuario.foi_assistido(serie) else "ainda não comecei"
    texto = "parei no " + usuario.texto_do_episodio(*atual)
    porcentagem = usuario.porcentagem_da_serie(serie)
    if porcentagem is not None:
        texto += f"  ·  {porcentagem}% da série"
    return texto


def criar_area_onde_parei(container, serie, ao_mudar=None):
    """Temporada + episódio em menus, e o botão "vi o próximo"."""
    area = tk.Frame(container, bg=COR_PAPEL)
    area.pack(fill="x", padx=34, pady=(0, 4))
    escala = escala_da_tela(container)

    status = tk.Label(area, text="", font=(FONTE_MANUSCRITA, -int(19 * escala), "bold"), fg=COR_AZUL_CANETA, bg=COR_PAPEL)
    status.pack(anchor="w")
    aviso = tk.Label(area, text="", font=(FONTE_MANUSCRITA, -int(14 * escala)), fg=COR_VERMELHO, bg=COR_PAPEL)

    por_temporada = usuario.episodios_por_temporada(serie)
    total_temporadas = len(por_temporada) or serie.get("temporadas") or MAXIMO_OPCOES_SEM_DADOS

    def episodios_da(temporada):
        if por_temporada and 1 <= temporada <= len(por_temporada):
            return por_temporada[temporada - 1]
        return MAXIMO_OPCOES_SEM_DADOS

    linha = tk.Frame(area, bg=COR_PAPEL)
    linha.pack(anchor="w", pady=(6, 2))
    estilo_menu = dict(
        width=64, height=28, fg_color=COR_PAPEL_ESCURO, button_color=COR_VINHO, button_hover_color=COR_VERMELHO,
        text_color=COR_TEXTO, dropdown_fg_color=COR_PAPEL, dropdown_text_color=COR_TEXTO, font=(FONTE_INTERFACE, 13, "bold")
    )
    tk.Label(linha, text="temporada", font=(FONTE_MANUSCRITA, -int(16 * escala)), fg=COR_TEXTO_SECUNDARIO, bg=COR_PAPEL).pack(side="left")
    menu_temporada = ctk.CTkOptionMenu(linha, values=[str(numero) for numero in range(1, total_temporadas + 1)], **estilo_menu)
    menu_temporada.pack(side="left", padx=(6, 12))
    tk.Label(linha, text="episódio", font=(FONTE_MANUSCRITA, -int(16 * escala)), fg=COR_TEXTO_SECUNDARIO, bg=COR_PAPEL).pack(side="left")
    menu_episodio = ctk.CTkOptionMenu(linha, values=["1"], **estilo_menu)
    menu_episodio.pack(side="left", padx=(6, 12))

    def trocar_temporada(valor):
        quantidade = episodios_da(int(valor))
        menu_episodio.configure(values=[str(numero) for numero in range(1, quantidade + 1)])
        if int(menu_episodio.get()) > quantidade:
            menu_episodio.set(str(quantidade))

    menu_temporada.configure(command=trocar_temporada)

    def depois_de_mudar(resultado):
        aviso.configure(text="série concluída! 🎉 ela entrou no seu diário" if resultado else "")
        mostrar()
        if ao_mudar is not None:
            ao_mudar()

    def salvar():
        try:
            resultado = usuario.definir_progresso(serie, int(menu_temporada.get()), int(menu_episodio.get()))
        except ValueError as erro:
            aviso.configure(text=str(erro))
            return
        depois_de_mudar(resultado["terminou"])

    def ver_o_proximo():
        try:
            _, _, terminou = usuario.avancar_episodio(serie)
        except ValueError as erro:
            aviso.configure(text=str(erro))
            return
        depois_de_mudar(terminou)

    def apagar(event=None):
        usuario.apagar_progresso(serie)
        depois_de_mudar(False)

    ctk.CTkButton(
        linha, text="salvar", width=70, height=28, corner_radius=4, fg_color=COR_VINHO, hover_color=COR_VERMELHO,
        text_color=COR_TEXTO_CAPA, font=(FONTE_MANUSCRITA, 15, "bold"), command=salvar
    ).pack(side="left")

    botao_proximo = ctk.CTkButton(
        area, text="", height=34, corner_radius=4, fg_color=COR_VERMELHO, hover_color=COR_VERMELHO_HOVER,
        text_color=COR_TEXTO_CAPA, font=(FONTE_MANUSCRITA, 17, "bold"), command=ver_o_proximo
    )
    botao_proximo.pack(anchor="w", pady=(6, 2))
    link_apagar = tk.Label(area, text="", font=(FONTE_MANUSCRITA, -int(14 * escala)), fg=COR_TEXTO_SUAVE, bg=COR_PAPEL, cursor="hand2")
    link_apagar.bind("<Button-1>", apagar)
    aviso.pack(anchor="w")

    def mostrar():
        status.configure(text=texto_onde_parei(serie))
        atual = usuario.obter_progresso(serie)
        temporada, episodio = atual or (1, 1)
        menu_temporada.set(str(temporada))
        trocar_temporada(str(temporada))
        menu_episodio.set(str(episodio))
        proxima = usuario.proximo_episodio(serie)
        botao_proximo.configure(text=f"▶  vi o próximo: {usuario.texto_do_episodio(*proxima)}" if atual else "▶  vi o primeiro episódio")
        if atual:
            link_apagar.configure(text="✕ apagar onde parei")
            link_apagar.pack(anchor="w", before=aviso)
        else:
            link_apagar.pack_forget()

    mostrar()
    return area


# ---------- Listas temáticas ("pra chorar", "com a família"...) ----------
def texto_do_link_de_listas(filme):
    listas = usuario.listas_do_filme(filme)
    if not listas:
        return "🏷 colocar numa lista"
    return "🏷 " + ", ".join(listas)


def abrir_listas_do_filme(filme, janela_mae, ao_fechar=None):
    """Janelinha com uma caixinha para cada lista + um campo para criar outra."""
    janela_listas = ctk.CTkToplevel(janela_mae)
    janela_listas.title("Listas")
    janela_listas.resizable(False, False)
    janela_listas.configure(fg_color=COR_PAPEL)
    janela_listas.transient(janela_mae)
    janela_mae.update_idletasks()
    janela_listas.geometry(f"+{janela_mae.winfo_rootx() + 120}+{janela_mae.winfo_rooty() + 220}")
    janela_listas.after(50, janela_listas.grab_set)

    ctk.CTkLabel(
        janela_listas, text="em quais listas ele entra? 🏷", font=(FONTE_MANUSCRITA, 22, "bold"),
        text_color=COR_TITULO_MANUSCRITO
    ).pack(padx=26, pady=(18, 2))
    ctk.CTkLabel(
        janela_listas, text=filme["nome"], font=(FONTE_TITULO, 16), text_color=COR_TEXTO
    ).pack(padx=26, pady=(0, 10))

    area_caixas = ctk.CTkFrame(janela_listas, fg_color="transparent")
    area_caixas.pack(fill="x", padx=30)

    def desenhar_caixas():
        for widget in area_caixas.winfo_children():
            widget.destroy()
        nomes = usuario.nomes_das_listas()
        if not nomes:
            ctk.CTkLabel(
                area_caixas, text="você ainda não tem listas: crie a primeira aqui embaixo",
                font=(FONTE_MANUSCRITA, 15), text_color=COR_TEXTO_SUAVE
            ).pack(anchor="w")
        for nome in nomes:
            marcada = tk.BooleanVar(value=usuario.esta_na_lista_tematica(nome, filme))
            ctk.CTkCheckBox(
                area_caixas, text=f"{nome}  ({len(usuario.dados_usuario['listas'][nome]['titulos'])})",
                variable=marcada, font=(FONTE_MANUSCRITA, 17), text_color=COR_AZUL_CANETA,
                fg_color=COR_VERMELHO, hover_color=COR_VERMELHO_HOVER, border_color=COR_BORDA_PAPEL,
                command=lambda nome=nome: (usuario.alternar_na_lista_tematica(nome, filme), desenhar_caixas())
            ).pack(anchor="w", pady=3)

    desenhar_caixas()

    linha_nova = ctk.CTkFrame(janela_listas, fg_color="transparent")
    linha_nova.pack(fill="x", padx=30, pady=(14, 4))
    campo = ctk.CTkEntry(
        linha_nova, width=210, placeholder_text="nova lista (ex.: pra chorar)", font=(FONTE_MANUSCRITA, 15),
        fg_color=COR_BILHETE, border_color=COR_BORDA_PAPEL, text_color=COR_TEXTO
    )
    campo.pack(side="left")
    aviso = ctk.CTkLabel(janela_listas, text="", font=(FONTE_MANUSCRITA, 14), text_color=COR_VERMELHO)

    def criar(event=None):
        try:
            nome = usuario.criar_lista(campo.get())
        except ValueError as erro:
            aviso.configure(text=str(erro))
            return
        usuario.alternar_na_lista_tematica(nome, filme)
        campo.delete(0, "end")
        aviso.configure(text="")
        desenhar_caixas()

    ctk.CTkButton(
        linha_nova, text="+ criar", width=70, height=30, corner_radius=4, fg_color=COR_VINHO,
        hover_color=COR_VERMELHO, text_color=COR_TEXTO_CAPA, font=(FONTE_MANUSCRITA, 15, "bold"), command=criar
    ).pack(side="left", padx=(8, 0))
    campo.bind("<Return>", criar)
    aviso.pack(pady=(0, 2))

    def fechar():
        janela_listas.destroy()
        if ao_fechar is not None:
            ao_fechar()

    ctk.CTkButton(
        janela_listas, text="pronto ✓", height=34, corner_radius=4, fg_color=COR_VERMELHO,
        hover_color=COR_VERMELHO_HOVER, text_color=COR_TEXTO_CAPA, font=(FONTE_MANUSCRITA, 17, "bold"),
        command=fechar
    ).pack(padx=30, pady=(6, 18), fill="x")
    janela_listas.protocol("WM_DELETE_WINDOW", fechar)
    return janela_listas


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

    # "🏷 colocar numa lista": as listas temáticas que você criou
    link_listas = tk.Label(
        pagina_esquerda, text="", font=(FONTE_MANUSCRITA, -int(15 * escala), "bold"),
        fg=COR_AZUL_CANETA, bg=COR_PAPEL, cursor="hand2", wraplength=int(240 * escala)
    )
    link_listas.pack(pady=(0, 6))

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

    # Séries: até onde você viu (S02E05)
    if filmes.eh_serie(filme):
        adicionar_titulo_secao(pagina_direita, "ONDE EU PAREI 📺")
        criar_area_onde_parei(
            pagina_direita, filme,
            ao_mudar=lambda: (atualizar_botoes(), ponte.atualizar_meus_filmes(voltar_ao_topo=False))
        )

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
        ponte.atualizar_meus_filmes(voltar_ao_topo=False)  # a anotação aparece na entrada do diário

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

        link_listas.configure(text=texto_do_link_de_listas(filme))
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
    link_listas.bind("<Button-1>", lambda event: abrir_listas_do_filme(
        filme, detalhes, ao_fechar=lambda: (atualizar_botoes(), ponte.atualizar_meus_filmes(voltar_ao_topo=False))
    ))
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


# Partes que vêm ANTES desta usam estes nomes pela ponte (veja tela/ponte.py).
ponte.registrar(
    abrir_detalhes=abrir_detalhes,
)
