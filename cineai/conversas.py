"""
Histórico de conversas do CineAI, salvo em conversas.json.

Cada conversa guarda as mensagens e os filmes recomendados nela.
Exemplo:

{
  "conversas": [
    {
      "id": "20261003-115800",
      "titulo": "Quero uma animação de 2001 com Eddie Murphy",
      "criada_em": "2026-10-03 11:58",
      "atualizada_em": "2026-10-03 12:04",
      "mensagens": [
        {"autor": "voce", "texto": "Quero uma animação...", "hora": "11:58"},
        {"autor": "cineai", "texto": "Shrek (2001) é...", "hora": "11:58", "filme": "808"}
      ],
      "filmes_recomendados": ["808"]
    }
  ]
}

Este módulo não sabe nada de interface.
"""

import json
import os
from datetime import datetime
from pathlib import Path


# Os testes automáticos usam outra pasta para não mexer nas suas conversas.
from cineai.caminhos import PASTA_USUARIO
from cineai.usuario import trazer_arquivo_do_lugar_antigo

PASTA_DADOS = PASTA_USUARIO                       # dados/ (os testes trocam por uma pasta temporária)
CAMINHO_CONVERSAS = PASTA_DADOS / "conversas.json"
trazer_arquivo_do_lugar_antigo("conversas.json")

MAXIMO_CONVERSAS = 50          # as mais antigas são apagadas automaticamente
TAMANHO_MAXIMO_TITULO = 45

AUTOR_VOCE = "voce"
AUTOR_CINEAI = "cineai"


# =========================================================
# ARQUIVO
# =========================================================
def carregar_todas():
    if not CAMINHO_CONVERSAS.exists():
        return []

    try:
        with open(CAMINHO_CONVERSAS, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
    except (json.JSONDecodeError, OSError) as erro:
        caminho_backup = CAMINHO_CONVERSAS.with_suffix(".corrompido.json")
        try:
            CAMINHO_CONVERSAS.replace(caminho_backup)
            print(f"conversas.json estava com problema ({erro}). Cópia salva em {caminho_backup.name}.")
        except OSError:
            pass
        return []

    lista = dados.get("conversas", []) if isinstance(dados, dict) else []
    return [conversa for conversa in lista if isinstance(conversa, dict) and conversa.get("id")]


def salvar_todas():
    """Grava num arquivo temporário e troca depois, para nunca corromper o original."""
    # Só as conversas com pelo menos uma mensagem sua vão para o arquivo.
    com_mensagens = [conversa for conversa in lista_conversas if conversa["mensagens"]]

    # Mantém as mais recentes
    com_mensagens.sort(key=lambda conversa: conversa["atualizada_em"], reverse=True)
    com_mensagens = com_mensagens[:MAXIMO_CONVERSAS]

    caminho_temporario = CAMINHO_CONVERSAS.with_suffix(".tmp")
    with open(caminho_temporario, "w", encoding="utf-8") as arquivo:
        json.dump({"conversas": com_mensagens}, arquivo, ensure_ascii=False, indent=2)
    caminho_temporario.replace(CAMINHO_CONVERSAS)


lista_conversas = carregar_todas()


def recarregar():
    """Lê o conversas.json de novo (depois de restaurar um backup)."""
    lista_conversas[:] = carregar_todas()


# =========================================================
# AUXILIARES
# =========================================================
def agora_texto():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def gerar_id():
    """'20261003-115800-1' — data/hora + contador, para nunca repetir."""
    base = datetime.now().strftime("%Y%m%d-%H%M%S")
    ids_existentes = {conversa["id"] for conversa in lista_conversas}

    contador = 1
    while f"{base}-{contador}" in ids_existentes:
        contador += 1
    return f"{base}-{contador}"


def criar_titulo(texto):
    """Primeira mensagem, cortada: 'Quero uma animação de 2001 com Eddie…'."""
    titulo = " ".join(str(texto).split())
    if len(titulo) > TAMANHO_MAXIMO_TITULO:
        titulo = titulo[:TAMANHO_MAXIMO_TITULO - 1].rstrip() + "…"
    return titulo


# =========================================================
# OPERAÇÕES
# =========================================================
def nova_conversa():
    """Cria uma conversa vazia. Ela só vai para o arquivo quando você mandar algo."""
    conversa = {
        "id": gerar_id(),
        "titulo": "Nova conversa",
        "criada_em": agora_texto(),
        "atualizada_em": agora_texto(),
        "mensagens": [],
        "filmes_recomendados": [],
    }
    lista_conversas.append(conversa)
    return conversa


def registrar_mensagem(conversa, autor, texto, chave_filme=None):
    """Guarda uma mensagem (e o filme recomendado, se houver) e salva."""
    mensagem = {
        "autor": autor,
        "texto": texto,
        "hora": datetime.now().strftime("%H:%M"),
    }

    if chave_filme is not None:
        mensagem["filme"] = chave_filme
        if chave_filme not in conversa["filmes_recomendados"]:
            conversa["filmes_recomendados"].append(chave_filme)

    # A primeira mensagem sua vira o título
    if autor == AUTOR_VOCE and not any(m["autor"] == AUTOR_VOCE for m in conversa["mensagens"]):
        conversa["titulo"] = criar_titulo(texto)

    conversa["mensagens"].append(mensagem)
    conversa["atualizada_em"] = agora_texto()
    salvar_todas()


def conversas_salvas():
    """Conversas com mensagens, da mais recente para a mais antiga."""
    salvas = [conversa for conversa in lista_conversas if conversa["mensagens"]]
    salvas.sort(key=lambda conversa: conversa["atualizada_em"], reverse=True)
    return salvas


def buscar_por_id(id_conversa):
    for conversa in lista_conversas:
        if conversa["id"] == id_conversa:
            return conversa
    return None


def apagar(id_conversa):
    conversa = buscar_por_id(id_conversa)
    if conversa is not None:
        lista_conversas.remove(conversa)
        salvar_todas()


def rotulo(conversa):
    """Texto para a lista: '03/10 11:58 · Quero uma animação de 2001…'."""
    data_hora = conversa["atualizada_em"]  # "2026-10-03 11:58:00"
    dia_mes = f"{data_hora[8:10]}/{data_hora[5:7]}"
    hora = data_hora[11:16]
    return f"{dia_mes} {hora} · {conversa['titulo']}"