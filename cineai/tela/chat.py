"""
tela/chat.py — O chat em bilhetes de papel (Início e página Chat CineAI) e o envio das mensagens para o filmes.py.

Parte da janela do CineAI (veja cineai/interface.py, que junta todas as partes).
"""
from cineai.tela.inicio import *  # noqa: F401,F403  (tudo das partes anteriores)
from cineai.tela.ponte import ponte


# =========================================================
# CHAT COMO TROCA DE BILHETES
# =========================================================
# Cada mensagem é um papelzinho de verdade (widgets simples do Tk, leves):
#   CineAI -> ficha de papel branco à esquerda, com faixa vermelha, fita e "✦ CineAI"
#   você   -> anotação em caneta azul, letra de mão, à direita, assinada "— você"
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
            ponte.adicionar_ao_historico(resposta["filme"])

        # A nota foi dada pelo chat ("Dou 5 estrelas para Shrek") ou você
        # disse "Já vi esse": atualiza selos e a página Meus filmes.
        if resposta.get("atualizou_usuario") or resposta["tipo"] == "usuario_atualizado":
            ao_mudar_listas()

        ponte.atualizar_painel_rag()  # o caminho desta resposta aparece no Painel do RAG

        # "Interestelar ou Matrix?": abre os dois lado a lado
        if resposta["tipo"] == "comparacao":
            abrir_comparacao(resposta["comparacao"])

        # "Como foi meu ano no cinema?": abre as páginas da retrospectiva
        if resposta["tipo"] == "retrospectiva":
            ponte.abrir_retrospectiva(resposta.get("ano"))

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
    ponte.historico_recomendacoes.clear()
    ponte.atualizar_recomendacoes()
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
            ponte.adicionar_ao_historico(filme)
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


# Partes que vêm ANTES desta usam estes nomes pela ponte (veja tela/ponte.py).
ponte.registrar(
    processar=processar,
)
