"""
tela/retrospectiva.py — Retrospectiva do ano (páginas viradas uma a uma), a janelinha do Diário em PDF e a importação do Letterboxd.

Parte da janela do CineAI (veja cineai/interface.py, que junta todas as partes).
"""
from cineai.tela.meu_diario import *  # noqa: F401,F403  (tudo das partes anteriores)
from cineai.tela.ponte import ponte


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
    if numeros.get("meta"):
        if numeros["titulos"] >= numeros["meta"]:
            frases.append(f"🎯 meta de {numeros['meta']} títulos: batida! 🎉")
        else:
            frases.append(f"🎯 meta: {numeros['titulos']} de {numeros['meta']} títulos")
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
    if numeros.get("meta") and numeros["titulos"] >= numeros["meta"]:
        frase = f"você bateu a meta de {numeros['meta']} títulos em {ano}! 🎉"
    elif ano == date.today().year:
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
        criar_link_letterboxd(folha, escala)
        return
    linha = tk.Frame(folha, bg=COR_PAPEL)
    linha.pack(pady=(0, px(10)))
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
    criar_link_letterboxd(folha, escala)


# ---------- Importar do Letterboxd ----------
def criar_link_letterboxd(folha, escala):
    def px(valor):
        return int(valor * escala)

    link = tk.Label(
        folha, text="📥  trazer meu histórico do Letterboxd", font=(FONTE_MANUSCRITA, -px(18), "bold"),
        fg=COR_AZUL_CANETA, bg=COR_PAPEL, cursor="hand2"
    )
    link.pack(pady=(0, px(26)))
    link.bind("<Button-1>", abrir_importar_letterboxd)


def abrir_importar_letterboxd(event=None):
    """Escolhe o .zip do Letterboxd, mostra o que vai entrar e importa (com backup antes)."""
    from tkinter import filedialog

    if not messagebox.askokcancel(
        "Importar do Letterboxd",
        "No Letterboxd, vá em Settings › Data › Export your data.\n"
        "Ele baixa um arquivo .zip: escolha esse arquivo na próxima janela.\n\n"
        "Nada do que você já tem no CineAI é apagado, e antes de importar\n"
        "o CineAI faz um backup do diário.",
        parent=janela
    ):
        return
    caminho = filedialog.askopenfilename(
        parent=janela, title="Escolha o .zip do Letterboxd",
        filetypes=[("Exportação do Letterboxd", "*.zip"), ("Arquivo CSV", "*.csv"), ("Todos os arquivos", "*.*")]
    )
    if not caminho:
        return

    try:
        previa = letterboxd.importar(filmes.filmes, caminho, simular=True)
    except (ValueError, OSError, UnicodeDecodeError) as erro:
        messagebox.showerror("Importar do Letterboxd", str(erro), parent=janela)
        return

    if not messagebox.askyesno(
        "Importar do Letterboxd",
        "Vai entrar no seu diário:\n\n" + letterboxd.texto_do_resumo(previa) + "\n\nImportar agora?",
        parent=janela
    ):
        return

    resumo = letterboxd.importar(filmes.filmes, caminho)
    ao_mudar_listas()
    mensagem = "Pronto! ✓\n\n" + letterboxd.texto_do_resumo(resumo)
    if resumo["nao_encontrados"]:
        exemplos = ", ".join(resumo["nao_encontrados"][:5])
        mensagem += (
            f"\nAlguns: {exemplos}{'...' if len(resumo['nao_encontrados']) > 5 else ''}\n\n"
            "Para trazer esses também (busca no TMDB, precisa da chave no .env):\n"
            "python importadores/importar_letterboxd.py arquivo.zip --adicionar"
        )
    messagebox.showinfo("Importar do Letterboxd", mensagem, parent=janela)


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


# Partes que vêm ANTES desta usam estes nomes pela ponte (veja tela/ponte.py).
ponte.registrar(
    abrir_retrospectiva=abrir_retrospectiva,
    criar_botao_retrospectiva=criar_botao_retrospectiva,
    criar_link_letterboxd=criar_link_letterboxd,
)
