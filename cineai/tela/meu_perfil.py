"""
tela/meu_perfil.py — Página Meu perfil: gosto, "o que o seu diário diz sobre você" e Para você.

Parte da janela do CineAI (veja cineai/interface.py, que junta todas as partes).
"""
from cineai.tela.retrospectiva import *  # noqa: F401,F403  (tudo das partes anteriores)
from cineai.tela.ponte import ponte


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


# Partes que vêm ANTES desta usam estes nomes pela ponte (veja tela/ponte.py).
ponte.registrar(
    atualizar_pagina_perfil=atualizar_pagina_perfil,
)
