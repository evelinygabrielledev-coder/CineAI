"""
interface.py — a janela do CineAI.

O código da janela fica em cineai/tela/, uma parte por arquivo, nesta ordem
(cada parte usa as anteriores):

    base             A base da janela: imports, cores, fontes, funções de apoio e a janela principal (janela = ctk.CTk()).
    recortes         Polaroides desenhadas com o Pillow (os cards de filme), selinhos ❤/✅ e a grade de cards.
    janela_detalhes  A página de um filme (o diário aberto) e a janela que compara dois títulos.
    menu_lateral     A capa vermelha do lado esquerdo, os ícones desenhados à mão e a área onde as páginas aparecem.
    inicio           Página Início: letreiro, película 5-4-3-2-1, busca em forma de ingresso e os recortes recomendados.
    chat             O chat em bilhetes de papel (Início e página Chat CineAI) e o envio das mensagens para o filmes.py.
    catalogo         Páginas Catálogo (busca e filtros) e Recomendações.
    meu_diario       Página Meu diário: Capa, Diário (entradas por mês), Favoritos, Quero assistir e o backup.
    retrospectiva    Retrospectiva do ano (páginas viradas uma a uma) e a janelinha do Diário em PDF.
    meu_perfil       Página Meu perfil: gosto, "o que o seu diário diz sobre você" e Para você.
    painel_rag       Painel do RAG: o caminho de cada resposta, com as etapas e os tempos.

Aqui ficam só a navegação entre as páginas e a inicialização.
O main.py chama interface.iniciar().
"""
from cineai.tela.painel_rag import *  # noqa: F401,F403  (todas as partes da janela)


# =========================================================
# NAVEGAÇÃO
# =========================================================
todas_paginas = [
    pagina_inicio,
    pagina_catalogo,
    pagina_recomendacoes,
    pagina_meus_filmes,
    pagina_perfil,
    pagina_chat,
    pagina_rag
]


def mostrar_pagina(pagina, botao_ativo, entrada_foco=None):
    for pagina_existente in todas_paginas:
        pagina_existente.grid_forget()

    pagina.grid(row=0, column=0, sticky="nsew")

    # O botão da página aberta vira um "ingresso" creme com letra vermelha.
    for botao in botoes_menu:
        botao.configure(fg_color="transparent", text_color=COR_TEXTO_CAPA, hover_color=COR_MENU_HOVER)
    botao_ativo.configure(fg_color=COR_INGRESSO, text_color=COR_VERMELHO, hover_color=COR_INGRESSO)

    if entrada_foco is not None:
        entrada_foco.focus()


def mostrar_inicio():
    mostrar_pagina(pagina_inicio, botao_inicio, entrada_busca)


def mostrar_catalogo():
    mostrar_pagina(pagina_catalogo, botao_buscar_menu, entrada_catalogo)


def mostrar_recomendacoes():
    mostrar_pagina(pagina_recomendacoes, botao_recomendacoes)


def mostrar_meus_filmes():
    mostrar_pagina(pagina_meus_filmes, botao_meus_filmes_menu)
    pagina_meus_filmes.update_idletasks()  # garante que a página já está visível
    atualizar_meus_filmes()


def mostrar_perfil():
    mostrar_pagina(pagina_perfil, botao_perfil_menu)
    pagina_perfil.update_idletasks()  # garante que a página já está visível
    atualizar_pagina_perfil()


def mostrar_chat():
    mostrar_pagina(pagina_chat, botao_chat_menu, entrada_chat_completo)
    chat_completo.see("end")


botao_inicio.configure(command=mostrar_inicio)
botao_buscar_menu.configure(command=mostrar_catalogo)
botao_recomendacoes.configure(command=mostrar_recomendacoes)
botao_meus_filmes_menu.configure(command=mostrar_meus_filmes)
botao_perfil_menu.configure(command=mostrar_perfil)
botao_chat_menu.configure(command=mostrar_chat)
botao_rag_menu.configure(command=lambda: mostrar_pagina(pagina_rag, botao_rag_menu))


# =========================================================
# INICIALIZAÇÃO
# =========================================================
for coluna in range(COLUNAS_CARDS):
    criar_card_recomendacao(coluna)  # os 4 recortes da Home ("cole aqui")

# Backup automático (se o último tem mais de 7 dias) — silencioso
try:
    usuario.backup_automatico_se_precisar()
except OSError as erro_backup:
    print(f"Não consegui fazer o backup automático: {erro_backup}")

# Sugestão da noite: o primeiro recorte já vem colado, com um bilhete no chat
sugestao_da_noite, motivo_da_sugestao, _ = filmes.sugestao_da_noite()
if sugestao_da_noite is not None:
    adicionar_filme_aos_cards(sugestao_da_noite)
    adicionar_mensagem(
        NOME_IA,
        f"🌙 Sugestão da noite: {filmes.descrever_filme_curto(sugestao_da_noite)} — {motivo_da_sugestao}. "
        'Clique no recorte para abrir, ou me pergunte "o que eu vejo hoje?".'
    )

atualizar_catalogo()
atualizar_recomendacoes()
atualizar_meus_filmes()
atualizar_painel_rag()
mostrar_inicio()
def iniciar():
    """Abre a janela do CineAI (o main.py chama isto)."""
    janela.mainloop()


if __name__ == "__main__":
    iniciar()
