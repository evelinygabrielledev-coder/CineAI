"""
tela/catalogo.py — Páginas Catálogo (busca e filtros) e Recomendações.

Parte da janela do CineAI (veja cineai/interface.py, que junta todas as partes).
"""
from cineai.tela.chat import *  # noqa: F401,F403  (tudo das partes anteriores)
from cineai.tela.ponte import ponte


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


# Partes que vêm ANTES desta usam estes nomes pela ponte (veja tela/ponte.py).
ponte.registrar(
    adicionar_ao_historico=adicionar_ao_historico,
    atualizar_catalogo=atualizar_catalogo,
    atualizar_recomendacoes=atualizar_recomendacoes,
    esconder_assistidos_var=esconder_assistidos_var,
    filtro_ordem=filtro_ordem,
    historico_recomendacoes=historico_recomendacoes,
)
