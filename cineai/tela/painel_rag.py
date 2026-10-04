"""
tela/painel_rag.py — Painel do RAG: o caminho de cada resposta, com as etapas e os tempos.

Parte da janela do CineAI (veja cineai/interface.py, que junta todas as partes).
"""
from cineai.tela.meu_perfil import *  # noqa: F401,F403  (tudo das partes anteriores)
from cineai.tela.ponte import ponte


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


# Partes que vêm ANTES desta usam estes nomes pela ponte (veja tela/ponte.py).
ponte.registrar(
    atualizar_painel_rag=atualizar_painel_rag,
)
