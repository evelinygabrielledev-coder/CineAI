"""
tela/meu_diario.py — Página Meu diário: Capa, Diário (entradas por mês), Favoritos, Quero assistir e o backup.

Parte da janela do CineAI (veja cineai/interface.py, que junta todas as partes).
"""
from cineai.tela.catalogo import *  # noqa: F401,F403  (tudo das partes anteriores)
from cineai.tela.ponte import ponte


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
ABA_LISTAS = "🏷  Listas"

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
    values=[ABA_CAPA, ABA_DIARIO, ABA_FAVORITOS, ABA_QUERO_VER, ABA_LISTAS],
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


# ---------- Meta do ano ("ver 50 filmes em 2026") ----------
LARGURA_BARRA_META, ALTURA_BARRA_META = 520, 24


def texto_do_ritmo(progresso):
    if progresso["batida"]:
        alem = progresso["feitos"] - progresso["meta"]
        return "meta batida! 🎉" + (f"  (+{alem} além)" if alem else "")
    if progresso["no_ritmo"]:
        return "no ritmo certo ✓"
    if progresso["por_mes"]:
        return f"faltam {progresso['falta']}: uns {progresso['por_mes']} por mês até dezembro"
    return f"faltaram {progresso['falta']}"


def editar_meta(ano):
    from tkinter import simpledialog
    atual = usuario.obter_meta(ano)
    quantidade = simpledialog.askinteger(
        "Meta do ano", f"Quantos títulos você quer ver em {ano}?\n(0 apaga a meta)",
        parent=janela, minvalue=0, maxvalue=usuario.META_MAXIMA, initialvalue=atual or 50
    )
    if quantidade is None:
        return   # cancelou
    usuario.definir_meta(ano, quantidade)
    ponte.atualizar_meus_filmes(voltar_ao_topo=False)


def criar_area_da_meta(folha, escala, ano=None):
    """Na Capa: a meta do ano com uma barra de marca-texto (ou o convite para criar uma)."""
    def px(valor):
        return int(valor * escala)

    ano = ano or date.today().year
    progresso = usuario.progresso_da_meta(filmes.filmes, ano)
    area = tk.Frame(folha, bg=COR_PAPEL)
    area.pack(pady=(0, px(18)))

    if progresso is None:
        link = tk.Label(
            area, text=f"🎯  definir uma meta para {ano}", font=(FONTE_MANUSCRITA, -px(19), "bold"),
            fg=COR_VERMELHO, bg=COR_PAPEL, cursor="hand2"
        )
        link.pack()
        link.bind("<Button-1>", lambda event: editar_meta(ano))
        return

    cabecalho = tk.Frame(area, bg=COR_PAPEL)
    cabecalho.pack()
    tk.Label(
        cabecalho, text=f"🎯 meta de {ano}:", font=(FONTE_MANUSCRITA, -px(20), "bold"),
        fg=COR_VERMELHO, bg=COR_PAPEL
    ).pack(side="left")
    tk.Label(
        cabecalho, text=f"{progresso['feitos']} de {progresso['meta']} títulos",
        font=(FONTE_MANUSCRITA, -px(21)), fg=COR_AZUL_CANETA, bg=COR_PAPEL
    ).pack(side="left", padx=(px(8), px(14)))
    mudar = tk.Label(
        cabecalho, text="✎ mudar", font=(FONTE_MANUSCRITA, -px(15)), fg=COR_TEXTO_SUAVE,
        bg=COR_PAPEL, cursor="hand2"
    )
    mudar.pack(side="left")
    mudar.bind("<Button-1>", lambda event: editar_meta(ano))

    # Barra: papel kraft com a passada de marca-texto até onde você chegou
    largura, altura = px(LARGURA_BARRA_META), px(ALTURA_BARRA_META)
    barra = tk.Canvas(area, width=largura, height=altura, bg=COR_PAPEL, highlightthickness=0)
    barra.pack(pady=(px(6), px(4)))
    barra.create_rectangle(1, 1, largura - 1, altura - 1, fill=COR_PAPEL_ESCURO, outline=COR_BORDA_PAPEL)
    preenchido = int((largura - 4) * progresso["porcentagem"] / 100)
    if preenchido > 0:
        cor = COR_DOURADO if progresso["batida"] else COR_MARCA_TEXTO
        barra.create_rectangle(2, 3, 2 + preenchido, altura - 3, fill=cor, outline="")
    # tracinho de onde você "deveria" estar hoje
    if not progresso["batida"] and ano == date.today().year:
        x_esperado = 2 + int((largura - 4) * min(1, progresso["esperado_ate_hoje"] / progresso["meta"]))
        barra.create_line(x_esperado, 0, x_esperado, altura, fill=COR_VERMELHO, width=max(1, px(2)), dash=(3, 2))
    barra.create_text(
        largura // 2, altura // 2, text=f"{progresso['porcentagem']}%",
        font=(FONTE_TITULO, -px(14)), fill=COR_TEXTO
    )
    tk.Label(
        area, text=texto_do_ritmo(progresso), font=(FONTE_MANUSCRITA, -px(16)),
        fg=COR_AZUL_CANETA if progresso["batida"] or progresso["no_ritmo"] else COR_TEXTO_SECUNDARIO,
        bg=COR_PAPEL
    ).pack()


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
        ).pack(pady=(px(6), px(14)))
        ponte.criar_link_letterboxd(folha, escala)
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

    criar_area_da_meta(folha, escala)

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

    ponte.criar_botao_retrospectiva(folha, escala)
    criar_area_de_backup(folha, escala)

    canvas_rolagem = getattr(scroll_meus_filmes, "_parent_canvas", None)
    if canvas_rolagem is not None:
        canvas_rolagem.yview_moveto(0)


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


