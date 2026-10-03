"""
rastreio.py — o "gravador" do Painel do RAG.

Cada mensagem enviada ao CineAI gera um RASTRO: a lista das etapas por
onde a resposta passou (regras, filtros, IA, busca semântica, ranking...),
com o tempo de cada uma. A interface mostra esse rastro na página
"Painel do RAG".

Como usar dentro do filmes.py:
    rastro.iniciar("Quero um filme sobre ogros")
    rastro.etapa("🔎", "Filtros", "nenhum filtro encontrado")
    rastro.tabela("📊", "Similaridade", colunas, linhas)
    rastro.finalizar(resultado)

Se nenhum rastro foi iniciado (ex.: nos testes que chamam funções soltas),
as chamadas simplesmente não fazem nada.
"""
import time
from datetime import datetime

MAXIMO_RASTROS_GUARDADOS = 30   # últimas 30 mensagens ficam no painel
MAXIMO_LINHAS_TABELA = 5        # top 5 de cada ranking
TAMANHO_MAXIMO_TEXTO = 220      # prompts e respostas longos são cortados


def encurtar(texto, tamanho=TAMANHO_MAXIMO_TEXTO):
    texto = " ".join(str(texto).split())  # junta quebras de linha e espaços
    if len(texto) <= tamanho:
        return texto
    return texto[: tamanho - 1] + "…"


def formatar_ms(milissegundos):
    """12.3 -> '12 ms' | 1530 -> '1,53 s'."""
    if milissegundos < 1000:
        return f"{milissegundos:.0f} ms"
    return f"{milissegundos / 1000:.2f} s".replace(".", ",")


class Rastreio:

    def __init__(self):
        self.atual = None
        self.historico = []  # rastros finalizados, do mais novo para o mais antigo

    # ---------------- início e fim ----------------
    def iniciar(self, mensagem):
        agora = time.perf_counter()
        self.atual = {
            "mensagem": mensagem,
            "horario": datetime.now().strftime("%H:%M:%S"),
            "etapas": [],
            "chamadas_ia": 0,
            "tempo_ia_ms": 0.0,
            "total_ms": 0.0,
            "_inicio": agora,
            "_ultimo": agora,
        }

    def finalizar(self, resultado=None, erro=None):
        """Fecha o rastro, guarda no histórico e devolve uma cópia limpa."""
        if self.atual is None:
            return None

        if erro is not None:
            self.etapa("❌", "Erro", encurtar(erro))
        elif resultado is not None:
            filme = resultado.get("filme")
            detalhe = f'tipo da resposta: {resultado.get("tipo")}'
            if filme is not None:
                detalhe += f' • filme: {filme["nome"]} ({filme.get("ano", "")})'
            self.etapa("✅", "Resposta", detalhe)

        rastro_pronto = {
            chave: valor for chave, valor in self.atual.items()
            if not chave.startswith("_")
        }
        rastro_pronto["total_ms"] = (time.perf_counter() - self.atual["_inicio"]) * 1000

        self.historico.insert(0, rastro_pronto)
        del self.historico[MAXIMO_RASTROS_GUARDADOS:]

        self.atual = None
        return rastro_pronto

    # ---------------- etapas ----------------
    def _tempo_desde_ultima(self):
        agora = time.perf_counter()
        milissegundos = (agora - self.atual["_ultimo"]) * 1000
        self.atual["_ultimo"] = agora
        return milissegundos

    def etapa(self, icone, titulo, detalhe=""):
        """Uma etapa simples: ícone, título e uma frase explicando."""
        if self.atual is None:
            return
        self.atual["etapas"].append({
            "icone": icone,
            "titulo": titulo,
            "detalhe": detalhe,
            "ms": self._tempo_desde_ultima(),
            "tabela": None,
        })

    def tabela(self, icone, titulo, colunas, linhas, detalhe=""):
        """
        Etapa com ranking. Cada linha: (nome, [valores em texto], barra 0..1).
        A barra é desenhada no painel para comparar as pontuações.
        """
        if self.atual is None:
            return
        self.atual["etapas"].append({
            "icone": icone,
            "titulo": titulo,
            "detalhe": detalhe,
            "ms": self._tempo_desde_ultima(),
            "tabela": {
                "colunas": colunas,
                "linhas": linhas[:MAXIMO_LINHAS_TABELA],
            },
        })

    def chamada_ia(self, finalidade, prompt, resposta, milissegundos):
        """Registra uma chamada ao Ollama com o tempo exato que ela levou."""
        if self.atual is None:
            return
        self.atual["chamadas_ia"] += 1
        self.atual["tempo_ia_ms"] += milissegundos

        # O tempo "desde a última etapa" inclui a IA; descontamos para não contar duas vezes.
        self._tempo_desde_ultima()

        self.atual["etapas"].append({
            "icone": "🤖",
            "titulo": f"IA ({finalidade})",
            "detalhe": f'resposta: "{encurtar(resposta, 120)}"\nprompt: {encurtar(prompt)}',
            "ms": milissegundos,
            "tabela": None,
        })


# Um único gravador para o programa todo.
rastro = Rastreio()