# =========================================================
# LISTAS TEMÁTICAS — etiquetas no topo, polaroides da lista embaixo
# =========================================================
TEXTO_LISTAS_VAZIO = (
    "Nenhuma lista ainda...\n\n"
    "crie uma aqui em cima (\"pra chorar\", \"com a família\", \"maratona de Natal\")\n"
    "e, na página de cada filme, toque em  🏷 colocar numa lista."
)
estado_listas = {"aberta": None}


def nova_lista(event=None):
    from tkinter import simpledialog
    nome = simpledialog.askstring("Nova lista", "Nome da lista (ex.: pra chorar):", parent=janela)
    if not nome:
        return
    try:
        estado_listas["aberta"] = usuario.criar_lista(nome)
    except ValueError as erro:
        messagebox.showinfo("Nova lista", str(erro), parent=janela)
        return
    atualizar_meus_filmes()


def renomear_lista_aberta(event=None):
    from tkinter import simpledialog
    atual = estado_listas["aberta"]
    nome = simpledialog.askstring("Renomear lista", "Novo nome:", initialvalue=atual, parent=janela)
    if not nome or nome == atual:
        return
    try:
        estado_listas["aberta"] = usuario.renomear_lista(atual, nome)
    except ValueError as erro:
        messagebox.showinfo("Renomear lista", str(erro), parent=janela)
        return
    atualizar_meus_filmes(voltar_ao_topo=False)


def apagar_lista_aberta(event=None):
    atual = estado_listas["aberta"]
    quantidade = len(usuario.dados_usuario["listas"].get(atual, {}).get("titulos", {}))
    if not messagebox.askyesno(
        "Apagar lista",
        f'Apagar a lista "{atual}"?\n\nOs {quantidade} títulos dela continuam no diário; só a lista some.',
        parent=janela
    ):
        return
    usuario.apagar_lista(atual)
    estado_listas["aberta"] = None
    atualizar_meus_filmes()


def desenhar_listas():
    limpar_grade(widgets_meus_filmes, imagens_meus_filmes)
    escala = escala_da_tela(scroll_meus_filmes)

    def px(valor):
        return int(valor * escala)

    nomes = usuario.nomes_das_listas()
    if estado_listas["aberta"] not in nomes:
        estado_listas["aberta"] = nomes[0] if nomes else None

    topo = tk.Frame(scroll_meus_filmes, bg=COR_FUNDO)
    topo.grid(row=0, column=0, columnspan=COLUNAS_CARDS, sticky="ew", padx=(px(10), px(40)), pady=(px(12), px(6)))
    widgets_meus_filmes.append(topo)

    # Etiquetas de papel, uma por lista (a aberta fica vermelha)
    linha = None
    for posicao, nome in enumerate(nomes + ["+ nova lista"]):
        if posicao % 5 == 0:
            linha = tk.Frame(topo, bg=COR_FUNDO)
            linha.pack(anchor="w", pady=(0, px(6)))
        eh_nova = posicao == len(nomes)
        aberta = nome == estado_listas["aberta"]
        quantidade = "" if eh_nova else f"  ({len(usuario.dados_usuario['listas'][nome]['titulos'])})"
        etiqueta = tk.Label(
            linha, text=f"🏷 {nome}{quantidade}" if not eh_nova else nome,
            font=(FONTE_MANUSCRITA, -px(18), "bold"),
            fg=COR_TEXTO_CAPA if aberta else (COR_VERMELHO if eh_nova else COR_TEXTO),
            bg=COR_VERMELHO if aberta else (COR_FUNDO if eh_nova else CORES_PAPEL_SELO[posicao % len(CORES_PAPEL_SELO)]),
            highlightbackground=COR_BORDA_PAPEL, highlightthickness=0 if eh_nova else 1,
            padx=px(12), pady=px(5), cursor="hand2"
        )
        etiqueta.pack(side="left", padx=(0, px(8)), pady=(px((posicao % 2) * 3), 0))
        if eh_nova:
            etiqueta.bind("<Button-1>", nova_lista)
        else:
            etiqueta.bind("<Button-1>", lambda event, nome=nome: (estado_listas.update(aberta=nome), atualizar_meus_filmes()))

    if estado_listas["aberta"] is None:
        vazio = tk.Label(
            topo, text=TEXTO_LISTAS_VAZIO, font=(FONTE_MANUSCRITA, -px(18)), fg=COR_TEXTO_SECUNDARIO,
            bg=COR_FUNDO, justify="center"
        )
        vazio.pack(pady=(px(40), 0))
        return

    aberta = estado_listas["aberta"]
    titulo = tk.Frame(topo, bg=COR_FUNDO)
    titulo.pack(anchor="w", pady=(px(10), px(4)))
    tk.Label(
        titulo, text=aberta, font=(FONTE_MANUSCRITA, -px(30), "bold"), fg=COR_TITULO_MANUSCRITO, bg=COR_FUNDO
    ).pack(side="left")
    for texto, acao in (("✎ renomear", renomear_lista_aberta), ("✕ apagar lista", apagar_lista_aberta)):
        link = tk.Label(titulo, text=texto, font=(FONTE_MANUSCRITA, -px(15)), fg=COR_TEXTO_SUAVE, bg=COR_FUNDO, cursor="hand2")
        link.pack(side="left", padx=(px(16), 0), pady=(px(10), 0))
        link.bind("<Button-1>", acao)
    tk.Frame(topo, bg=COR_MARCA_TEXTO, height=px(6), width=px(220)).pack(anchor="w", pady=(0, px(6)))

    filmes_da_lista = usuario.filmes_da_lista_tematica(aberta, filmes.filmes)
    if not filmes_da_lista:
        tk.Label(
            topo, text="lista vazia por enquanto: abra um filme e toque em  🏷 colocar numa lista",
            font=(FONTE_MANUSCRITA, -px(17)), fg=COR_TEXTO_SUAVE, bg=COR_FUNDO
        ).pack(anchor="w", pady=(px(16), 0))
        return
    for posicao, filme in enumerate(filmes_da_lista[:LIMITE_CARDS_GRADE]):
        criar_card_filme(
            scroll_meus_filmes, filme, 1 + posicao // COLUNAS_CARDS, posicao % COLUNAS_CARDS,
            widgets_meus_filmes, imagens_meus_filmes
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

    if seletor_aba.get() == ABA_LISTAS:
        desenhar_listas()
        return
    preencher_grade(
        scroll_meus_filmes,
        usuario.filmes_da_lista("favoritos", filmes.filmes),
        widgets_meus_filmes,
        imagens_meus_filmes,
        TEXTO_FAVORITOS_VAZIO
    )


# Partes que vêm ANTES desta usam estes nomes pela ponte (veja tela/ponte.py).
ponte.registrar(
    atualizar_meus_filmes=atualizar_meus_filmes,
)
