"""
Testes automáticos do CineAI.

Como rodar (dentro da pasta do projeto):

    python testes/testes.py              -> modo RÁPIDO: leva segundos.
                                     Usa um catálogo de teste com 21 filmes e uma
                                     IA simulada. Não precisa do Ollama aberto.

    python testes/testes.py --completo   -> modo COMPLETO: usa o seu dados/filmes.json de verdade,
                                     o modelo de embeddings e o Ollama (deixe aberto).
                                     Mais lento, mas testa o app como ele é.

Os seus dados (usuario.json e conversas.json) NUNCA são tocados:
os testes usam uma pasta temporária, apagada no final.

Cada teste tem uma frase explicando o que ele confere. Quando você corrigir um bug,
transforme o caso que falhou num teste novo aqui: assim, se ele voltar, você descobre na hora.
"""

import hashlib
import importlib
import json
import math
import os
import re
import shutil
import sys
import tempfile
import types
import unicodedata
import unittest
from datetime import date
from pathlib import Path

import numpy as np

# A pasta do projeto (um nível acima de testes/) entra no caminho do Python,
# para "from cineai import ..." funcionar rodando daqui.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# =========================================================
# MODO E PASTA TEMPORÁRIA
# =========================================================
MODO_COMPLETO = "--completo" in sys.argv
sys.argv = [argumento for argumento in sys.argv if argumento != "--completo"]

PASTA_TEMPORARIA = Path(tempfile.mkdtemp(prefix="cineai_testes_"))
os.environ["CINEAI_PASTA_USUARIO"] = str(PASTA_TEMPORARIA)


# =========================================================
# CATÁLOGO DE TESTE (modo rápido)
# =========================================================
def filme_de_teste(id_tmdb, nome, ano, genero, diretor, elenco, sinopse,
                   votos, rotten, imdb, metacritic, duracao):
    return {
        "id": id_tmdb, "nome": nome, "titulo_original": nome, "ano": ano,
        "genero": genero, "diretor": diretor, "elenco": elenco, "sinopse": sinopse,
        "duracao_minutos": duracao, "nota_tmdb": round(imdb - 0.2, 1),
        "votos_tmdb": votos, "poster": None, "premios": [], "indicacoes": [],
        "rotten_tomatoes": {"critica": rotten, "publico": None},
        "nota_imdb": imdb, "metacritic": metacritic,
    }


def serie_de_teste(id_tmdb, nome, ano, ano_final, genero, criadores, elenco, sinopse,
                   votos, rotten, imdb, duracao_episodio, temporadas, episodios, status):
    serie = filme_de_teste(id_tmdb, nome, ano, genero, criadores, elenco, sinopse,
                           votos, rotten, imdb, None, duracao_episodio)
    serie.update({
        "tipo": "serie", "ano_final": ano_final, "temporadas": temporadas,
        "episodios": episodios, "status": status,
    })
    return serie


CATALOGO_DE_TESTE = [
    filme_de_teste(808, "Shrek", 2001, "Animação, Comédia, Fantasia, Aventura, Família",
                   "Andrew Adamson, Vicky Jenson", ["Mike Myers", "Eddie Murphy", "Cameron Diaz"],
                   "Um ogro mal-humorado vive num pântano e aceita resgatar uma princesa aprisionada "
                   "por um dragão, acompanhado de um burro falante.", 17000, 88, 7.9, 84, 90),
    filme_de_teste(809, "Shrek 2", 2004, "Animação, Comédia, Fantasia, Aventura, Família",
                   "Andrew Adamson, Kelly Asbury, Conrad Vernon", ["Mike Myers", "Eddie Murphy", "Cameron Diaz"],
                   "Shrek e Fiona visitam os pais da princesa no reino de Tão Tão Distante, e o ogro "
                   "precisa conquistar o sogro rei.", 12000, 89, 7.3, 75, 93),
    filme_de_teste(862, "Toy Story: Um Mundo de Aventuras", 1995, "Animação, Aventura, Família, Comédia",
                   "John Lasseter", ["Tom Hanks", "Tim Allen"],
                   "Woody, um cowboy de brinquedo, sente ciúmes quando o astronauta de brinquedo "
                   "Buzz Lightyear chega ao quarto de Andy.", 18000, 100, 8.3, 96, 81),
    filme_de_teste(863, "Toy Story 2", 1999, "Animação, Comédia, Família",
                   "John Lasseter", ["Tom Hanks", "Tim Allen"],
                   "Woody é roubado por um colecionador de brinquedos e Buzz Lightyear lidera uma "
                   "missão de resgate.", 13000, 100, 7.9, 88, 92),
    filme_de_teste(8587, "O Rei Leão", 1994, "Família, Animação, Drama",
                   "Roger Allers, Rob Minkoff", ["Matthew Broderick", "James Earl Jones"],
                   "O jovem leão Simba foge depois da morte do pai e precisa voltar para enfrentar "
                   "o tio Scar e assumir o trono.", 17000, 93, 8.5, 88, 88),
    filme_de_teste(420818, "O Rei Leão", 2019, "Aventura, Drama, Família",
                   "Jon Favreau", ["Donald Glover", "Beyoncé"],
                   "Nova versão realista da história do leão Simba, que foge após a morte do pai "
                   "e retorna para reconquistar seu reino.", 9000, 52, 6.8, 55, 118),
    filme_de_teste(157336, "Interestelar", 2014, "Aventura, Drama, Ficção científica",
                   "Christopher Nolan", ["Matthew McConaughey", "Anne Hathaway", "Jessica Chastain"],
                   "Com a Terra morrendo, um grupo de astronautas viaja por um buraco de minhoca "
                   "procurando um novo planeta habitável para a humanidade.", 34000, 73, 8.7, 74, 169),
    filme_de_teste(27205, "A Origem", 2010, "Ação, Ficção científica, Aventura",
                   "Christopher Nolan", ["Leonardo DiCaprio", "Joseph Gordon-Levitt", "Elliot Page"],
                   "Um ladrão especializado em invadir sonhos recebe a missão de plantar uma ideia "
                   "na mente de um herdeiro.", 36000, 87, 8.8, 74, 148),
    filme_de_teste(374720, "Dunkirk", 2017, "Guerra, Ação, Drama",
                   "Christopher Nolan", ["Fionn Whitehead", "Tom Hardy"],
                   "Soldados aliados cercados na praia de Dunkirk tentam escapar durante a Segunda "
                   "Guerra Mundial.", 16000, 92, 7.8, 94, 106),
    filme_de_teste(597, "Titanic", 1997, "Drama, Romance",
                   "James Cameron", ["Leonardo DiCaprio", "Kate Winslet"],
                   "Um jovem artista pobre e uma moça rica se apaixonam a bordo do navio Titanic "
                   "em sua viagem inaugural.", 25000, 88, 7.9, 75, 194),
    filme_de_teste(106646, "O Lobo de Wall Street", 2013, "Crime, Drama, Comédia",
                   "Martin Scorsese", ["Leonardo DiCaprio", "Jonah Hill", "Margot Robbie"],
                   "A ascensão e queda de um corretor da bolsa de Nova York entre fraudes, festas "
                   "e excessos.", 23000, 80, 8.2, 75, 180),
    filme_de_teste(646380, "Não Olhe para Cima", 2021, "Comédia, Ficção científica, Drama",
                   "Adam McKay", ["Leonardo DiCaprio", "Jennifer Lawrence"],
                   "Dois astrônomos descobrem um cometa que vai destruir a Terra e tentam alertar "
                   "uma humanidade distraída.", 9000, 56, 7.2, 49, 138),
    filme_de_teste(329, "Jurassic Park: O Parque dos Dinossauros", 1993, "Aventura, Ficção científica",
                   "Steven Spielberg", ["Sam Neill", "Laura Dern"],
                   "Um milionário cria um parque com dinossauros clonados a partir de DNA, mas os "
                   "animais escapam do controle.", 15000, 91, 8.2, 68, 127),
    filme_de_teste(539, "Psicose", 1960, "Terror, Thriller, Mistério",
                   "Alfred Hitchcock", ["Anthony Perkins", "Janet Leigh"],
                   "Uma secretária foge com dinheiro roubado e se hospeda num motel administrado "
                   "pelo estranho Norman Bates.", 9500, 97, 8.5, 97, 109),
    filme_de_teste(138843, "Invocação do Mal", 2013, "Terror, Thriller",
                   "James Wan", ["Vera Farmiga", "Patrick Wilson"],
                   "Investigadores paranormais ajudam uma família aterrorizada por uma presença "
                   "maligna numa casa assombrada.", 10000, 86, 7.5, 68, 112),
    filme_de_teste(350, "O Diabo Veste Prada", 2006, "Drama, Comédia",
                   "David Frankel", ["Meryl Streep", "Anne Hathaway"],
                   "Uma jovem jornalista consegue emprego como assistente da temida editora de uma "
                   "revista de moda.", 12000, 75, 6.9, 62, 109),
    filme_de_teste(1584, "Escola de Rock", 2003, "Comédia, Música, Família",
                   "Richard Linklater", ["Jack Black"],
                   "Um músico fracassado finge ser professor substituto e transforma seus alunos "
                   "numa banda de rock.", 8000, 91, 7.2, 82, 109),
    filme_de_teste(1417, "O Labirinto do Fauno", 2006, "Fantasia, Drama, Guerra",
                   "Guillermo del Toro", ["Ivana Baquero", "Sergi López"],
                   "Na Espanha de 1944, uma menina descobre um labirinto guardado por um fauno que "
                   "diz que ela é a princesa de um reino encantado.", 10000, 95, 8.2, 98, 118),
    filme_de_teste(137106, "Uma Aventura Lego", 2014, "Animação, Família, Aventura, Comédia, Fantasia",
                   "Phil Lord, Christopher Miller", ["Chris Pratt", "Elizabeth Banks"],
                   "Um bonequinho Lego comum é confundido com o escolhido que pode salvar o universo "
                   "de peças de montar.", 9000, 96, 7.7, 83, 100),
    filme_de_teste(286217, "Perdido em Marte", 2015, "Drama, Aventura, Ficção científica",
                   "Ridley Scott", ["Matt Damon", "Jessica Chastain"],
                   "Um astronauta é dado como morto e abandonado em Marte, e precisa sobreviver "
                   "sozinho no planeta até o resgate.", 20000, 91, 8.0, 80, 144),
    filme_de_teste(38365, "Gente Grande", 2010, "Comédia",
                   "Dennis Dugan", ["Adam Sandler", "Chris Rock", "Kevin James"],
                   "Cinco amigos de infância se reúnem com suas famílias num fim de semana numa "
                   "casa de lago.", 9000, 10, 6.0, 30, 102),

    # ---------- séries ----------
    serie_de_teste(1396, "Breaking Bad", 2008, 2013, "Drama, Crime",
                   "Vince Gilligan", ["Bryan Cranston", "Aaron Paul"],
                   "Um professor de química com câncer vira fabricante de drogas para garantir o "
                   "futuro da família.", 15000, 96, 9.5, 47, 5, 62, "Finalizada"),
    serie_de_teste(2316, "The Office", 2005, 2013, "Comédia",
                   "Greg Daniels", ["Steve Carell", "Rainn Wilson", "John Krasinski"],
                   "O dia a dia de um escritório de papel com um chefe atrapalhado e colegas "
                   "excêntricos, gravado como documentário.", 8000, 81, 9.0, 22, 9, 201, "Finalizada"),
    serie_de_teste(66732, "Stranger Things", 2016, None, "Drama, Mistério, Ficção científica, Fantasia",
                   "Matt Duffer, Ross Duffer", ["Millie Bobby Brown", "Winona Ryder"],
                   "Quando um garoto desaparece, os amigos dele encontram uma menina com poderes "
                   "e segredos do governo numa pequena cidade.", 17000, 92, 8.7, 51, 4, 34, "Em exibição"),
    # Mesmo id do Shrek (808) de propósito: filme e série NÃO podem se misturar.
    serie_de_teste(808, "Dark", 2017, 2020, "Drama, Mistério, Ficção científica, Crime",
                   "Baran bo Odar, Jantje Friese", ["Louis Hofmann", "Lisa Vicari"],
                   "O desaparecimento de duas crianças revela segredos de quatro famílias e uma "
                   "viagem no tempo numa cidade alemã.", 6500, 95, 8.7, 55, 3, 26, "Finalizada"),
]


# =========================================================
# IA SIMULADA (modo rápido)
# =========================================================
def normalizar(texto):
    texto = unicodedata.normalize("NFD", str(texto).lower())
    return "".join(caractere for caractere in texto if unicodedata.category(caractere) != "Mn")


class ModeloSimulado:
    """
    Embeddings de mentirinha: cada palavra (pelos 5 primeiros caracteres) vira
    uma posição do vetor. Textos com as mesmas palavras ficam parecidos.
    É simples, mas suficiente para testar a lógica sem baixar o modelo real.
    """
    DIMENSOES = 512

    def __init__(self, *argumentos, **opcoes):
        pass

    def _vetor(self, texto):
        vetor = np.zeros(self.DIMENSOES, dtype=np.float32)
        for palavra in re.findall(r"[a-z0-9]+", normalizar(texto)):
            if len(palavra) >= 4:
                posicao = int(hashlib.md5(palavra[:5].encode()).hexdigest(), 16) % self.DIMENSOES
                vetor[posicao] += 1
        tamanho = np.linalg.norm(vetor)
        return vetor / tamanho if tamanho else vetor

    def encode(self, entrada, **opcoes):
        if isinstance(entrada, list):
            return np.array([self._vetor(texto) for texto in entrada])
        return self._vetor(entrada)


def ollama_simulado(model, messages, think=None):
    """Responde como o qwen3 responderia nos casos que os testes usam."""
    prompt = messages[0]["content"]

    def resposta(texto):
        return types.SimpleNamespace(message=types.SimpleNamespace(content=texto))

    if "Classifique a mensagem" in prompt:
        mensagem = normalizar(prompt.split("Mensagem:")[-1].split("Responda somente")[0])
        if any(palavra in mensagem for palavra in ["capital", "quanto e", "trabalho de"]):
            return resposta("FORA")
        return resposta("<think>pensando...</think>BUSCA")

    if "Extraia apenas o assunto" in prompt:
        mensagem = prompt.split("Mensagem:")[-1].split("Resposta:")[0].strip()
        if " sobre " in mensagem:
            return resposta(mensagem.split(" sobre ", 1)[1].strip())
        return resposta("NENHUMA")

    if "Escreva o retrato" in prompt:
        # Cita o primeiro título das anotações (ou dos 5 estrelas), como o qwen faria.
        titulos = re.findall(r"^  \* (.+?) \(", prompt, flags=re.MULTILINE)
        cinco = re.findall(r"Deu 5 estrelas para: ([^,\n]+)", prompt)
        titulo = (titulos or cinco or ["um filme"])[0]
        return resposta(
            "<think>lendo...</think>Retrato: Você é daquelas pessoas que sentem os filmes por inteiro. "
            f"Quando fala de {titulo}, dá para perceber o carinho em cada palavra, e as suas notas "
            "mostram alguém generoso, mas atento aos detalhes."
        )

    return resposta("Resposta pela sinopse.")


# Onde assistir (como o importadores/importar_onde_assistir.py deixaria no filmes.json)
STREAMINGS_DE_TESTE = {
    "Shrek": ["Netflix", "Prime Video"],
    "Interestelar": ["Max", "Prime Video"],
    "Toy Story: Um Mundo de Aventuras": ["Disney+"],
    "Titanic": [],          # consultado, mas fora dos streamings por assinatura
}
for filme_teste in CATALOGO_DE_TESTE:
    if filme_teste["nome"] in STREAMINGS_DE_TESTE:
        filme_teste["onde_assistir"] = {
            "assinatura": STREAMINGS_DE_TESTE[filme_teste["nome"]], "consultado_em": "2026-10-04"
        }


if not MODO_COMPLETO:
    caminho_catalogo = PASTA_TEMPORARIA / "filmes_teste.json"
    caminho_catalogo.write_text(json.dumps(CATALOGO_DE_TESTE, ensure_ascii=False), encoding="utf-8")
    os.environ["CINEAI_CATALOGO"] = str(caminho_catalogo)
    os.environ["CINEAI_CACHE"] = str(PASTA_TEMPORARIA / "cache_teste.pkl")

    sys.modules["sentence_transformers"] = types.SimpleNamespace(SentenceTransformer=ModeloSimulado)
    sys.modules["ollama"] = types.SimpleNamespace(chat=ollama_simulado)


# Só agora importamos o CineAI (depois de configurar caminhos e simulações)
print("Carregando o CineAI" + (" com o catálogo real..." if MODO_COMPLETO else " (modo rápido)..."))
from cineai import conversas, filmes, perfil, rastreio, streamings, usuario  # noqa: E402


apenas_modo_rapido = unittest.skipIf(MODO_COMPLETO, "depende do catálogo de teste")
apenas_modo_completo = unittest.skipUnless(MODO_COMPLETO, "só no modo --completo")


# =========================================================
# BASE COMUM
# =========================================================
class TesteCineAI(unittest.TestCase):

    def setUp(self):
        """Antes de cada teste: usuário e conversa zerados."""
        for arquivo in ["usuario.json", "conversas.json"]:
            (PASTA_TEMPORARIA / arquivo).unlink(missing_ok=True)
        usuario.dados_usuario = usuario.criar_dados_vazios()
        conversas.lista_conversas.clear()
        filmes.reiniciar_conversa()

    # ---------- atalhos ----------
    def filme(self, nome, ano=None):
        for filme in filmes.filmes:
            if filme["nome"] == nome and (ano is None or filme["ano"] == ano):
                return filme
        self.fail(f'O filme "{nome}" não está no catálogo.')

    def pedir(self, mensagem):
        return filmes.processar_mensagem(mensagem)

    def recomendado(self, mensagem):
        """Nome do filme recomendado (ou falha se não veio filme)."""
        resultado = self.pedir(mensagem)
        self.assertEqual(
            resultado["tipo"], "recomendacao",
            f'"{mensagem}" deveria recomendar um filme, mas respondeu: {resultado["texto"][:120]}'
        )
        return resultado["filme"]["nome"]


# =========================================================
# 1. TEXTO E PALAVRAS
# =========================================================
class TestTexto(TesteCineAI):

    def test_palavra_inteira(self):
        """'ano' casa com 'De que ano ele é?', mas não com 'plano' ou 'humano'."""
        self.assertTrue(filmes.contem_alguma_palavra("De que ano ele é?", ["ano"]))
        self.assertFalse(filmes.contem_alguma_palavra("Qual é o plano do ogro?", ["ano"]))
        self.assertFalse(filmes.contem_alguma_palavra("Ele é humano?", ["ano"]))

    def test_pedido_de_outro(self):
        """'Quero outro' é pedido de outro; 'astronautas procurando outro planeta' é busca nova."""
        for frase in ["Quero outro", "Não gostei desse, quero outro", "me mostra outra opção", "próximo"]:
            self.assertTrue(filmes.eh_pedido_de_outro_filme(frase), frase)
        for frase in ["Quero um filme sobre astronautas procurando outro planeta",
                      "Quero outro filme de comédia", "filme sobre outras dimensões"]:
            self.assertFalse(filmes.eh_pedido_de_outro_filme(frase), frase)

    def test_saudacao(self):
        """'oi' e 'bom dia' são saudações; 'oi, quero uma comédia' não é só saudação."""
        self.assertTrue(filmes.eh_saudacao("oi"))
        self.assertTrue(filmes.eh_saudacao("Bom dia, CineAI!"))
        self.assertFalse(filmes.eh_saudacao("oi, quero uma comédia"))


# =========================================================
# 2. DETECTORES (gênero, pessoas, ano, qualidade)
# =========================================================
class TestDetectores(TesteCineAI):

    def test_genero_sem_acento_e_plural(self):
        """'comedia', 'comédias' e 'sci-fi' são reconhecidos."""
        self.assertEqual(filmes.detectar_genero("Quero uma comedia"), "comedia")
        self.assertEqual(filmes.detectar_genero("Quero umas comédias"), "comedia")
        self.assertEqual(filmes.detectar_genero("algo sci-fi"), "ficcao cientifica")

    def test_pessoas_pelo_sobrenome(self):
        """'do Nolan' acha o diretor; 'com DiCaprio' acha o ator."""
        self.assertEqual(filmes.detectar_diretor("Quero um filme do Nolan"), "Christopher Nolan")
        self.assertEqual(filmes.detectar_ator("Quero um filme com DiCaprio"), "Leonardo DiCaprio")

    def test_nome_completo_tem_prioridade(self):
        """'com Eddie Murphy' acha só o ator, sem casar outro 'Murphy'."""
        diretor, ator = filmes.detectar_diretor_e_ator("animação com Eddie Murphy")
        self.assertEqual((diretor, ator), (None, "Eddie Murphy"))

    def test_palavra_comum_nao_vira_ator(self):
        """'filme de rock' não vira 'filme com Chris Rock'."""
        self.assertIsNone(filmes.detectar_ator("Quero um filme de rock"))

    def test_ano(self):
        """Anos válidos são detectados; '3000' não."""
        self.assertEqual(filmes.detectar_ano("um filme de 1999"), 1999)
        self.assertIsNone(filmes.detectar_ano("o ano 3000"))

    def test_qualidade(self):
        """Crítica, público, geral e clássico; frases parecidas não confundem."""
        casos = {
            "Quero um filme que a crítica amou": "critica",
            "que o público adorou": "publico",
            "uma comédia bem avaliada": "geral",
            "uma animação clássica": "classico",
            "sobre pessoas que buscam uma vida melhor": None,
            "um filme sobre críticos de arte": None,
        }
        for frase, esperado in casos.items():
            self.assertEqual(filmes.detectar_qualidade(frase), esperado, frase)


# =========================================================
# 3. INTENÇÃO (pergunta x busca)
# =========================================================
class TestIntencao(TesteCineAI):

    def test_regras_antes_da_ia(self):
        """As regras resolvem sem chamar a IA."""
        self.assertEqual(filmes.classificar_por_regras("Ele é humano?"), "PERGUNTA")
        self.assertEqual(filmes.classificar_por_regras("Quem dirigiu ele?"), "PERGUNTA")
        self.assertEqual(filmes.classificar_por_regras("Tem algum filme com Tom Hanks?"), "BUSCA")
        self.assertEqual(filmes.classificar_por_regras("Quero um filme parecido com esse"), "BUSCA")


# =========================================================
# 4. BUSCAS
# =========================================================
class TestBusca(TesteCineAI):

    def test_filtros_combinados(self):
        """'animação de 2001 com Eddie Murphy' -> Shrek."""
        self.assertEqual(self.recomendado("Quero uma animação de 2001 com Eddie Murphy"), "Shrek")

    def test_diretor_pelo_sobrenome(self):
        """'do Nolan' recomenda um filme do Christopher Nolan."""
        resultado = self.pedir("Quero um filme do Nolan")
        self.assertIn("Christopher Nolan", resultado["filme"]["diretor"])

    def test_genero_sem_acento(self):
        """'Quero uma comedia' recomenda uma comédia."""
        resultado = self.pedir("Quero uma comedia")
        self.assertIn("Comédia", resultado["filme"]["genero"])

    def test_ator_mais_popular_primeiro(self):
        """Filtros vêm do mais popular: DiCaprio -> A Origem (mais votos)."""
        nome = self.recomendado("Quero um filme com Leonardo DiCaprio")
        if MODO_COMPLETO:
            self.assertIn("Leonardo DiCaprio", self.pedir("Quero um filme com DiCaprio")["filme"]["elenco"])
        else:
            self.assertEqual(nome, "A Origem")

    def test_busca_por_assunto(self):
        """Ogro -> Shrek; dinossauros -> Jurassic Park."""
        pedido_do_ogro = "Quero um filme sobre um ogro que resgata uma princesa"
        if MODO_COMPLETO:
            # Com 1900 títulos, outras histórias de princesa competem: basta Shrek estar no top 5.
            resultado = self.pedir(pedido_do_ogro)
            ranking = next(e for e in resultado["rastro"]["etapas"] if e["tabela"])
            self.assertIn("Shrek", [linha[0] for linha in ranking["tabela"]["linhas"]])
        else:
            self.assertEqual(self.recomendado(pedido_do_ogro), "Shrek")
        self.assertEqual(
            self.recomendado("Quero um filme sobre dinossauros"),
            "Jurassic Park: O Parque dos Dinossauros"
        )

    def test_bug_outro_planeta(self):
        """Bug antigo: 'outro planeta' depois de Shrek era tratado como 'Quero outro'."""
        self.recomendado("Quero uma animação de 2001 com Eddie Murphy")
        self.assertEqual(
            self.recomendado("Quero um filme sobre astronautas procurando outro planeta"),
            "Interestelar"
        )

    @apenas_modo_rapido
    def test_quero_outro_nao_repete(self):
        """'Quero outro' traz o próximo da lista, sem repetir."""
        primeiro = self.recomendado("Quero um filme do Nolan")
        segundo = self.recomendado("Quero outro")
        terceiro = self.recomendado("Quero outro")
        self.assertEqual(len({primeiro, segundo, terceiro}), 3)

    def test_saudacao_responde(self):
        """'oi' recebe uma saudação, não 'nenhum filme encontrado'."""
        self.assertTrue(self.pedir("oi")["texto"].startswith("Olá"))


# =========================================================
# 5. QUALIDADE ("a crítica amou", "clássico")
# =========================================================
class TestQualidade(TesteCineAI):

    def test_critica_amou(self):
        """'Que a crítica amou' traz filme com 90%+ no Rotten, em ordem decrescente."""
        primeiro = self.pedir("Quero um filme que a crítica amou")["filme"]
        segundo = self.pedir("Quero outro")["filme"]
        self.assertGreaterEqual(primeiro["rotten_tomatoes"]["critica"], 90)
        self.assertGreaterEqual(primeiro["rotten_tomatoes"]["critica"], segundo["rotten_tomatoes"]["critica"])

    def test_classico_e_antigo(self):
        """'Animação clássica' traz animação lançada há 20+ anos (bug do Lego 2014)."""
        filme = self.pedir("Quero uma animação clássica")["filme"]
        self.assertIn("Animação", filme["genero"])
        self.assertLessEqual(filme["ano"], date.today().year - filmes.IDADE_MINIMA_CLASSICO)

    def test_publico_mostra_imdb(self):
        """'O público adorou' mostra a nota do IMDb, não a da crítica."""
        texto = self.pedir("Quero um filme que o público adorou")["texto"]
        linhas_de_nota = [
            linha for linha in texto.splitlines()
            if linha.startswith(("⭐", "🍅", "🍿", "Ⓜ"))
        ]
        self.assertTrue(linhas_de_nota, texto[-120:])
        self.assertTrue(linhas_de_nota[-1].startswith("⭐ IMDb"), texto[-120:])
        self.assertNotIn("🍅", "\n".join(linhas_de_nota))


# =========================================================
# 6. PERGUNTAS SOBRE O FILME ATUAL
# =========================================================
class TestPerguntasSobreFilme(TesteCineAI):

    def setUp(self):
        super().setUp()
        self.recomendado("Quero uma animação de 2001 com Eddie Murphy")  # Shrek

    def test_diretor_e_ano(self):
        """'Quem dirigiu ele?' e 'De que ano ele é?' respondem direto."""
        self.assertIn("Andrew Adamson", self.pedir("Quem dirigiu ele?")["texto"])
        self.assertEqual(self.pedir("De que ano ele é?")["texto"], "Ano: 2001")

    def test_plano_nao_e_ano(self):
        """Bug antigo: 'Qual é o plano do ogro?' respondia 'Ano: 2001'."""
        resposta = self.pedir("Qual é o plano do ogro?")
        self.assertEqual(resposta["tipo"], "pergunta")
        self.assertNotIn("Ano:", resposta["texto"])

    def test_ele_e_humano_e_pergunta(self):
        """Bug antigo: 'Ele é humano?' virava busca."""
        self.assertEqual(self.pedir("Ele é humano?")["tipo"], "pergunta")

    def test_notas_do_filme(self):
        """'Qual a nota?' mostra Rotten Tomatoes e IMDb."""
        texto = self.pedir("Qual a nota?")["texto"]
        self.assertIn("🍅 Rotten Tomatoes", texto)
        self.assertIn("⭐ IMDb", texto)


# =========================================================
# 7. FAVORITOS, ASSISTIDOS E PERSISTÊNCIA
# =========================================================
class TestUsuario(TesteCineAI):

    def recarregar_usuario(self):
        """Simula fechar e abrir o app."""
        importlib.reload(usuario)

    def test_salva_e_recarrega(self):
        """Favorito e assistido continuam depois de 'fechar e abrir'."""
        usuario.alternar_favorito(self.filme("Shrek"))
        usuario.alternar_assistido(self.filme("Titanic"))
        self.recarregar_usuario()
        self.assertTrue(usuario.eh_favorito(self.filme("Shrek")))
        self.assertTrue(usuario.foi_assistido(self.filme("Titanic")))

    def test_filmes_com_mesmo_nome(self):
        """'O Rei Leão' de 1994 e o de 2019 não se misturam (chave = id do TMDB)."""
        usuario.alternar_assistido(self.filme("O Rei Leão", 1994))
        self.assertTrue(usuario.foi_assistido(self.filme("O Rei Leão", 1994)))
        self.assertFalse(usuario.foi_assistido(self.filme("O Rei Leão", 2019)))

    def test_arquivo_corrompido(self):
        """usuario.json estragado não derruba o app: começa vazio e guarda uma cópia."""
        usuario.CAMINHO_USUARIO.write_text("{ isso não é json", encoding="utf-8")
        self.recarregar_usuario()
        self.assertEqual(usuario.dados_usuario, usuario.criar_dados_vazios())
        self.assertTrue(usuario.CAMINHO_USUARIO.with_suffix(".corrompido.json").exists())

    def test_pula_assistidos(self):
        """O CineAI não recomenda o que você já viu."""
        usuario.alternar_assistido(self.filme("Shrek"))
        self.assertNotEqual(self.recomendado("Quero um filme sobre um ogro que resgata uma princesa"), "Shrek")

    def test_citar_pelo_nome_libera(self):
        """'Quero rever Shrek' recomenda Shrek mesmo assistido."""
        usuario.alternar_assistido(self.filme("Shrek"))
        self.assertEqual(self.recomendado("Quero uma animação de 2001 com Eddie Murphy e rever Shrek"), "Shrek")

    def test_aviso_todos_assistidos(self):
        """Se todos os filmes encontrados já foram vistos, avisa (com 'aos', não 'a os')."""
        for filme in filmes.filmes:
            if "Christopher Nolan" in filme["diretor"]:
                usuario.alternar_assistido(filme)
        texto = self.pedir("Quero um filme do Nolan")["texto"]
        self.assertTrue(texto.startswith("Você já assistiu aos"), texto[:60])
        self.assertIn("Interestelar", texto)  # diz QUAIS títulos

    @apenas_modo_rapido  # no catálogo real o Vince Gilligan tem outras séries (Better Call Saul)
    def test_aviso_de_um_titulo_diz_qual(self):
        """Um só título já visto: diz o nome e se é série ou filme."""
        for item in filmes.filmes:
            if item["nome"] == "Breaking Bad":
                usuario.alternar_assistido(item)
        texto = self.pedir("Quero uma série do Vince Gilligan")["texto"]
        self.assertIn("Você já assistiu a Breaking Bad (série)", texto)


class TestAnotacoes(TesteCineAI):

    def test_salvar_ler_e_apagar(self):
        """A anotação fica salva depois de 'fechar e abrir' e some se apagar o texto."""
        shrek = self.filme("Shrek")
        usuario.definir_anotacao(shrek, "  Assisti com a minha irmã, rimos muito!  ")
        usuario.dados_usuario = usuario.carregar_dados()   # "fecha e abre"
        self.assertEqual(usuario.obter_anotacao(shrek), "Assisti com a minha irmã, rimos muito!")
        usuario.definir_anotacao(shrek, "")
        self.assertEqual(usuario.obter_anotacao(shrek), "")

    def test_numero_da_entrada(self):
        """O 1º filme marcado como visto é a entrada 1; o 2º, a entrada 2."""
        usuario.alternar_assistido(self.filme("Titanic"))
        usuario.alternar_assistido(self.filme("Shrek"))
        self.assertEqual(usuario.numero_da_entrada(self.filme("Titanic")), 1)
        self.assertEqual(usuario.numero_da_entrada(self.filme("Shrek")), 2)
        self.assertIsNone(usuario.numero_da_entrada(self.filme("Dunkirk")))

    def test_arquivo_antigo_sem_anotacoes(self):
        """usuario.json antigo (sem 'anotacoes') continua abrindo."""
        caminho = usuario.CAMINHO_USUARIO
        caminho.write_text('{"favoritos": {}, "assistidos": {}}', encoding="utf-8")
        self.assertEqual(usuario.carregar_dados()["anotacoes"], {})


class TestDiario(TesteCineAI):
    """Diário automático: cada título visto vira uma entrada (Meu diário)."""

    def marcar_tres(self):
        usuario.alternar_assistido(self.filme("Titanic"))
        usuario.definir_nota(self.filme("Shrek"), 5)
        usuario.definir_nota(self.filme("Dunkirk"), 3)
        usuario.definir_anotacao(self.filme("Shrek"), "Ri do começo ao fim.")

    def nomes(self, entradas):
        return [entrada["filme"]["nome"] for entrada in entradas]

    def test_entrada_tem_tudo(self):
        """A entrada traz número, data de hoje, nota e anotação."""
        from datetime import date
        self.marcar_tres()
        shrek = next(e for e in usuario.entradas_do_diario(filmes.filmes) if e["filme"]["nome"] == "Shrek")
        self.assertEqual(shrek["numero"], 2)
        self.assertEqual(shrek["data"], date.today())
        self.assertEqual(shrek["nota"], 5)
        self.assertEqual(shrek["anotacao"], "Ri do começo ao fim.")

    def test_ordens(self):
        """Mais recentes, mais antigos e por nota (sem nota vai para o fim)."""
        self.marcar_tres()
        self.assertEqual(self.nomes(usuario.entradas_do_diario(filmes.filmes)), ["Dunkirk", "Shrek", "Titanic"])
        self.assertEqual(
            self.nomes(usuario.entradas_do_diario(filmes.filmes, usuario.ORDEM_DIARIO_ANTIGOS)),
            ["Titanic", "Shrek", "Dunkirk"]
        )
        self.assertEqual(
            self.nomes(usuario.entradas_do_diario(filmes.filmes, usuario.ORDEM_DIARIO_NOTA)),
            ["Shrek", "Dunkirk", "Titanic"]
        )

    def test_numero_nao_muda_com_a_ordem(self):
        """Titanic é sempre a entrada #1, em qualquer ordem."""
        self.marcar_tres()
        for ordem in (usuario.ORDEM_DIARIO_RECENTES, usuario.ORDEM_DIARIO_ANTIGOS, usuario.ORDEM_DIARIO_NOTA):
            titanic = next(e for e in usuario.entradas_do_diario(filmes.filmes, ordem) if e["filme"]["nome"] == "Titanic")
            self.assertEqual(titanic["numero"], 1)

    def test_corrigir_a_data(self):
        """Corrigir a data reordena o diário (por data) e renumera as entradas."""
        from datetime import date, timedelta
        self.marcar_tres()   # Titanic, Shrek, Dunkirk: todos hoje
        usuario.definir_data_assistido(self.filme("Dunkirk"), date(2015, 7, 20))
        self.assertEqual(usuario.data_em_que_assistiu(self.filme("Dunkirk")), date(2015, 7, 20))
        self.assertEqual(usuario.numero_da_entrada(self.filme("Dunkirk")), 1)
        self.assertEqual(usuario.numero_da_entrada(self.filme("Titanic")), 2)
        self.assertEqual(self.nomes(usuario.entradas_do_diario(filmes.filmes))[-1], "Dunkirk")
        usuario.dados_usuario = usuario.carregar_dados()   # "fecha e abre"
        self.assertEqual(usuario.data_em_que_assistiu(self.filme("Dunkirk")), date(2015, 7, 20))
        with self.assertRaises(ValueError):
            usuario.definir_data_assistido(self.filme("Dunkirk"), date.today() + timedelta(days=1))
        with self.assertRaises(ValueError):
            usuario.definir_data_assistido(self.filme("A Origem"), date(2020, 1, 1))  # não foi visto

    def test_nao_sei_a_data(self):
        """'Não sei quando vi': a entrada fica sem data, vai para o começo do diário e aceita data depois."""
        from datetime import date
        self.marcar_tres()   # Titanic, Shrek, Dunkirk: todos hoje
        usuario.definir_data_assistido(self.filme("Shrek"), None)
        self.assertIsNone(usuario.data_em_que_assistiu(self.filme("Shrek")))
        self.assertEqual(usuario.numero_da_entrada(self.filme("Shrek")), 1)
        entradas = usuario.entradas_do_diario(filmes.filmes)
        self.assertEqual(self.nomes(entradas)[-1], "Shrek")
        self.assertIsNone(entradas[-1]["data"])
        usuario.dados_usuario = usuario.carregar_dados()   # "fecha e abre": continua sem data
        self.assertIsNone(usuario.data_em_que_assistiu(self.filme("Shrek")))
        self.assertTrue(usuario.foi_assistido(self.filme("Shrek")))
        usuario.definir_data_assistido(self.filme("Shrek"), date(2019, 5, 2))   # lembrou depois
        self.assertEqual(usuario.data_em_que_assistiu(self.filme("Shrek")), date(2019, 5, 2))

    def test_revisita_sem_data(self):
        """Um 'vi de novo' sem data fica logo depois da 1ª vez daquele título."""
        from datetime import date
        titanic = self.filme("Titanic")
        usuario.alternar_assistido(titanic)
        usuario.definir_data_assistido(titanic, date(2010, 1, 1))
        sessao = usuario.registrar_revisita(titanic)
        usuario.definir_data_assistido(titanic, None, sessao=sessao)
        entradas = usuario.entradas_do_diario(filmes.filmes, usuario.ORDEM_DIARIO_ANTIGOS)
        self.assertEqual([(e["vez"], e["data"]) for e in entradas], [(1, date(2010, 1, 1)), (2, None)])

    def test_diario_vazio_e_data_estranha(self):
        """Sem nada visto: lista vazia. Data inválida no arquivo: data None (não quebra)."""
        self.assertEqual(usuario.entradas_do_diario(filmes.filmes), [])
        titanic = self.filme("Titanic")
        usuario.alternar_assistido(titanic)
        usuario.dados_usuario["assistidos"][usuario.chave_filme(titanic)]["adicionado_em"] = "ontem"
        self.assertIsNone(usuario.entradas_do_diario(filmes.filmes)[0]["data"])


class TestRever(TesteCineAI):
    """'Vi de novo': cada vez que você vê um título vira uma entrada no diário."""

    def test_vi_de_novo_cria_entrada(self):
        """A revisita ganha entrada própria (2ª vez), com data e anotação separadas."""
        from datetime import date
        shrek = self.filme("Shrek")
        usuario.definir_nota(shrek, 5)
        usuario.definir_data_assistido(shrek, date(2019, 5, 2))
        usuario.definir_anotacao(shrek, "Primeira vez: ri muito.")
        sessao = usuario.registrar_revisita(shrek)
        usuario.definir_anotacao(shrek, "Revi com a família, ainda engraçado.", sessao=sessao)

        entradas = usuario.entradas_do_diario(filmes.filmes, usuario.ORDEM_DIARIO_ANTIGOS)
        self.assertEqual([(e["filme"]["nome"], e["vez"]) for e in entradas], [("Shrek", 1), ("Shrek", 2)])
        self.assertEqual(entradas[0]["anotacao"], "Primeira vez: ri muito.")
        self.assertEqual(entradas[1]["anotacao"], "Revi com a família, ainda engraçado.")
        self.assertEqual(entradas[1]["data"], date.today())
        self.assertEqual(usuario.quantas_vezes_viu(shrek), 2)

        usuario.dados_usuario = usuario.carregar_dados()   # "fecha e abre"
        self.assertEqual(usuario.obter_anotacao(shrek, sessao=0), "Revi com a família, ainda engraçado.")

    def test_data_e_apagar_revisita(self):
        """A data da revisita é corrigível; apagar a revisita mantém a 1ª vez."""
        from datetime import date
        titanic = self.filme("Titanic")
        usuario.alternar_assistido(titanic)
        usuario.definir_data_assistido(titanic, date(2010, 1, 1))
        sessao = usuario.registrar_revisita(titanic)
        usuario.definir_data_assistido(titanic, date(2020, 2, 2), sessao=sessao)
        self.assertEqual(usuario.numero_da_entrada(titanic, sessao), 2)
        usuario.apagar_revisita(titanic, sessao)
        self.assertEqual(usuario.quantas_vezes_viu(titanic), 1)
        self.assertEqual(len(usuario.entradas_do_diario(filmes.filmes)), 1)

    def test_capa_conta_sessoes(self):
        """Na capa: o título conta 1 vez, mas as horas e as sessões contam a revisita."""
        a_origem = self.filme("A Origem")
        usuario.alternar_assistido(a_origem)
        usuario.registrar_revisita(a_origem)
        numeros = usuario.estatisticas_do_diario(filmes.filmes)
        self.assertEqual(numeros["total"], 1)
        self.assertEqual(numeros["sessoes"], 2)
        self.assertEqual(numeros["revistos"], 1)
        self.assertEqual(numeros["horas"], round(2 * a_origem["duracao_minutos"] / 60))

    def test_rever_sem_ter_visto_so_marca(self):
        """'Vi de novo' em algo que você nunca marcou: vira a 1ª vez, sem revisita."""
        dunkirk = self.filme("Dunkirk")
        self.assertIsNone(usuario.registrar_revisita(dunkirk))
        self.assertEqual(usuario.quantas_vezes_viu(dunkirk), 1)

    def test_rever_pelo_chat(self):
        """'Vi Shrek de novo' registra a revisita e tira o título do 'Quero assistir'."""
        shrek = self.filme("Shrek")
        usuario.alternar_assistido(shrek)
        usuario.guardar_para_depois(shrek)   # guardado "pra rever"
        resultado = self.pedir("vi Shrek de novo ontem à noite")
        self.assertEqual(resultado["tipo"], "usuario_atualizado")
        self.assertIn("2ª vez", resultado["texto"])
        self.assertEqual(usuario.quantas_vezes_viu(shrek), 2)
        self.assertFalse(usuario.quer_assistir(shrek))


@apenas_modo_rapido  # usa os streamings do catálogo de teste
class TestOndeAssistir(TesteCineAI):
    """Onde assistir: streamings por assinatura do Brasil (dados da JustWatch, via TMDB)."""

    def test_nomes_do_tmdb_viram_nomes_curtos(self):
        """'Amazon Prime Video with Ads' -> Prime Video; 'Cinemax' não vira Max."""
        self.assertEqual(streamings.nome_padrao("Amazon Prime Video with Ads"), "Prime Video")
        self.assertEqual(streamings.nome_padrao("HBO Max"), "Max")
        self.assertEqual(streamings.nome_padrao("Paramount Plus Apple TV Channel"), "Paramount+")
        self.assertEqual(streamings.nome_padrao("Cinemax"), "Cinemax")
        self.assertEqual(streamings.padronizar_lista(["Netflix basic with Ads", "Netflix", "Max"]), ["Netflix", "Max"])

    def test_detectar_no_chat(self):
        """'na Netflix', 'no prime', 'que eu tenho'; 'um filme com o Max' não é streaming."""
        self.assertEqual(streamings.detectar_streaming("uma comédia na Netflix"), "Netflix")
        self.assertEqual(streamings.detectar_streaming("quero uma animação no prime"), "Prime Video")
        self.assertEqual(streamings.detectar_streaming("algo que eu tenho"), streamings.MEUS_STREAMINGS)
        self.assertIsNone(streamings.detectar_streaming("um filme com o Max"))

    def test_busca_com_streaming(self):
        """'Uma animação na Netflix' -> Shrek, e a resposta diz onde assistir."""
        resultado = self.pedir("Quero uma animação na Netflix")
        self.assertEqual(resultado["filme"]["nome"], "Shrek")
        self.assertIn("📺 Onde assistir: Netflix, Prime Video", resultado["texto"])

    def test_meus_streamings(self):
        """Com 'Max' marcado como seu, 'um filme que eu tenho' só traz o que está no Max."""
        usuario.definir_meus_streamings(["Max"])
        self.assertEqual(self.recomendado("Quero um filme que eu tenho"), "Interestelar")
        self.assertIn("Max ✓", streamings.texto_onde_assistir(self.filme("Interestelar")))

    def test_perguntas_sobre_o_titulo(self):
        """Depois de Shrek: 'tá na netflix?' (sim), 'tá no max?' (não) e 'onde eu vejo esse?'."""
        self.recomendado("Quero uma animação na Netflix")
        self.assertIn("Sim!", self.pedir("tá na netflix?")["texto"])
        resposta_max = self.pedir("tá no max?")["texto"]
        self.assertIn("não está no Max", resposta_max)
        self.assertIn("Netflix, Prime Video", self.pedir("onde eu vejo esse?")["texto"])

    def test_fora_dos_streamings_e_nao_consultado(self):
        """Titanic: consultado e fora de assinatura. Dunkirk: ainda não consultado."""
        self.assertIn("nenhum streaming", self.pedir("onde assistir Titanic?")["texto"])
        self.assertIn("Ainda não sei", self.pedir("onde assistir Dunkirk?")["texto"])

    def test_busca_nao_vira_pergunta(self):
        """'Quero uma comédia na Netflix' e 'onde assistir um filme de terror?' são buscas."""
        self.assertFalse(filmes.eh_pergunta_onde_assistir("Quero uma comédia na Netflix"))
        self.assertFalse(filmes.eh_pergunta_onde_assistir("onde assistir um filme de terror?"))

    def test_catalogo_filtra_streaming(self):
        """Catálogo: só Netflix -> Shrek; 'os que eu tenho' com Disney+ -> Toy Story."""
        self.assertEqual([f["nome"] for f in filmes.filtrar_catalogo(streaming="Netflix")], ["Shrek"])
        usuario.definir_meus_streamings(["Disney+"])
        nomes = [f["nome"] for f in filmes.filtrar_catalogo(streaming=streamings.MEUS_STREAMINGS)]
        self.assertEqual(nomes, ["Toy Story: Um Mundo de Aventuras"])


class TestSugestaoDaNoite(TesteCineAI):
    """Uma sugestão por dia: da lista Quero assistir, do seu gosto ou dos populares."""

    def test_mesma_sugestao_no_mesmo_dia(self):
        """No mesmo dia a sugestão não muda; ela nunca é algo que você já viu."""
        from datetime import date
        primeira = filmes.sugestao_da_noite(date(2026, 10, 4))[0]
        self.assertIs(filmes.sugestao_da_noite(date(2026, 10, 4))[0], primeira)
        self.assertFalse(usuario.foi_assistido(primeira))

    def test_vem_da_lista_quero_assistir(self):
        """Com títulos guardados, a sugestão sai da lista (e o motivo diz isso)."""
        usuario.guardar_para_depois(self.filme("Dunkirk"))
        filme, motivo, _ = filmes.sugestao_da_noite()
        self.assertEqual(filme["nome"], "Dunkirk")
        self.assertIn("Quero assistir", motivo)

    @apenas_modo_rapido  # usa os streamings do catálogo de teste
    def test_prefere_meus_streamings(self):
        """Entre os guardados, prefere o que está num streaming que você assina."""
        usuario.guardar_para_depois(self.filme("Dunkirk"))
        usuario.guardar_para_depois(self.filme("Interestelar"))
        usuario.definir_meus_streamings(["Max"])
        filme, motivo, _ = filmes.sugestao_da_noite()
        self.assertEqual(filme["nome"], "Interestelar")
        self.assertIn("Max ✓", motivo)

    def test_pelo_chat(self):
        """'O que eu vejo hoje?' traz a sugestão; 'quero outro' traz outra."""
        resultado = self.pedir("o que eu vejo hoje?")
        self.assertEqual(resultado["tipo"], "recomendacao")
        self.assertIn("Sugestão da noite", resultado["texto"])
        self.assertNotEqual(self.recomendado("quero outro"), resultado["filme"]["nome"])


class TestRetrospectiva(TesteCineAI):
    """Retrospectiva do ano: só as sessões com data naquele ano entram."""

    def ver(self, nome, data, nota=None, anotacao=None):
        filme = self.filme(nome)
        if nota is not None:
            usuario.definir_nota(filme, nota)
        else:
            usuario.alternar_assistido(filme)
        usuario.definir_data_assistido(filme, data)
        if anotacao:
            usuario.definir_anotacao(filme, anotacao)
        return filme

    def test_diario_vazio(self):
        """Sem sessões: nenhum ano, e a retrospectiva de qualquer ano é None."""
        from datetime import date
        self.assertEqual(usuario.anos_do_diario(filmes.filmes), [])
        self.assertIsNone(usuario.ano_padrao_da_retrospectiva(filmes.filmes))
        self.assertIsNone(usuario.retrospectiva_do_ano(filmes.filmes, date.today().year))

    def test_separa_por_ano(self):
        """Cada ano conta só o que foi visto nele; anos em ordem do mais novo."""
        from datetime import date
        self.ver("Titanic", date(2024, 3, 10), nota=3)
        self.ver("A Origem", date(2025, 7, 1), nota=5)
        self.ver("Interestelar", date(2025, 7, 20), nota=4)
        self.assertEqual(usuario.anos_do_diario(filmes.filmes), [2025, 2024])

        numeros = usuario.retrospectiva_do_ano(filmes.filmes, 2025)
        self.assertEqual(numeros["titulos"], 2)
        self.assertEqual(numeros["sessoes"], 2)
        self.assertEqual(numeros["mes"], (7, 2))
        self.assertEqual(numeros["meses"][6], 2)
        self.assertEqual(sum(numeros["meses"]), 2)
        self.assertEqual(numeros["pessoa"], ("Christopher Nolan", 2))
        self.assertEqual(numeros["melhor"]["filme"]["nome"], "A Origem")
        self.assertEqual(numeros["nota_media"], 4.5)
        self.assertEqual(numeros["primeira"]["filme"]["nome"], "A Origem")
        self.assertEqual(numeros["ultima"]["filme"]["nome"], "Interestelar")
        self.assertEqual(usuario.retrospectiva_do_ano(filmes.filmes, 2024)["titulos"], 1)
        self.assertIsNone(usuario.retrospectiva_do_ano(filmes.filmes, 2023))

    def test_ano_padrao(self):
        """Sem nada no ano de hoje, a retrospectiva abre no ano mais recente do diário."""
        from datetime import date
        self.ver("Titanic", date(2024, 3, 10))
        self.assertEqual(usuario.ano_padrao_da_retrospectiva(filmes.filmes, hoje=date(2026, 1, 5)), 2024)
        self.ver("Shrek", date(2026, 1, 2))
        self.assertEqual(usuario.ano_padrao_da_retrospectiva(filmes.filmes, hoje=date(2026, 1, 5)), 2026)

    def test_revisita_conta_no_ano_em_que_reviu(self):
        """Ver Shrek em 2019 e rever em 2025: em 2025 ele é reencontro, não novidade."""
        from datetime import date
        shrek = self.ver("Shrek", date(2019, 5, 2), nota=5)
        usuario.registrar_revisita(shrek, date(2025, 2, 14))
        numeros = usuario.retrospectiva_do_ano(filmes.filmes, 2025)
        self.assertEqual(numeros["titulos"], 1)
        self.assertEqual(numeros["novos"], 0)
        self.assertEqual(len(numeros["revistos"]), 1)
        self.assertEqual(numeros["revistos"][0]["vez"], 2)
        self.assertEqual(usuario.retrospectiva_do_ano(filmes.filmes, 2019)["revistos"], [])

    def test_anotacao_em_destaque(self):
        """A anotação escolhida é a do título com maior nota (e só se houver alguma)."""
        from datetime import date
        self.ver("Titanic", date(2025, 1, 5), nota=3, anotacao="Chorei demais no final do navio.")
        self.ver("A Origem", date(2025, 2, 5), nota=5, anotacao="Fiquei pensando no pião girando.")
        numeros = usuario.retrospectiva_do_ano(filmes.filmes, 2025)
        self.assertEqual(numeros["anotacao"]["filme"]["nome"], "A Origem")
        self.assertEqual(numeros["anotacoes"], 2)
        self.ver("Shrek", date(2024, 1, 1), nota=4)
        self.assertIsNone(usuario.retrospectiva_do_ano(filmes.filmes, 2024)["anotacao"])

    def test_dia_mais_cheio(self):
        """Dois títulos no mesmo dia viram o 'dia mais cheio'; um só não."""
        from datetime import date
        self.ver("Titanic", date(2025, 4, 12))
        numeros = usuario.retrospectiva_do_ano(filmes.filmes, 2025)
        self.assertIsNone(numeros["dia"])
        self.ver("Shrek", date(2025, 4, 12))
        self.assertEqual(usuario.retrospectiva_do_ano(filmes.filmes, 2025)["dia"], (date(2025, 4, 12), 2))

    def test_pelo_chat(self):
        """'Como foi meu ano de 2025 no cinema?' responde com o resumo e pede para abrir a janela."""
        from datetime import date
        self.ver("A Origem", date(2025, 7, 1), nota=5)
        resultado = self.pedir("minha retrospectiva de 2025")
        self.assertEqual(resultado["tipo"], "retrospectiva")
        self.assertEqual(resultado["ano"], 2025)
        self.assertIn("A Origem", resultado["texto"])
        self.assertIn("julho", resultado["texto"])

    def test_pelo_chat_sem_diario(self):
        """Sem nada no diário, o chat explica em vez de abrir uma janela vazia."""
        resultado = self.pedir("como foi meu ano no cinema?")
        self.assertEqual(resultado["tipo"], "mensagem")
        self.assertIn("diário", resultado["texto"])


class TestDiarioPdf(TesteCineAI):
    """Diário em PDF: capa, números e as entradas (gravado só na pasta temporária)."""

    def caminho(self, nome="diario.pdf"):
        return PASTA_TEMPORARIA / "exportados" / nome

    @staticmethod
    def contar_paginas(caminho):
        import re
        # Cada página nova é acrescentada ao fim do arquivo; o último /Count é o total.
        return int(re.findall(rb"/Count\s*(\d+)", caminho.read_bytes())[-1])

    def ver(self, nome, data, nota=None, anotacao=None):
        filme = self.filme(nome)
        if nota is not None:
            usuario.definir_nota(filme, nota)
        else:
            usuario.alternar_assistido(filme)
        usuario.definir_data_assistido(filme, data)
        if anotacao:
            usuario.definir_anotacao(filme, anotacao)

    def test_diario_vazio(self):
        """Sem entradas, não cria um PDF vazio: avisa com ValueError."""
        from cineai import diario_pdf
        with self.assertRaises(ValueError):
            diario_pdf.exportar_diario_pdf(filmes.filmes, caminho=self.caminho("vazio.pdf"))
        self.assertFalse(self.caminho("vazio.pdf").exists())

    def test_exporta_pdf(self):
        """Gera um PDF de verdade: capa + números + entradas, sem sobrar o .tmp."""
        from datetime import date
        from cineai import diario_pdf
        self.ver("Shrek", date(2025, 5, 2), nota=5, anotacao="Ri do começo ao fim com a família.")
        self.ver("Titanic", date(2025, 6, 1))
        paginas_prontas = []
        caminho = diario_pdf.exportar_diario_pdf(
            filmes.filmes, caminho=self.caminho(), ao_avancar=paginas_prontas.append
        )
        self.assertTrue(caminho.read_bytes().startswith(b"%PDF"))
        self.assertEqual(self.contar_paginas(caminho), 3)
        self.assertEqual(paginas_prontas, [1, 2, 3])
        self.assertFalse(caminho.with_suffix(".tmp").exists())

    def test_muitas_entradas_viram_mais_paginas(self):
        """Com várias entradas, o diário continua em páginas novas."""
        from datetime import date
        from cineai import diario_pdf
        for dia, filme in enumerate(filmes.filmes[:12], start=1):
            usuario.alternar_assistido(filme)
            usuario.definir_data_assistido(filme, date(2025, 1 + dia % 12, dia))
        caminho = diario_pdf.exportar_diario_pdf(filmes.filmes, caminho=self.caminho("muitas.pdf"))
        self.assertGreater(self.contar_paginas(caminho), 4)

    def test_so_um_ano(self):
        """Exportando um ano, só as sessões daquele ano entram."""
        from datetime import date
        from cineai import diario_pdf
        self.ver("Shrek", date(2024, 5, 2))
        self.ver("Titanic", date(2025, 6, 1))
        entradas = diario_pdf.entradas_para_exportar(filmes.filmes, 2025)
        self.assertEqual([entrada["filme"]["nome"] for entrada in entradas], ["Titanic"])
        with self.assertRaises(ValueError):
            diario_pdf.exportar_diario_pdf(filmes.filmes, ano=2023, caminho=self.caminho("2023.pdf"))

    def test_anotacao_longa_quebra_linhas(self):
        """A anotação é quebrada em linhas que cabem na coluna, sem perder palavras."""
        from cineai import diario_pdf
        fonte = diario_pdf.fonte(diario_pdf.FONTES_MANUSCRITAS, 34)
        texto = "Chorei no final, de novo. A trilha sonora é linda demais e a despedida acabou comigo. " * 3
        linhas = diario_pdf.quebrar_linhas(texto, fonte, 600)
        self.assertGreater(len(linhas), 2)
        self.assertEqual(" ".join(linhas).split(), texto.split())
        from PIL import Image, ImageDraw
        lapis = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        self.assertTrue(all(lapis.textlength(linha, font=fonte) <= 600 for linha in linhas))


class TestRetrato(TesteCineAI):
    """'O que meu diário diz sobre mim': a IA escreve, mas o CineAI confere."""
    TEXTO_SHREK = "Ri do começo ao fim com a família, que filme gostoso."
    TEXTO_TITANIC = "Longo demais e o final me irritou bastante."

    def montar_diario(self):
        usuario.definir_nota(self.filme("Shrek"), 5)
        usuario.definir_anotacao(self.filme("Shrek"), self.TEXTO_SHREK)
        usuario.definir_nota(self.filme("Titanic"), 2)
        usuario.definir_anotacao(self.filme("Titanic"), self.TEXTO_TITANIC)
        usuario.definir_nota(self.filme("A Origem"), 4)
        usuario.definir_anotacao(self.filme("A Origem"), "ok")   # curta demais: não entra

    @staticmethod
    def ia_que_responde(texto, chamadas=None):
        def perguntar(prompt):
            if chamadas is not None:
                chamadas.append(prompt)
            return texto
        return perguntar

    TEXTO_BOM = (
        "Retrato: Você ri alto e não tem vergonha disso: Shrek ganhou 5 estrelas e uma anotação cheia "
        "de família. Já Titanic não te convenceu, e você disse isso sem rodeios. É alguém que sabe o que quer."
    )

    def test_poucos_titulos(self):
        """Com menos de 3 títulos vistos, ainda não há retrato."""
        from cineai import retrato
        usuario.definir_nota(self.filme("Shrek"), 5)
        self.assertIsNone(retrato.gerar_retrato(filmes.filmes))

    def test_sem_ia_usa_frases_prontas(self):
        """Sem a IA, o retrato sai das regras: cita a 5 estrelas, a anotação e a nota baixa."""
        from cineai import retrato
        self.montar_diario()
        resultado = retrato.gerar_retrato(filmes.filmes, perguntar=None)
        self.assertEqual(resultado["origem"], retrato.ORIGEM_REGRAS)
        self.assertIn("Shrek", resultado["texto"])
        self.assertIn("Titanic", resultado["texto"])
        self.assertIn("Ri do começo ao fim", resultado["texto"])

    def test_citacoes_sao_as_suas_palavras(self):
        """As citações embaixo do texto são as anotações exatas (a mais curta que 3 palavras fica de fora)."""
        from cineai import retrato
        self.montar_diario()
        resultado = retrato.gerar_retrato(filmes.filmes)
        textos = [citacao["texto"] for citacao in resultado["citacoes"]]
        self.assertEqual(textos, [self.TEXTO_SHREK, self.TEXTO_TITANIC])

    def test_com_ia(self):
        """Texto bom da IA: passa na conferência, sem o rótulo 'Retrato:'."""
        from cineai import retrato
        self.montar_diario()
        resultado = retrato.gerar_retrato(filmes.filmes, self.ia_que_responde("<think>hm</think>" + self.TEXTO_BOM))
        self.assertEqual(resultado["origem"], retrato.ORIGEM_IA)
        self.assertTrue(resultado["texto"].startswith("Você ri alto"))

    def test_ia_inventando_cai_nas_regras(self):
        """Se a IA não cita nenhum título do diário, escreve em outro alfabeto ou falha, valem as regras."""
        from cineai import retrato
        self.montar_diario()
        inventado = "Você adora " + "Matrix e Senhor dos Anéis, sempre com pipoca e muita emoção. " * 3

        def ia_desligada(prompt):
            raise ConnectionError("Ollama fechado")

        for perguntar in (self.ia_que_responde(inventado), self.ia_que_responde("你好 Shrek " * 30),
                          self.ia_que_responde("Shrek."), ia_desligada):
            resultado = retrato.gerar_retrato(filmes.filmes, perguntar, forcar=True)
            self.assertEqual(resultado["origem"], retrato.ORIGEM_REGRAS)

    def test_guarda_e_so_reescreve_quando_muda(self):
        """O retrato fica guardado; muda o diário (ou 'escrever de novo') e a IA é chamada outra vez."""
        from cineai import retrato
        self.montar_diario()
        chamadas = []
        perguntar = self.ia_que_responde(self.TEXTO_BOM, chamadas)
        retrato.gerar_retrato(filmes.filmes, perguntar)
        retrato.gerar_retrato(filmes.filmes, perguntar)
        self.assertEqual(len(chamadas), 1)

        usuario.dados_usuario = usuario.carregar_dados()   # "fecha e abre": continua guardado
        retrato.gerar_retrato(filmes.filmes, perguntar)
        self.assertEqual(len(chamadas), 1)

        usuario.definir_anotacao(self.filme("Titanic"), "Revendo hoje, até que gostei do final.")
        retrato.gerar_retrato(filmes.filmes, perguntar)
        self.assertEqual(len(chamadas), 2)
        retrato.gerar_retrato(filmes.filmes, perguntar, forcar=True)
        self.assertEqual(len(chamadas), 3)

    def test_prompt_so_com_o_diario(self):
        """O prompt leva as anotações e proíbe inventar."""
        from cineai import retrato
        self.montar_diario()
        prompt = retrato.montar_prompt(retrato.fatos_do_diario(filmes.filmes))
        self.assertIn(self.TEXTO_SHREK, prompt)
        self.assertIn("Use SOMENTE", prompt)
        self.assertIn("Não gostou (1 ou 2 estrelas): Titanic", prompt)
        self.assertNotIn('"ok"', prompt)

    def test_pelo_chat(self):
        """'O que meu diário diz sobre mim?' responde com o retrato e as suas palavras."""
        self.montar_diario()
        resultado = self.pedir("o que meu diário diz sobre mim?")
        self.assertIn("O que o seu diário diz sobre você", resultado["texto"])
        self.assertIn(self.TEXTO_SHREK, resultado["texto"])

    def test_pelo_chat_sem_diario(self):
        resultado = self.pedir("meu retrato")
        self.assertIn("Ainda é cedo", resultado["texto"])


class TestSeriesPorEpisodio(TesteCineAI):
    """'Parei no S02E05': até onde você viu cada série."""
    TEMPORADAS_BREAKING_BAD = [7, 13, 13, 13, 16]

    def setUp(self):
        super().setUp()
        self.bb = self.filme("Breaking Bad")
        self.bb["episodios_por_temporada"] = list(self.TEMPORADAS_BREAKING_BAD)

    def tearDown(self):
        self.bb.pop("episodios_por_temporada", None)
        super().tearDown()

    def test_marcar_e_avancar(self):
        """Depois do último episódio da temporada vem o E01 da próxima."""
        usuario.definir_progresso(self.bb, 1, 6)
        self.assertEqual(usuario.avancar_episodio(self.bb), (1, 7, False))
        self.assertEqual(usuario.avancar_episodio(self.bb), (2, 1, False))
        self.assertEqual(usuario.porcentagem_da_serie(self.bb), round(100 * 8 / 62))
        usuario.dados_usuario = usuario.carregar_dados()   # "fecha e abre"
        self.assertEqual(usuario.obter_progresso(self.bb), (2, 1))

    def test_terminar_a_serie_vai_pro_diario(self):
        usuario.guardar_para_depois(self.bb)
        usuario.definir_progresso(self.bb, 5, 15)
        self.assertFalse(usuario.quer_assistir(self.bb))       # começou a ver: saiu da lista
        self.assertEqual(usuario.avancar_episodio(self.bb)[2], True)
        self.assertTrue(usuario.foi_assistido(self.bb))
        self.assertIsNone(usuario.obter_progresso(self.bb))
        self.assertEqual(usuario.series_em_andamento(filmes.filmes), [])

    def test_valida_temporada_e_episodio(self):
        with self.assertRaises(ValueError):
            usuario.definir_progresso(self.bb, 6, 1)     # só tem 5 temporadas
        with self.assertRaises(ValueError):
            usuario.definir_progresso(self.bb, 1, 8)     # a 1ª tem 7 episódios
        with self.assertRaises(ValueError):
            usuario.definir_progresso(self.bb, 0, 1)

    def test_sem_saber_os_episodios(self):
        """Sem episodios_por_temporada: só segue contando, e confere o total de temporadas."""
        dark = self.filme("Dark")
        usuario.definir_progresso(dark, 1, 10)
        self.assertEqual(usuario.avancar_episodio(dark), (1, 11, False))
        self.assertIsNone(usuario.porcentagem_da_serie(dark))
        with self.assertRaises(ValueError):
            usuario.definir_progresso(dark, 4, 1)

    def test_em_andamento_mais_recente_primeiro(self):
        dark = self.filme("Dark")
        usuario.definir_progresso(self.bb, 1, 1)
        usuario.definir_progresso(dark, 1, 1)
        usuario.definir_progresso(self.bb, 1, 2)
        self.assertEqual([serie["nome"] for serie, _, _ in usuario.series_em_andamento(filmes.filmes)],
                         ["Breaking Bad", "Dark"])

    def test_ler_episodio(self):
        self.assertEqual(filmes.ler_episodio("parei no S02E05"), (2, 5))
        self.assertEqual(filmes.ler_episodio("vi o episódio 3 da temporada 4"), (4, 3))
        self.assertEqual(filmes.ler_episodio("temporada 2, episódio 10"), (2, 10))
        self.assertIsNone(filmes.ler_episodio("um filme de 2005"))

    def test_pelo_chat(self):
        resultado = self.pedir("parei no S02E05 de Breaking Bad")
        self.assertEqual(resultado["tipo"], "usuario_atualizado")
        self.assertEqual(usuario.obter_progresso(self.bb), (2, 5))
        self.pedir("vi mais um episódio de Breaking Bad")
        self.assertEqual(usuario.obter_progresso(self.bb), (2, 6))
        self.assertIn("S02E06", self.pedir("onde eu parei?")["texto"])
        self.assertIn("De qual série", self.pedir("vi o próximo episódio")["texto"])


class TestListasTematicas(TesteCineAI):
    """Listas com nome ('pra chorar', 'com a família'...) que você mesma cria."""

    def test_criar_colocar_e_ver(self):
        usuario.criar_lista("  pra   chorar ")
        titanic, shrek = self.filme("Titanic"), self.filme("Shrek")
        self.assertTrue(usuario.alternar_na_lista_tematica("pra chorar", titanic))
        usuario.alternar_na_lista_tematica("pra chorar", shrek)
        self.assertEqual([f["nome"] for f in usuario.filmes_da_lista_tematica("pra chorar", filmes.filmes)],
                         ["Shrek", "Titanic"])
        self.assertEqual(usuario.listas_do_filme(titanic), ["pra chorar"])
        self.assertFalse(usuario.alternar_na_lista_tematica("pra chorar", titanic))
        usuario.dados_usuario = usuario.carregar_dados()   # "fecha e abre"
        self.assertEqual(usuario.nomes_das_listas(), ["pra chorar"])

    def test_nomes_repetidos_e_vazios(self):
        usuario.criar_lista("Com a Família")
        with self.assertRaises(ValueError):
            usuario.criar_lista("com a familia")    # mesma lista, só muda maiúscula/acento
        with self.assertRaises(ValueError):
            usuario.criar_lista("   ")

    def test_renomear_e_apagar(self):
        usuario.criar_lista("natal")
        usuario.criar_lista("terror")
        usuario.alternar_na_lista_tematica("natal", self.filme("Shrek"))
        usuario.renomear_lista("natal", "maratona de Natal")
        self.assertEqual(usuario.nomes_das_listas(), ["maratona de Natal", "terror"])   # continua no lugar
        self.assertTrue(usuario.esta_na_lista_tematica("maratona de Natal", self.filme("Shrek")))
        usuario.apagar_lista("terror")
        self.assertEqual(usuario.nomes_das_listas(), ["maratona de Natal"])

    def test_pelo_chat(self):
        usuario.criar_lista("pra chorar")
        resultado = self.pedir("coloca Titanic na lista pra chorar")
        self.assertEqual(resultado["tipo"], "usuario_atualizado")
        self.assertTrue(usuario.esta_na_lista_tematica("pra chorar", self.filme("Titanic")))
        self.assertIn("Titanic", self.pedir("o que tem na lista pra chorar?")["texto"])
        self.assertIn("pra chorar", self.pedir("quais são minhas listas?")["texto"])
        self.pedir("tira Titanic da lista pra chorar")
        self.assertFalse(usuario.esta_na_lista_tematica("pra chorar", self.filme("Titanic")))

    def test_minha_lista_continua_sendo_quero_assistir(self):
        """'Salva esse na minha lista' segue indo para o Quero assistir."""
        usuario.criar_lista("pra chorar")
        self.pedir("me fala do Titanic")
        self.pedir("salva esse na minha lista")
        self.assertTrue(usuario.quer_assistir(self.filme("Titanic")))


class TestMetaDoAno(TesteCineAI):
    """Meta do ano: títulos diferentes vistos no ano, com o ritmo até hoje."""

    def ver(self, nome, data):
        filme = self.filme(nome)
        usuario.alternar_assistido(filme)
        usuario.definir_data_assistido(filme, data)
        return filme

    def test_sem_meta(self):
        self.assertIsNone(usuario.progresso_da_meta(filmes.filmes, 2025))

    def test_progresso_e_ritmo(self):
        """Revisita não conta duas vezes; no meio do ano, metade da meta é 'no ritmo'."""
        from datetime import date
        usuario.definir_meta(2025, 4)
        shrek = self.ver("Shrek", date(2025, 1, 10))
        usuario.registrar_revisita(shrek, date(2025, 2, 1))
        self.ver("Titanic", date(2025, 3, 1))
        self.ver("Dunkirk", date(2024, 3, 1))   # outro ano: não conta
        progresso = usuario.progresso_da_meta(filmes.filmes, 2025, hoje=date(2025, 7, 2))
        self.assertEqual((progresso["feitos"], progresso["falta"], progresso["porcentagem"]), (2, 2, 50))
        self.assertTrue(progresso["no_ritmo"])
        self.assertEqual(progresso["por_mes"], 1)       # 2 faltando em 6 meses
        atrasado = usuario.progresso_da_meta(filmes.filmes, 2025, hoje=date(2025, 11, 15))
        self.assertFalse(atrasado["no_ritmo"])
        self.assertEqual(atrasado["por_mes"], 1)        # 2 faltando em 2 meses

    def test_batida_e_apagar(self):
        from datetime import date
        usuario.definir_meta(2025, 1)
        self.ver("Shrek", date(2025, 1, 10))
        self.assertTrue(usuario.progresso_da_meta(filmes.filmes, 2025)["batida"])
        self.assertEqual(usuario.retrospectiva_do_ano(filmes.filmes, 2025)["meta"], 1)
        usuario.definir_meta(2025, 0)
        self.assertIsNone(usuario.obter_meta(2025))
        with self.assertRaises(ValueError):
            usuario.definir_meta(2025, 5000)

    def test_pelo_chat(self):
        """'Minha meta é ver 30 filmes em 2025' grava; 'como está minha meta de 2025?' responde."""
        resultado = self.pedir("minha meta é ver 30 filmes em 2025")
        self.assertEqual(usuario.obter_meta(2025), 30)
        self.assertIn("30", resultado["texto"])
        self.assertIn("0 de 30", self.pedir("como está minha meta de 2025?")["texto"])


class TestLetterboxd(TesteCineAI):
    """Importar do Letterboxd: o .zip exportado vira diário, notas, anotações, favoritos e lista."""
    DIARIO = (
        "Date,Name,Year,Letterboxd URI,Rating,Rewatch,Tags,Watched Date\n"
        "2025-02-01,Shrek,2001,x,4.5,,,2025-01-31\n"
        "2025-06-10,Shrek,2001,x,5,Yes,,2025-06-09\n"
        "2025-03-05,Inception,2010,x,3.5,,,2025-03-04\n"
        "2025-03-06,Um Filme Que Não Existe,1999,x,3,,,2025-03-06\n"
    )
    NOTAS = "Date,Name,Year,Letterboxd URI,Rating\n2025-06-10,Shrek,2001,x,5\n2025-03-05,Inception,2010,x,3.5\n"
    RESENHAS = (
        "Date,Name,Year,Letterboxd URI,Rating,Rewatch,Review,Tags,Watched Date\n"
        "2025-06-10,Shrek,2001,x,5,Yes,<i>Ainda</i> ri muito com a família.,,2025-06-09\n"
    )
    VISTOS = "Date,Name,Year,Letterboxd URI\n2024-12-25,Titanic,1997,x\n2025-02-01,Shrek,2001,x\n"
    QUERO = "Date,Name,Year,Letterboxd URI\n2025-01-01,Dunkirk,2017,x\n"
    CURTIDOS = "Date,Name,Year,Letterboxd URI\n2025-02-02,Shrek,2001,x\n"

    def setUp(self):
        super().setUp()
        import copy
        import zipfile
        self.catalogo = copy.deepcopy(filmes.filmes)
        for filme in self.catalogo:
            if filme["nome"] == "A Origem":
                filme["titulo_original"] = "Inception"   # o Letterboxd usa o título em inglês
        self.zip = PASTA_TEMPORARIA / "letterboxd.zip"
        with zipfile.ZipFile(self.zip, "w") as pacote:
            pacote.writestr("diary.csv", "﻿" + self.DIARIO)
            pacote.writestr("ratings.csv", self.NOTAS)
            pacote.writestr("reviews.csv", self.RESENHAS)
            pacote.writestr("watched.csv", self.VISTOS)
            pacote.writestr("watchlist.csv", self.QUERO)
            pacote.writestr("likes/films.csv", self.CURTIDOS)

    def filme_do_catalogo(self, nome):
        return next(filme for filme in self.catalogo if filme["nome"] == nome)

    def test_importa_tudo(self):
        """Sessões, revisita com resenha, nota arredondada, favorito, lista e quem ficou de fora."""
        from datetime import date
        from cineai import letterboxd
        resumo = letterboxd.importar(self.catalogo, self.zip)
        shrek = self.filme_do_catalogo("Shrek")
        origem = self.filme_do_catalogo("A Origem")

        self.assertEqual(usuario.data_do_registro(usuario.chave_filme(shrek)), date(2025, 1, 31))
        self.assertEqual(usuario.quantas_vezes_viu(shrek), 2)
        self.assertEqual(usuario.obter_anotacao(shrek, sessao=0), "Ainda ri muito com a família.")
        self.assertEqual(usuario.obter_nota(shrek), 5)
        self.assertEqual(usuario.obter_nota(origem), 4)            # 3,5 -> 4
        self.assertTrue(usuario.foi_assistido(self.filme_do_catalogo("Titanic")))
        self.assertTrue(usuario.eh_favorito(shrek))
        self.assertTrue(usuario.quer_assistir(self.filme_do_catalogo("Dunkirk")))
        self.assertEqual(resumo["nao_encontrados"], ["Um Filme Que Não Existe (1999)"])
        self.assertEqual(resumo["filmes"], 3)
        self.assertEqual(resumo["sessoes"], 4)

    def test_importar_de_novo_nao_duplica(self):
        from cineai import letterboxd
        letterboxd.importar(self.catalogo, self.zip)
        resumo = letterboxd.importar(self.catalogo, self.zip)
        self.assertEqual((resumo["filmes"], resumo["sessoes"], resumo["notas"]), (0, 0, 0))
        self.assertEqual(usuario.quantas_vezes_viu(self.filme_do_catalogo("Shrek")), 2)

    def test_nao_apaga_o_que_ja_existe(self):
        """Nota e anotação do CineAI ficam; o backup é feito antes."""
        from cineai import letterboxd
        shrek = self.filme_do_catalogo("Shrek")
        usuario.definir_nota(shrek, 3)
        usuario.definir_anotacao(shrek, "Minha anotação do CineAI.")
        resumo = letterboxd.importar(self.catalogo, self.zip)
        self.assertEqual(usuario.obter_nota(shrek), 3)
        self.assertEqual(usuario.obter_anotacao(shrek), "Minha anotação do CineAI.")
        self.assertIsNotNone(resumo["backup"])
        # marcado hoje no CineAI, mas visto em janeiro segundo o Letterboxd: vale a data antiga
        from datetime import date
        self.assertEqual(usuario.data_do_registro(usuario.chave_filme(shrek)), date(2025, 1, 31))

    def test_simular_nao_grava(self):
        from cineai import letterboxd
        resumo = letterboxd.importar(self.catalogo, self.zip, simular=True)
        self.assertEqual(resumo["filmes"], 3)
        self.assertEqual(usuario.dados_usuario["assistidos"], {})

    def test_arquivo_errado(self):
        from cineai import letterboxd
        arquivo = PASTA_TEMPORARIA / "qualquer.txt"
        arquivo.write_text("oi", encoding="utf-8")
        with self.assertRaises(ValueError):
            letterboxd.importar(self.catalogo, arquivo)

    def test_conversoes(self):
        from cineai import letterboxd
        self.assertEqual([letterboxd.converter_nota(valor) for valor in ("0.5", "3.5", "4", "", "5")], [1, 4, 4, None, 5])
        self.assertEqual(letterboxd.limpar_resenha("Muito <b>bom</b>!<br/>Recomendo &amp; reveria"),
                         "Muito bom!\nRecomendo & reveria")


class TestBackup(TesteCineAI):
    """Backup do diário: cópias com data em dados/backups (aqui, na pasta temporária)."""

    def setUp(self):
        super().setUp()
        import shutil
        shutil.rmtree(usuario.PASTA_BACKUPS, ignore_errors=True)

    def test_fazer_e_restaurar(self):
        """Backup guarda tudo; restaurar volta o diário como estava (e guarda o estado atual antes)."""
        usuario.definir_nota(self.filme("Shrek"), 5)
        usuario.definir_anotacao(self.filme("Shrek"), "Ri muito com o burro.")
        caminho = usuario.fazer_backup()
        self.assertTrue(caminho.exists())
        self.assertIn("1 vistos", usuario.resumo_do_backup(caminho))

        usuario.alternar_assistido(self.filme("Shrek"))          # "apagou sem querer"
        usuario.definir_anotacao(self.filme("Shrek"), "")
        self.assertFalse(usuario.foi_assistido(self.filme("Shrek")))

        usuario.restaurar_backup(caminho)
        self.assertEqual(usuario.obter_nota(self.filme("Shrek")), 5)
        self.assertEqual(usuario.obter_anotacao(self.filme("Shrek")), "Ri muito com o burro.")
        self.assertEqual(len(usuario.listar_backups()), 2)        # o original + o "antes de restaurar"

    def test_guarda_so_os_10_mais_novos(self):
        """Com mais de 10 backups, os mais antigos são apagados."""
        from datetime import datetime, timedelta
        usuario.alternar_assistido(self.filme("Titanic"))
        inicio = datetime(2026, 1, 1, 12, 0, 0)
        for dias in range(13):
            usuario.fazer_backup(inicio + timedelta(days=dias))
        backups = usuario.listar_backups()
        self.assertEqual(len(backups), usuario.MAXIMO_BACKUPS)
        self.assertEqual(backups[0][1], inicio + timedelta(days=12))

    def test_automatico_so_depois_de_7_dias(self):
        """Sem nada no diário não faz; depois faz e só repete após 7 dias."""
        from datetime import datetime, timedelta
        agora = datetime(2026, 10, 4, 21, 0, 0)
        self.assertIsNone(usuario.backup_automatico_se_precisar(agora))   # diário vazio
        usuario.alternar_assistido(self.filme("Titanic"))
        self.assertIsNotNone(usuario.backup_automatico_se_precisar(agora))
        self.assertIsNone(usuario.backup_automatico_se_precisar(agora + timedelta(days=3)))
        self.assertIsNotNone(usuario.backup_automatico_se_precisar(agora + timedelta(days=8)))


class TestQueroAssistir(TesteCineAI):
    """Lista "Quero assistir": guardar pra depois, pelo botão ou pelo chat."""

    def test_guardar_o_filme_da_conversa(self):
        """'Salva esse pra depois' guarda o filme recomendado."""
        self.recomendado("Quero um filme do Nolan")
        atual = filmes.filme_atual
        resultado = self.pedir("salva esse pra depois")
        self.assertTrue(usuario.quer_assistir(atual))
        self.assertEqual(resultado["tipo"], "usuario_atualizado")
        self.assertIn("já está", self.pedir("guarda ele na minha lista")["texto"])

    def test_guardar_pelo_nome_e_tirar(self):
        """'Salva Interestelar pra depois' e 'tira Interestelar da minha lista'."""
        interestelar = self.filme("Interestelar")
        self.pedir("Salva Interestelar pra depois")
        self.assertTrue(usuario.quer_assistir(interestelar))
        self.pedir("tira Interestelar da minha lista")
        self.assertFalse(usuario.quer_assistir(interestelar))

    def test_ver_tira_da_lista(self):
        """Marcar como visto (ou dar nota) tira o título da lista sozinho."""
        shrek, titanic = self.filme("Shrek"), self.filme("Titanic")
        usuario.guardar_para_depois(shrek)
        usuario.guardar_para_depois(titanic)
        usuario.alternar_assistido(shrek)
        usuario.definir_nota(titanic, 4)
        self.assertFalse(usuario.quer_assistir(shrek))
        self.assertFalse(usuario.quer_assistir(titanic))

    def test_listar(self):
        """'O que eu queria assistir?' lista os guardados; vazio explica como guardar."""
        self.assertIn("vazia", self.pedir("o que eu queria assistir?")["texto"])
        usuario.guardar_para_depois(self.filme("Titanic"))
        self.assertIn("Titanic", self.pedir("o que tem na minha lista?")["texto"])

    def test_recomendar_da_lista(self):
        """O que espera há mais tempo vem primeiro; 'quero outro' traz o próximo da lista."""
        usuario.guardar_para_depois(self.filme("Titanic"))
        usuario.guardar_para_depois(self.filme("Shrek"))
        self.assertEqual(self.recomendado("me recomenda algo da minha lista"), "Titanic")
        self.assertEqual(self.recomendado("quero outro"), "Shrek")

    def test_frases_de_pedido_nao_viram_lista(self):
        """'Eu queria ver uma comédia' e 'quero ver um filme, por favor' continuam buscas."""
        for frase in ["eu queria ver uma comédia", "quero ver um filme de terror, por favor",
                      "quero assistir algo leve"]:
            self.assertIsNone(filmes.detectar_pedido_quero_assistir(frase), frase)

    def test_arquivo_antigo_sem_a_lista(self):
        """usuario.json antigo (sem 'quero_assistir') continua abrindo."""
        usuario.CAMINHO_USUARIO.write_text('{"favoritos": {}, "assistidos": {}}', encoding="utf-8")
        self.assertEqual(usuario.carregar_dados()["quero_assistir"], {})


class TestCapaDoDiario(TesteCineAI):
    """Números da capa do diário (usuario.estatisticas_do_diario)."""

    def test_diario_vazio(self):
        """Sem nada visto: tudo zerado, sem quebrar."""
        numeros = usuario.estatisticas_do_diario(filmes.filmes)
        self.assertEqual(numeros["total"], 0)
        self.assertIsNone(numeros["nota_media"])
        self.assertIsNone(numeros["genero"])
        self.assertIsNone(numeros["melhor"])
        self.assertEqual(numeros["horas"], 0)

    def test_numeros(self):
        """Contagens, nota média, diretor que se repete e o mais bem avaliado."""
        usuario.definir_nota(self.filme("A Origem"), 5)
        usuario.definir_nota(self.filme("Interestelar"), 4)
        usuario.definir_nota(self.filme("Titanic"), 3)
        numeros = usuario.estatisticas_do_diario(filmes.filmes)
        self.assertEqual(numeros["total"], 3)
        self.assertEqual(numeros["filmes"], 3)
        self.assertEqual(numeros["nota_media"], 4.0)
        self.assertEqual(numeros["pessoa"], ("Christopher Nolan", 2))
        self.assertEqual(numeros["melhor"]["filme"]["nome"], "A Origem")
        minutos = sum(self.filme(nome)["duracao_minutos"] for nome in ["A Origem", "Interestelar", "Titanic"])
        self.assertEqual(numeros["horas"], round(minutos / 60))
        self.assertFalse(numeros["horas_estimadas"])

    @apenas_modo_rapido  # depende dos episódios da série no catálogo de teste
    def test_serie_conta_como_estimativa(self):
        """Série soma episódios × duração e marca as horas como estimativa (≈)."""
        breaking_bad = self.filme("Breaking Bad")
        usuario.alternar_assistido(breaking_bad)
        numeros = usuario.estatisticas_do_diario(filmes.filmes)
        self.assertEqual(numeros["series"], 1)
        self.assertTrue(numeros["horas_estimadas"])
        esperado = breaking_bad["episodios"] * breaking_bad["duracao_minutos"]
        self.assertEqual(numeros["horas"], round(esperado / 60))

    def test_diretor_so_com_dois(self):
        """Com um título só de cada diretor, não há 'diretor que mais aparece'."""
        usuario.alternar_assistido(self.filme("Titanic"))
        self.assertIsNone(usuario.estatisticas_do_diario(filmes.filmes)["pessoa"])

    def test_nome_do_dono(self):
        """O nome da capa é salvo (com espaços arrumados) e apagado se vier vazio."""
        usuario.definir_nome_do_dono("  Eveliny   Gabrielle ")
        usuario.dados_usuario = usuario.carregar_dados()
        self.assertEqual(usuario.obter_nome_do_dono(), "Eveliny Gabrielle")
        usuario.definir_nome_do_dono("")
        self.assertEqual(usuario.obter_nome_do_dono(), "")


@apenas_modo_rapido  # usa as sinopses do catálogo de teste e os embeddings simulados
class TestAnotacoesNaRecomendacao(TesteCineAI):
    """Etapa 4: o que você escreve no diário entra na recomendação (RAG com as suas palavras)."""
    TEXTO_DINOSSAUROS = "Adorei os dinossauros clonados escapando do parque!"

    def anotar(self, nome, nota, texto):
        filme = self.filme(nome)
        usuario.definir_nota(filme, nota)
        usuario.definir_anotacao(filme, texto)
        return filme

    def test_anotacao_positiva_puxa(self):
        """Nota 5★ com texto sobre dinossauros: Jurassic Park ganha a maior parte de anotações."""
        self.anotar("Titanic", 5, self.TEXTO_DINOSSAUROS)
        perfil_atual = perfil.calcular_perfil(filmes.filmes)
        jurassic = self.filme("Jurassic Park: O Parque dos Dinossauros")
        partes = {f["nome"]: perfil.parte_das_anotacoes(f, perfil_atual) for f in filmes.filmes}
        self.assertGreater(partes[jurassic["nome"]], 0.3)
        self.assertEqual(max(partes, key=partes.get), jurassic["nome"])
        self.assertIn("Titanic", perfil.frase_da_anotacao(jurassic, perfil_atual))

    def test_anotacao_negativa_afasta(self):
        """O mesmo texto num título com 1★ empurra Jurassic Park para baixo."""
        self.anotar("Titanic", 1, self.TEXTO_DINOSSAUROS)
        perfil_atual = perfil.calcular_perfil(filmes.filmes)
        jurassic = self.filme("Jurassic Park: O Parque dos Dinossauros")
        self.assertLess(perfil.parte_das_anotacoes(jurassic, perfil_atual), 0)
        self.assertIsNone(perfil.frase_da_anotacao(jurassic, perfil_atual))

    def test_anotacao_sentimental_usa_a_ancora(self):
        """'Marcou minha infância' em Shrek não fala do filme: a âncora (sinopse do Shrek) traz Shrek 2."""
        shrek = self.anotar("Shrek", 5, "Marcou muito minha infância")
        perfil_atual = perfil.calcular_perfil(filmes.filmes)
        anotacao = perfil_atual["anotacoes"][0]
        vizinhos = perfil.vizinhos_da_anotacao(anotacao, filmes.filmes)
        self.assertEqual(vizinhos[0][1]["nome"], "Shrek 2")
        self.assertNotIn(shrek["nome"], [filme["nome"] for _, filme in vizinhos])

    def test_anotacao_curta_nao_conta(self):
        """'Amei!' não diz sobre o quê: fica de fora da busca pelas anotações."""
        self.anotar("Titanic", 5, "Amei!")
        self.assertEqual(perfil.calcular_perfil(filmes.filmes)["anotacoes"], [])

    def test_partes_nao_empatam_no_teto(self):
        """Bug do catálogo real: todos davam +1,00. Agora a curva suave nunca chega a 1."""
        self.anotar("Titanic", 5, self.TEXTO_DINOSSAUROS)
        perfil_atual = perfil.calcular_perfil(filmes.filmes)
        partes = [perfil.parte_das_anotacoes(filme, perfil_atual) for filme in filmes.filmes]
        self.assertLess(max(partes), 1.0)

    def test_tres_estrelas_nao_conta(self):
        """Anotação de título com 3★ (neutro) não entra no perfil."""
        self.anotar("Titanic", 3, self.TEXTO_DINOSSAUROS)
        self.assertEqual(perfil.calcular_perfil(filmes.filmes)["anotacoes"], [])

    def test_explicacao_cita_a_anotacao(self):
        """Com perfil completo, a explicação ganha a linha 📝 com o trecho do que você escreveu."""
        self.anotar("Titanic", 5, self.TEXTO_DINOSSAUROS)
        usuario.definir_nota(self.filme("Shrek"), 5)
        usuario.definir_nota(self.filme("Dunkirk"), 4)
        perfil_atual = perfil.calcular_perfil(filmes.filmes)
        explicacao = perfil.explicar_recomendacao(self.filme("Jurassic Park: O Parque dos Dinossauros"), perfil_atual)
        self.assertIn("📝 Lembra o que você escreveu sobre Titanic", explicacao)

    def test_pedido_pelo_chat(self):
        """'Me recomenda algo pelo que eu escrevi no diário' usa as anotações (e avisa se não houver)."""
        self.assertIn("Ainda não tenho anotações", self.pedir("me recomenda algo pelo que eu escrevi no diário")["texto"])
        self.anotar("Titanic", 5, self.TEXTO_DINOSSAUROS)
        resultado = self.pedir("me recomenda algo pelo que eu escrevi no diário")
        self.assertEqual(resultado["filme"]["nome"], "Jurassic Park: O Parque dos Dinossauros")
        self.assertIn("📝", resultado["texto"])
        titulos = [etapa["titulo"] for etapa in resultado["rastro"]["etapas"]]
        self.assertIn("Ranking pelas suas anotações", titulos)


# =========================================================
# 8. ESTRELAS
# =========================================================
class TestEstrelas(TesteCineAI):

    def test_nota_marca_assistido(self):
        """Dar nota marca o filme como assistido; desmarcar apaga a nota."""
        shrek = self.filme("Shrek")
        usuario.definir_nota(shrek, 4)
        self.assertTrue(usuario.foi_assistido(shrek))
        usuario.alternar_assistido(shrek)
        self.assertIsNone(usuario.obter_nota(shrek))

    def test_nota_invalida(self):
        """Nota fora de 1 a 5 é recusada."""
        with self.assertRaises(ValueError):
            usuario.definir_nota(self.filme("Shrek"), 7)

    def test_dar_nota_pelo_chat(self):
        """'Dou 5 estrelas para Shrek' salva a nota."""
        resultado = self.pedir("Dou 5 estrelas para Shrek")
        self.assertEqual(resultado["tipo"], "usuario_atualizado")
        self.assertEqual(usuario.obter_nota(self.filme("Shrek")), 5)

    def test_nota_para_filme_atual(self):
        """'Dou 4 estrelas pra esse' vale para o filme recomendado."""
        nome = self.recomendado("Quero uma animação de 2001 com Eddie Murphy")
        self.pedir("Dou 4 estrelas pra esse")
        self.assertEqual(usuario.obter_nota(self.filme(nome)), 4)

    def test_consultar_e_listar(self):
        """'Qual nota eu dei' e 'Quais filmes eu dei 5 estrelas?'."""
        usuario.definir_nota(self.filme("Shrek"), 5)
        usuario.definir_nota(self.filme("Titanic"), 3)
        self.assertIn("★★★★★", self.pedir("Qual nota eu dei para Shrek?")["texto"])
        lista = self.pedir("Quais filmes eu dei 5 estrelas?")["texto"]
        self.assertIn("Shrek", lista)
        self.assertNotIn("Titanic", lista)

    def test_nao_confunde(self):
        """'Qual a nota?' é sobre o filme; 'filme nota alta' não salva nota."""
        self.recomendado("Quero uma animação de 2001 com Eddie Murphy")
        self.assertTrue(self.pedir("Qual a nota?")["texto"].startswith("🍅"))
        self.assertNotEqual(self.pedir("Quero um filme nota alta")["tipo"], "usuario_atualizado")


# =========================================================
# 9. PERFIL E RECOMENDAÇÃO PERSONALIZADA
# =========================================================
class TestPerfil(TesteCineAI):

    def dar_notas_de_fa_de_animacao(self):
        usuario.definir_nota(self.filme("Shrek"), 5)
        usuario.definir_nota(self.filme("Toy Story: Um Mundo de Aventuras"), 5)
        usuario.alternar_favorito(self.filme("Toy Story: Um Mundo de Aventuras"))
        usuario.definir_nota(self.filme("O Rei Leão", 1994), 4)
        usuario.definir_nota(self.filme("Dunkirk"), 1)

    def test_suavizacao(self):
        """1 filme com 5★ vale menos que 2 filmes com 5★ do mesmo gênero."""
        usuario.definir_nota(self.filme("Psicose"), 5)
        afinidade_um = perfil.calcular_perfil(filmes.filmes)["generos"]["terror"]["afinidade"]
        usuario.definir_nota(self.filme("Invocação do Mal"), 5)
        afinidade_dois = perfil.calcular_perfil(filmes.filmes)["generos"]["terror"]["afinidade"]
        self.assertAlmostEqual(afinidade_um, 2 / math.sqrt(1 + perfil.SUAVIZACAO), places=2)
        self.assertGreater(afinidade_dois, afinidade_um)

    def test_nota_positiva_nunca_diminui_o_gosto(self):
        """Bug encontrado pelos testes: um 4★ a mais em Animação não pode diminuir a afinidade."""
        usuario.definir_nota(self.filme("Shrek"), 5)
        usuario.definir_nota(self.filme("Toy Story: Um Mundo de Aventuras"), 5)
        antes = perfil.calcular_perfil(filmes.filmes)["generos"]["animacao"]["afinidade"]
        usuario.definir_nota(self.filme("O Rei Leão", 1994), 4)
        depois = perfil.calcular_perfil(filmes.filmes)["generos"]["animacao"]["afinidade"]
        self.assertGreater(depois, antes)

    def test_genero_favorito(self):
        """Quem dá 5★ para animações tem Animação no topo e Guerra nos evitados."""
        self.dar_notas_de_fa_de_animacao()
        perfil_atual = perfil.calcular_perfil(filmes.filmes)
        nomes_top = [item["nome"] for item in perfil.itens_ordenados(perfil_atual["generos"], quantidade=2)]
        self.assertIn("Animação", nomes_top)
        evitados = [item["nome"] for item in perfil.itens_ordenados(perfil_atual["generos"], positivos=False)]
        self.assertIn("Guerra", evitados)

    def test_sinais_se_anulam(self):
        """5★ e 1★ no mesmo diretor dão afinidade zero."""
        usuario.definir_nota(self.filme("A Origem"), 5)
        usuario.definir_nota(self.filme("Dunkirk"), 1)
        perfil_atual = perfil.calcular_perfil(filmes.filmes)
        self.assertAlmostEqual(perfil_atual["diretores"]["christopher nolan"]["afinidade"], 0.0)

    def test_recomendar_nao_traz_assistidos(self):
        """A grade 'Para você' nunca mostra filme já assistido."""
        self.dar_notas_de_fa_de_animacao()
        recomendados = perfil.recomendar(filmes.filmes, perfil.calcular_perfil(filmes.filmes))
        self.assertFalse(any(usuario.foi_assistido(filme) for filme in recomendados))

    def test_perfil_pequeno_avisa(self):
        """Com menos de 3 filmes, 'Me recomenda algo' avisa que ainda está te conhecendo."""
        self.assertTrue(self.pedir("Me recomenda algo")["texto"].startswith("Ainda estou te conhecendo"))

    @apenas_modo_rapido
    def test_recomendacao_explicada(self):
        """Com perfil, 'Me recomenda algo' traz animação e explica com 💡."""
        self.dar_notas_de_fa_de_animacao()
        resultado = self.pedir("Me recomenda algo")
        self.assertIn("Animação", resultado["filme"]["genero"])
        self.assertIn("💡 Combina com você", resultado["texto"])

    def test_qualidade_pesa(self):
        """Bug antigo: comédia de 10% não pode ganhar de uma de 91% só por ter menos gêneros."""
        if MODO_COMPLETO:
            self.skipTest("depende do catálogo de teste")
        self.dar_notas_de_fa_de_animacao()
        self.assertNotEqual(self.recomendado("Quero uma comédia pra mim"), "Gente Grande")

    def test_pedidos_personalizados(self):
        """Frases genéricas usam o perfil; frases com critério não."""
        for frase in ["Me recomenda algo", "Quero um filme", "O que eu deveria assistir?", "uma comédia pra mim"]:
            self.assertTrue(filmes.eh_pedido_personalizado(frase), frase)
        for frase in ["Quero uma comédia", "Eu gostaria de uma comédia"]:
            self.assertFalse(filmes.eh_pedido_personalizado(frase), frase)

    def test_pergunta_sobre_perfil(self):
        """'Qual é o meu gênero favorito?' mostra o resumo do perfil."""
        self.dar_notas_de_fa_de_animacao()
        self.assertTrue(self.pedir("Qual é o meu gênero favorito?")["texto"].startswith("Seu perfil"))


# =========================================================
# 10. PEDIDOS RELATIVOS ("parecido com esse")
# =========================================================
class TestRelativos(TesteCineAI):

    def test_deteccao(self):
        """Cada expressão vira o tipo certo."""
        casos = {
            "algo parecido com esse": "parecido",
            "um mais recente": "mais_recente",
            "Quero outro filme do mesmo diretor": "mesmo_diretor",
            "com a mesma atriz": "mesmo_ator",
            "um mais curto": "mais_curto",
            "parecido com meus favoritos": None,
        }
        for frase, esperado in casos.items():
            self.assertEqual(filmes.detectar_pedido_relativo(frase), esperado, frase)

    def test_mesmo_diretor(self):
        """'Um do mesmo diretor' depois de um Nolan traz outro Nolan."""
        primeiro = self.pedir("Quero um filme do Nolan")["filme"]
        segundo = self.pedir("Um do mesmo diretor")["filme"]
        self.assertIn("Christopher Nolan", segundo["diretor"])
        self.assertNotEqual(primeiro["id"], segundo["id"])

    def test_mais_recente_mantem_criterio(self):
        """'Um mais recente' depois de 'do Nolan' continua no Nolan e é mais novo."""
        primeiro = self.pedir("Quero um filme do Nolan")["filme"]
        segundo = self.pedir("Quero um mais recente")["filme"]
        self.assertGreater(segundo["ano"], primeiro["ano"])
        self.assertIn("Christopher Nolan", segundo["diretor"])

    def test_parecido_com_filme_citado(self):
        """'Parecido com Shrek' funciona mesmo sem filme na conversa."""
        resultado = self.pedir("Quero um filme parecido com Shrek")
        self.assertEqual(resultado["tipo"], "recomendacao")
        self.assertNotEqual(resultado["filme"]["nome"], "Shrek")
        self.assertIn("🔗", resultado["texto"])

    def test_sem_referencia(self):
        """'Algo parecido com esse' sem filme pergunta qual."""
        self.assertIn("Com base em qual filme", self.pedir("algo parecido com esse")["texto"])


# =========================================================
# 11. FORA DO ESCOPO
# =========================================================
class TestForaDoEscopo(TesteCineAI):

    def test_perguntas_gerais(self):
        """Capital do Japão e contas recebem 'eu só entendo de filmes'."""
        for frase in ["Qual é a capital do Japão?", "Quanto é 2 + 2?", "Que dia é hoje?"]:
            self.assertEqual(self.pedir(frase)["tipo"], "fora_do_escopo", frase)

    def test_perguntas_de_cinema_passam(self):
        """Perguntas de cinema NÃO são bloqueadas."""
        for frase in ["Qual é o melhor filme de 2014?", "Quem é o Christopher Nolan?", "Qual nota eu dei para Shrek?"]:
            self.assertFalse(filmes.parece_fora_do_escopo(frase), frase)

    def test_personagem_do_filme_atual(self):
        """Com Toy Story na conversa, 'Por que o Woody tem ciúmes?' é sobre o filme."""
        toy_story = self.filme("Toy Story: Um Mundo de Aventuras")
        self.assertFalse(filmes.parece_fora_do_escopo("Por que o Woody tem ciúmes?", toy_story))
        self.assertTrue(filmes.parece_fora_do_escopo("Qual é a capital do Japão?", toy_story))


# =========================================================
# 12. HISTÓRICO DE CONVERSAS
# =========================================================
class TestConversas(TesteCineAI):

    def test_titulo_e_salvamento(self):
        """A primeira mensagem vira o título, e a conversa vai para o arquivo."""
        conversa = conversas.nova_conversa()
        conversas.registrar_mensagem(conversa, conversas.AUTOR_VOCE, "Quero uma animação de 2001 com Eddie Murphy")
        conversas.registrar_mensagem(conversa, conversas.AUTOR_CINEAI, "Shrek (2001)...", "808")
        self.assertEqual(conversa["titulo"], "Quero uma animação de 2001 com Eddie Murphy")
        importlib.reload(conversas)
        salva = conversas.buscar_por_id(conversa["id"])
        self.assertIsNotNone(salva)
        self.assertEqual(len(salva["mensagens"]), 2)
        self.assertEqual(salva["filmes_recomendados"], ["808"])

    def test_conversa_vazia_nao_salva(self):
        """Conversa sem mensagens não aparece na lista."""
        conversas.nova_conversa()
        self.assertEqual(conversas.conversas_salvas(), [])

    def test_apagar(self):
        """Apagar remove a conversa do arquivo."""
        conversa = conversas.nova_conversa()
        conversas.registrar_mensagem(conversa, conversas.AUTOR_VOCE, "oi")
        conversas.apagar(conversa["id"])
        importlib.reload(conversas)
        self.assertIsNone(conversas.buscar_por_id(conversa["id"]))

    def test_restaurar_contexto(self):
        """Reabrir a conversa traz de volta o filme atual: 'Quem dirigiu ele?' funciona."""
        filmes.restaurar_contexto([usuario.chave_filme(self.filme("Shrek"))])
        self.assertIn("Andrew Adamson", self.pedir("Quem dirigiu ele?")["texto"])

    def test_titulo_longo_cortado(self):
        """Títulos longos são cortados com '…'."""
        titulo = conversas.criar_titulo("a" * 100)
        self.assertLessEqual(len(titulo), conversas.TAMANHO_MAXIMO_TITULO)
        self.assertTrue(titulo.endswith("…"))


# =========================================================
# 13. SEMELHANTES, TRAILER, SURPRESA E FRASES CURTAS
# =========================================================
@apenas_modo_rapido  # usa os filmes e séries do catálogo de teste
class TestVitoriasRapidas(TesteCineAI):

    # ---------- semelhantes ----------
    def test_semelhantes_de_shrek(self):
        """Os semelhantes de Shrek começam por Shrek 2 e não incluem o próprio Shrek."""
        semelhantes = filmes.filmes_semelhantes(self.filme("Shrek"))
        nomes = [filme["nome"] for filme in semelhantes]
        self.assertEqual(len(semelhantes), filmes.QUANTIDADE_SEMELHANTES)
        self.assertNotIn("Shrek", nomes)
        self.assertEqual(nomes[0], "Shrek 2")

    # ---------- trailer ----------
    def test_trailer_salvo_e_busca(self):
        """Com código salvo abre o vídeo; sem código abre a busca do YouTube."""
        filme_com_trailer = dict(self.filme("Shrek"), trailer_youtube="abc123")
        self.assertEqual(filmes.url_trailer(filme_com_trailer), "https://www.youtube.com/watch?v=abc123")

        url_busca = filmes.url_trailer(self.filme("Interestelar"))
        self.assertTrue(url_busca.startswith("https://www.youtube.com/results?search_query="))
        self.assertIn("Interestelar", url_busca)
        self.assertNotIn(" ", url_busca)

    def test_escolhe_trailer_em_portugues(self):
        """Entre os vídeos do TMDB, o trailer em português do YouTube vence."""
        try:
            from importadores import importar_tmdb
        except ImportError:
            self.skipTest("biblioteca requests não instalada")
        videos = {"results": [
            {"site": "YouTube", "type": "Teaser", "key": "teaser", "iso_639_1": "pt"},
            {"site": "YouTube", "type": "Trailer", "key": "ingles", "iso_639_1": "en", "official": True},
            {"site": "YouTube", "type": "Trailer", "key": "portugues", "iso_639_1": "pt"},
            {"site": "Vimeo", "type": "Trailer", "key": "vimeo", "iso_639_1": "pt"},
        ]}
        self.assertEqual(importar_tmdb.escolher_trailer(videos), "portugues")
        self.assertIsNone(importar_tmdb.escolher_trailer({"results": []}))

    # ---------- surpreenda-me ----------
    def test_surpresa_varia_e_nao_repete_assistidos(self):
        """'Me surpreenda' sorteia filmes diferentes e nunca um que você já viu."""
        usuario.alternar_assistido(self.filme("Shrek"))
        sorteados = set()
        for semente in range(15):
            filmes.random.seed(semente)
            filmes.reiniciar_conversa()
            nome = self.recomendado("Me surpreenda!")
            self.assertNotEqual(nome, "Shrek")
            sorteados.add(nome)
        self.assertGreater(len(sorteados), 2)

    def test_surpresa_evita_repetir_na_conversa(self):
        """Pedindo 'Me surpreenda' várias vezes na mesma conversa, não repete."""
        nomes = [self.recomendado("Me surpreenda") for _ in range(5)]
        self.assertEqual(len(nomes), len(set(nomes)))

    # ---------- explicação ----------
    def test_explicacao_dos_filtros(self):
        """A recomendação diz quais filtros levaram ao filme."""
        texto = self.pedir("Quero uma comédia com Jack Black")["texto"]
        self.assertIn("💡", texto)
        self.assertIn("comédia", texto)
        self.assertIn("Jack Black", texto)

    def test_explicacao_do_assunto(self):
        """Busca por assunto mostra as palavras em comum com a sinopse."""
        texto = self.pedir("Quero um filme sobre um ogro que resgata uma princesa")["texto"]
        self.assertIn("💡", texto)
        self.assertIn("ogro", texto)

    # ---------- esse não ----------
    def test_esse_nao(self):
        """'Esse não' funciona como 'Quero outro'."""
        primeiro = self.pedir("Quero um filme do Nolan")["filme"]
        segundo = self.pedir("Esse não")["filme"]
        self.assertIsNotNone(segundo)
        self.assertNotEqual(primeiro["id"], segundo["id"])
        self.assertIn("Christopher Nolan", segundo["diretor"])

    def test_rejeicao_nao_engole_busca(self):
        """'Não quero terror' traz assunto novo: não é rejeição."""
        self.assertTrue(filmes.eh_rejeicao("Não gostei desse"))
        self.assertTrue(filmes.eh_rejeicao("pula"))
        self.assertFalse(filmes.eh_rejeicao("Não quero terror"))
        self.assertFalse(filmes.eh_rejeicao("Quero um filme do Nolan"))

    # ---------- já vi esse ----------
    def test_ja_vi_esse(self):
        """'Já vi esse' marca como assistido e recomenda o próximo."""
        primeiro = self.pedir("Quero um filme do Nolan")["filme"]
        resultado = self.pedir("Já vi esse")
        self.assertTrue(usuario.foi_assistido(primeiro))
        self.assertTrue(resultado["atualizou_usuario"])
        self.assertEqual(resultado["tipo"], "recomendacao")
        self.assertNotEqual(resultado["filme"]["id"], primeiro["id"])

    def test_ja_vi_nao_e_pedido_de_nota(self):
        """'Já vi Shrek e dei 5 estrelas' não é o atalho 'já vi esse'."""
        self.assertTrue(filmes.eh_ja_vi_esse("Esse eu já vi"))
        self.assertFalse(filmes.eh_ja_vi_esse("Já vi Shrek e dei 5 estrelas"))

    # ---------- leve / tenso ----------
    def test_algo_leve(self):
        """'Quero algo leve' sem filme na conversa traz um filme leve."""
        resultado = self.pedir("Quero algo leve")
        self.assertEqual(resultado["tipo"], "recomendacao")
        self.assertGreaterEqual(filmes.leveza(resultado["filme"]), filmes.LEVEZA_MINIMA_ABSOLUTA)
        self.assertIn("☀️", resultado["texto"])

    def test_leve_nao_e_puxado_por_genero_pesado(self):
        """Quem ama Drama pede 'algo leve': não vem um filme leve 'por pouco' explicado por Drama."""
        for nome in ["Titanic", "O Diabo Veste Prada", "Dunkirk"]:
            usuario.definir_nota(self.filme(nome), 5)
        resultado = self.pedir("Quero algo leve")
        self.assertGreater(filmes.leveza(resultado["filme"]), filmes.LEVEZA_MINIMA_ABSOLUTA)
        explicacao = [linha for linha in resultado["texto"].splitlines() if "Combina com você" in linha]
        for linha in explicacao:
            self.assertNotIn("Drama", linha)

    def test_mais_tenso_que_o_atual(self):
        """Depois de Shrek, 'algo mais tenso' traz um filme mais pesado."""
        shrek = self.filme("Shrek")
        self.pedir("Quero um filme parecido com Shrek 2")
        filmes.filme_atual = shrek
        resultado = self.pedir("Quero algo mais tenso")
        self.assertLess(filmes.leveza(resultado["filme"]), filmes.leveza(shrek))

    # ---------- histórico ----------
    def test_primeiro_e_anterior(self):
        """'Qual foi o primeiro que você recomendou?' e 'o anterior' voltam no histórico."""
        primeiro = self.pedir("Quero um filme do Nolan")["filme"]
        segundo = self.pedir("Quero outro")["filme"]
        self.pedir("Quero outro")

        resultado = self.pedir("Qual foi o primeiro que você recomendou?")
        self.assertEqual(resultado["filme"]["id"], primeiro["id"])
        self.assertIn("Christopher Nolan", self.pedir("Quem dirigiu ele?")["texto"])

        filmes.filme_atual = filmes.historico_recomendacoes[2]
        self.assertEqual(self.pedir("o anterior")["filme"]["id"], segundo["id"])

    def test_lista_de_recomendados(self):
        """'Quais você já recomendou?' lista os filmes da conversa."""
        self.pedir("Quero um filme do Nolan")
        self.pedir("Quero outro")
        texto = self.pedir("Quais você já recomendou?")["texto"]
        self.assertIn("1.", texto)
        self.assertIn("2.", texto)

    def test_primeiro_filme_do_diretor_nao_e_historico(self):
        """'Qual foi o primeiro filme do Nolan?' não é pergunta sobre o histórico."""
        self.assertIsNone(filmes.detectar_pedido_de_historico("Qual foi o primeiro filme do Nolan?"))

    def test_historico_restaurado(self):
        """Reabrir uma conversa recupera o histórico sem repetir filmes."""
        chave_shrek = usuario.chave_filme(self.filme("Shrek"))
        chave_titanic = usuario.chave_filme(self.filme("Titanic"))
        filmes.restaurar_contexto([chave_shrek, chave_shrek, chave_titanic])
        self.assertEqual([filme["nome"] for filme in filmes.historico_recomendacoes], ["Shrek", "Titanic"])
        self.assertEqual(filmes.filme_atual["nome"], "Titanic")


# =========================================================
# 14. PAINEL DO RAG (rastro de cada resposta)
# =========================================================
@apenas_modo_rapido  # usa os filmes e séries do catálogo de teste
class TestPainelRAG(TesteCineAI):

    def titulos(self, resultado):
        return [etapa["titulo"] for etapa in resultado["rastro"]["etapas"]]

    def test_busca_por_assunto_mostra_o_caminho(self):
        """Busca por assunto: filtros, IA, assunto, similaridades, limite e resposta."""
        resultado = self.pedir("Quero um filme sobre um ogro que resgata uma princesa")
        titulos = self.titulos(resultado)
        for esperado in ["Filtros exatos", "IA (extrair assunto)", "Assunto da busca",
                         "Busca semântica (embeddings)", "Limite de similaridade", "Resposta"]:
            self.assertIn(esperado, titulos)
        self.assertEqual(resultado["rastro"]["chamadas_ia"], 1)

        ranking = next(e for e in resultado["rastro"]["etapas"] if e["tabela"])
        self.assertEqual(ranking["tabela"]["linhas"][0][0], "Shrek")
        self.assertLessEqual(len(ranking["tabela"]["linhas"]), 5)

    def test_saudacao_sem_ia(self):
        """'oi' é resolvido só por regra: nenhuma chamada à IA."""
        rastro_oi = self.pedir("oi")["rastro"]
        self.assertEqual(rastro_oi["chamadas_ia"], 0)
        self.assertIn("saudação", rastro_oi["etapas"][0]["detalhe"])

    def test_tempos_e_historico(self):
        """Toda etapa tem tempo, e o histórico guarda a mensagem mais nova primeiro."""
        self.pedir("Quero um filme do Nolan")
        ultimo = self.pedir("Quero outro")["rastro"]
        self.assertGreaterEqual(ultimo["total_ms"], 0)
        self.assertTrue(all(etapa["ms"] >= 0 for etapa in ultimo["etapas"]))
        self.assertEqual(rastreio.rastro.historico[0]["mensagem"], "Quero outro")

    def test_ranking_do_perfil(self):
        """'Me recomenda algo' com perfil mostra a tabela do ranking pelo seu gosto."""
        for nome in ["Shrek", "Toy Story: Um Mundo de Aventuras", "Uma Aventura Lego"]:
            usuario.definir_nota(self.filme(nome), 5)
        titulos = self.titulos(self.pedir("Me recomenda algo"))
        self.assertIn("Ranking pelo seu perfil", titulos)
        self.assertIn("Já assistidos", titulos)

    def test_funcoes_soltas_nao_quebram(self):
        """Sem rastro iniciado (funções chamadas direto), nada é gravado e nada quebra."""
        filmes.filtrar_filmes("Quero uma comédia")
        self.assertIsNone(rastreio.rastro.atual)


# =========================================================
# 15. COMPARAR TÍTULOS
# =========================================================
@apenas_modo_rapido  # usa os filmes e séries do catálogo de teste
class TestComparar(TesteCineAI):

    def nomes(self, frase):
        dupla = filmes.detectar_comparacao(frase)
        return [filme["nome"] for filme in dupla] if dupla else None

    def test_deteccao(self):
        """'X ou Y?', 'compare X e Y' e 'X vs Y' viram comparação, na ordem da frase."""
        self.assertEqual(self.nomes("Interestelar ou A Origem?"), ["Interestelar", "A Origem"])
        self.assertEqual(self.nomes("Compare Titanic e Dunkirk"), ["Titanic", "Dunkirk"])
        self.assertEqual(self.nomes("Psicose vs Invocação do Mal"), ["Psicose", "Invocação do Mal"])

    def test_titulo_maior_ganha(self):
        """Em 'Shrek ou Shrek 2', 'Shrek 2' não é confundido com 'Shrek'."""
        self.assertEqual(self.nomes("Shrek ou Shrek 2?"), ["Shrek", "Shrek 2"])
        self.assertEqual(
            self.nomes("Toy Story 2 ou Toy Story?"),
            ["Toy Story 2", "Toy Story: Um Mundo de Aventuras"]
        )

    def test_nao_e_comparacao(self):
        """Pedido com 'ou' sem dois filmes, ou 'parecido com X ou Y', não compara."""
        self.assertIsNone(self.nomes("Quero um filme de ação ou comédia"))
        self.assertIsNone(self.nomes("Quero algo parecido com Shrek ou Toy Story"))
        self.assertIsNone(self.nomes("Quero rever Shrek"))

    def test_esse_ou_outro(self):
        """'Esse ou Perdido em Marte?' compara o filme da conversa com o citado."""
        atual = self.pedir("Quero um filme do Nolan")["filme"]
        resultado = self.pedir("Esse ou Perdido em Marte?")
        self.assertEqual(resultado["tipo"], "comparacao")
        self.assertEqual(resultado["comparacao"]["filmes"][0]["id"], atual["id"])
        self.assertEqual(resultado["comparacao"]["filmes"][1]["nome"], "Perdido em Marte")

    def test_vencedores_e_em_comum(self):
        """A Origem ganha na crítica e na duração; os dois são do Nolan."""
        resultado = self.pedir("Interestelar ou A Origem?")
        comparacao = resultado["comparacao"]
        linhas = {linha["rotulo"]: linha for linha in comparacao["linhas"]}
        self.assertEqual(linhas["Rotten (crítica)"]["vencedor"], 1)
        self.assertEqual(linhas["Duração"]["vencedor"], 1)      # menor duração vence
        self.assertIsNone(linhas["Metacritic"]["vencedor"])     # 74 × 74: empate
        self.assertTrue(any("Christopher Nolan" in item for item in comparacao["em_comum"]))
        self.assertIn("A crítica prefere A Origem", resultado["texto"])


# =========================================================
# 16. BUSCA AVANÇADA DO CATÁLOGO
# =========================================================
@apenas_modo_rapido  # usa os filmes e séries do catálogo de teste
class TestBuscaAvancada(TesteCineAI):

    def nomes(self, **filtros):
        return [filme["nome"] for filme in filmes.filtrar_catalogo(**filtros)]

    def test_sem_filtro_traz_tudo(self):
        """Sem filtro: todos os filmes, do mais popular ao menos popular."""
        lista = filmes.filtrar_catalogo()
        self.assertEqual(len(lista), len(filmes.filmes))
        self.assertEqual(lista[0]["nome"], "A Origem")  # 36000 votos

    def test_texto_com_varias_palavras(self):
        """'nolan 2010' exige as duas palavras: só A Origem."""
        self.assertEqual(self.nomes(texto="nolan 2010"), ["A Origem"])
        self.assertIn("Titanic", self.nomes(texto="dicaprio"))

    def test_genero_e_decada(self):
        """Animação dos anos 1990: os dois Toy Story e O Rei Leão de 1994."""
        nomes = self.nomes(genero="Animação", decada="Anos 1990")
        self.assertEqual(set(nomes), {"Toy Story: Um Mundo de Aventuras", "Toy Story 2", "O Rei Leão"})

    def test_antes_de_1980(self):
        """Psicose (1960) fica em 'Antes de 1980'."""
        self.assertEqual(self.nomes(decada="Antes de 1980"), ["Psicose"])
        self.assertEqual(filmes.decadas_do_catalogo()[-1], "Antes de 1980")

    def test_nota_minima_e_ordem_da_critica(self):
        """Rotten 90%+, da maior nota para a menor."""
        lista = filmes.filtrar_catalogo(nota_minima=90, ordem="Crítica (Rotten)")
        notas = [filmes.nota_da_critica(filme) for filme in lista]
        self.assertTrue(all(nota >= 90 for nota in notas))
        self.assertEqual(notas, sorted(notas, reverse=True))

    def test_outras_ordens(self):
        """Mais antigos, mais curtos e A–Z."""
        self.assertEqual(self.nomes(ordem="Mais antigos")[0], "Psicose")
        self.assertEqual(self.nomes(ordem="Mais curtos")[0], "Toy Story: Um Mundo de Aventuras")  # 81 min
        self.assertEqual(self.nomes(ordem="A–Z")[0], "A Origem")

    def test_esconder_assistidos(self):
        """'Esconder os que já vi' tira os assistidos."""
        usuario.alternar_assistido(self.filme("Shrek"))
        self.assertNotIn("Shrek", self.nomes(esconder_assistidos=True))
        self.assertIn("Shrek", self.nomes(esconder_assistidos=False))

    def test_combina_comigo(self):
        """'Combina comigo' com perfil de animação põe animações na frente."""
        for nome in ["Shrek", "Toy Story: Um Mundo de Aventuras", "Uma Aventura Lego"]:
            usuario.definir_nota(self.filme(nome), 5)
        primeiro = filmes.filtrar_catalogo(ordem="Combina comigo", esconder_assistidos=True)[0]
        self.assertIn("Animação", primeiro["genero"])

    def test_listas_dos_menus(self):
        """Os menus mostram os gêneros com acento e as décadas do catálogo."""
        self.assertIn("Ficção científica", filmes.generos_do_catalogo())
        self.assertEqual(filmes.decadas_do_catalogo()[0], "Anos 2020")


# =========================================================
# 17. SÉRIES NO MESMO CATÁLOGO
# =========================================================
@apenas_modo_rapido  # usa os filmes e séries do catálogo de teste
class TestSeries(TesteCineAI):

    def serie(self, nome):
        for item in filmes.filmes:
            if item["nome"] == nome and filmes.eh_serie(item):
                return item
        self.fail(f'A série "{nome}" não está no catálogo.')

    def test_detectar_tipo(self):
        """'série' -> serie | 'filme' -> filme | 'filme ou série' / nada -> os dois."""
        self.assertEqual(filmes.detectar_tipo("Quero uma série de comédia"), "serie")
        self.assertEqual(filmes.detectar_tipo("Quero um filme do Nolan"), "filme")
        self.assertIsNone(filmes.detectar_tipo("Pode ser filme ou série"))
        self.assertIsNone(filmes.detectar_tipo("Me recomenda algo"))

    def test_mesmo_id_nao_mistura(self):
        """Shrek (filme 808) e Dark (série 808): favoritar um não favorita o outro."""
        shrek, dark = self.filme("Shrek"), self.serie("Dark")
        self.assertNotEqual(usuario.chave_filme(shrek), usuario.chave_filme(dark))
        usuario.alternar_favorito(dark)
        self.assertTrue(usuario.eh_favorito(dark))
        self.assertFalse(usuario.eh_favorito(shrek))

    def test_serie_de_comedia(self):
        """'Uma série de comédia' traz The Office, não um filme de comédia."""
        resultado = self.pedir("Quero uma série de comédia")
        self.assertEqual(resultado["filme"]["nome"], "The Office")
        self.assertIn("é uma série de Comédia", resultado["texto"])
        self.assertIn("9 temporadas", resultado["texto"])

    def test_filme_de_comedia_nao_traz_serie(self):
        """'Um filme de comédia' nunca traz série."""
        resultado = self.pedir("Quero um filme de comédia")
        self.assertFalse(filmes.eh_serie(resultado["filme"]))

    def test_quero_uma_serie_usa_o_gosto(self):
        """'Quero uma série' (sem critério) é pedido pelo seu gosto, só entre séries."""
        self.assertTrue(filmes.eh_pedido_personalizado("Quero uma série"))
        resultado = self.pedir("Quero uma série")
        self.assertTrue(filmes.eh_serie(resultado["filme"]))
        segundo = self.pedir("Quero outro")
        self.assertTrue(filmes.eh_serie(segundo["filme"]))

    def test_serie_por_assunto(self):
        """'Série sobre professor que fabrica drogas' -> Breaking Bad."""
        resultado = self.pedir("Quero uma série sobre um professor que fabrica drogas")
        self.assertEqual(resultado["filme"]["nome"], "Breaking Bad")

    def test_serie_pelo_criador(self):
        """'Série do Vince Gilligan' acha pelo criador (campo diretor)."""
        resultado = self.pedir("Quero uma série do Vince Gilligan")
        self.assertEqual(resultado["filme"]["nome"], "Breaking Bad")
        self.assertIn("criada por Vince Gilligan", resultado["texto"])

    def test_perguntas_da_serie(self):
        """Temporadas, status, criador e duração respondem sem IA."""
        filmes.restaurar_contexto([usuario.chave_filme(self.serie("Breaking Bad"))])
        self.assertIn("5 temporadas", self.pedir("Quantas temporadas tem?")["texto"])
        self.assertIn("Sim, já acabou", self.pedir("Ela já acabou?")["texto"])
        self.assertIn("Vince Gilligan", self.pedir("Quem criou?")["texto"])
        resposta_duracao = self.pedir("Quanto tempo dura cada episódio?")
        self.assertIn("47min", resposta_duracao["texto"])
        self.assertEqual(resposta_duracao["rastro"]["chamadas_ia"], 0)

    def test_status_em_exibicao(self):
        """'Ela já acabou?' sobre série no ar: 'Ainda não acabou'."""
        filmes.restaurar_contexto([usuario.chave_filme(self.serie("Stranger Things"))])
        texto = self.pedir("Ela já acabou?")["texto"]
        self.assertIn("Ainda não acabou", texto)
        self.assertIn("desde 2016", texto)

    def test_filme_nao_tem_temporada(self):
        """'Quantas temporadas?' sobre um filme explica que é filme."""
        filmes.restaurar_contexto([usuario.chave_filme(self.filme("Interestelar"))])
        self.assertIn("é um filme", self.pedir("Quantas temporadas tem?")["texto"])

    def test_periodo_de_exibicao(self):
        """2008–2013 (acabou), 2016– (em exibição), 2014 (filme)."""
        self.assertEqual(filmes.periodo_de_exibicao(self.serie("Breaking Bad")), "2008–2013")
        self.assertEqual(filmes.periodo_de_exibicao(self.serie("Stranger Things")), "2016–")
        self.assertEqual(filmes.periodo_de_exibicao(self.filme("Interestelar")), "2014")

    def test_parecido_com_serie_traz_serie(self):
        """'Parecido com Stranger Things' traz série; 'um filme parecido com...' traz filme."""
        resultado = self.pedir("Quero algo parecido com Stranger Things")
        self.assertTrue(filmes.eh_serie(resultado["filme"]))
        filmes.reiniciar_conversa()
        resultado = self.pedir("Quero um filme parecido com Stranger Things")
        self.assertFalse(filmes.eh_serie(resultado["filme"]))

    def test_titulo_curto_com_maiuscula(self):
        """'Dark' (4 letras) só vale escrito com maiúscula no meio da frase."""
        self.assertEqual(filmes.encontrar_filme_citado("Quero algo parecido com Dark")["nome"], "Dark")
        self.assertIsNone(filmes.encontrar_filme_citado("quero um filme dark e sombrio"))
        nomes = [item["nome"] for item in filmes.encontrar_filmes_citados("Dark ou Stranger Things?")]
        self.assertEqual(nomes, ["Stranger Things"])  # "Dark" no começo da frase não conta
        nomes = [item["nome"] for item in filmes.encontrar_filmes_citados("Compare Dark e Stranger Things")]
        self.assertEqual(nomes, ["Dark", "Stranger Things"])

    def test_catalogo_filtra_tipo(self):
        """Catálogo: Todos / Filmes / Séries."""
        so_series = filmes.filtrar_catalogo(tipo="serie")
        self.assertEqual(len(so_series), 4)
        self.assertTrue(all(filmes.eh_serie(item) for item in so_series))
        self.assertEqual(len(filmes.filtrar_catalogo(tipo="filme")), 21)
        self.assertEqual(len(filmes.filtrar_catalogo()), 25)

    def test_comparar_filme_e_serie(self):
        """'Breaking Bad ou Interestelar?' mostra o tipo e as temporadas."""
        comparacao = self.pedir("Breaking Bad ou Interestelar?")["comparacao"]
        rotulos = [linha["rotulo"] for linha in comparacao["linhas"]]
        self.assertIn("Tipo", rotulos)
        self.assertIn("Temporadas", rotulos)
        duracao = next(linha for linha in comparacao["linhas"] if linha["rotulo"] == "Duração")
        self.assertIsNone(duracao["vencedor"])  # episódio × filme não se compara


# =========================================================
# 18. BUGS ENCONTRADOS NO TESTE DAS SÉRIES (03/10)
# =========================================================
@apenas_modo_rapido  # usa os filmes e séries do catálogo de teste
class TestCorrecoesSeries(TesteCineAI):

    def test_serie_sai_do_assunto(self):
        """A IA devolveu 'serie de investigação policial': o 'serie de' é removido."""
        self.assertEqual(filmes.limpar_tipo_do_assunto("serie de investigação policial"), "investigação policial")
        self.assertEqual(filmes.limpar_tipo_do_assunto("filme sobre ogros"), "ogros")
        self.assertEqual(filmes.limpar_tipo_do_assunto("viagem no tempo"), "viagem no tempo")

    def test_decada(self):
        """'anos 2000' é a década (2000–2009), não o ano 2000."""
        self.assertEqual(filmes.detectar_decada("quero uma dos anos 2000"), (2000, 2009))
        self.assertEqual(filmes.detectar_decada("um filme dos anos 90"), (1990, 1999))
        self.assertEqual(filmes.detectar_decada("da década de 80"), (1980, 1989))
        self.assertIsNone(filmes.detectar_decada("quero uma dos anos 200"))
        self.assertIsNone(filmes.detectar_ano("quero uma dos anos 2000"))
        self.assertEqual(filmes.detectar_ano("um filme de 2000"), 2000)

    def test_filmes_dos_anos_90(self):
        """'Animação dos anos 90' traz uma animação de 1990 a 1999."""
        filme = self.pedir("Quero uma animação dos anos 90")["filme"]
        self.assertTrue(1990 <= filme["ano"] <= 1999)

    def test_serie_continua_serie(self):
        """Depois de 'uma série de comédia', 'quero uma dos anos 2000' ainda é série."""
        self.pedir("Quero uma série de comédia")
        resultado = self.pedir("quero uma dos anos 2000")
        self.assertTrue(filmes.eh_serie(resultado["filme"]), resultado["filme"]["nome"])
        self.assertTrue(2000 <= resultado["filme"]["ano"] <= 2009)

    def test_filme_ou_serie_libera_os_dois(self):
        """'Filme ou série' depois de séries volta a valer para os dois."""
        self.pedir("Quero uma série de comédia")
        self.pedir("Pode ser filme ou série de drama")
        self.assertIsNone(filmes.tipo_da_conversa)

    def test_tipo_herdado_sem_resultado_tenta_os_dois(self):
        """Depois de séries, 'algo com DiCaprio' (que não tem série) ainda acha um filme."""
        self.pedir("Quero uma série de comédia")
        resultado = self.pedir("quero algo com o DiCaprio")
        self.assertEqual(resultado["tipo"], "recomendacao")
        self.assertIn("Leonardo DiCaprio", resultado["filme"]["elenco"])

    def test_nome_com_erro_de_digitacao(self):
        """'Matthew Mcconaghey' (errado) acha Matthew McConaughey, não um sobrenome solto."""
        self.assertEqual(filmes.detectar_ator("um filme com o Matthew Mcconaghey"), "Matthew McConaughey")
        self.assertEqual(filmes.detectar_ator("com Leonardo Di Caprio"), "Leonardo DiCaprio")
        self.assertEqual(self.recomendado("Quero um filme com o Matthew Mcconaghey"), "Interestelar")

    def test_titulo_exato_tem_prioridade(self):
        """'Breaking Bad' e 'quero a serie breaking bad' mostram a própria série."""
        resultado = self.pedir("breaking bad")
        self.assertEqual(resultado["filme"]["nome"], "Breaking Bad")
        self.assertIn("Achei pelo título", resultado["texto"])
        filmes.reiniciar_conversa()
        self.assertEqual(self.recomendado("quero a serie breaking bad"), "Breaking Bad")

    def test_titulo_e_depois_outro(self):
        """Depois do título, 'quero outro' traz um parecido (série com série)."""
        self.pedir("Stranger Things")
        segundo = self.pedir("quero outro")["filme"]
        self.assertTrue(filmes.eh_serie(segundo))
        self.assertNotEqual(segundo["nome"], "Stranger Things")

    def test_titulo_do_filme_atual(self):
        """Bug do teste: 'o mentalista' logo depois de recomendar O Mentalista virava busca."""
        primeiro = self.pedir("Quero uma série com a Millie Bobby Brwn")["filme"]  # nome errado de propósito
        self.assertEqual(primeiro["nome"], "Stranger Things")
        resultado = self.pedir("stranger things")
        self.assertEqual(resultado["filme"]["nome"], "Stranger Things")
        self.assertIn("Ainda não acabou", self.pedir("Ela já acabou?")["texto"])

    def test_pergunta_sim_ou_nao_do_elenco(self):
        """'A Winona Ryder está no elenco?' responde Sim; 'O Tom Hanks está?' responde Não."""
        self.pedir("Stranger Things")
        self.assertIn("Sim! Winona Ryder está no elenco", self.pedir("A Winona Ryder está no elenco?")["texto"])
        self.assertIn("Sim! Winona Ryder", self.pedir("A Ryder está no elenco?")["texto"])
        self.assertIn("Não, Tom Hanks não está no elenco", self.pedir("O Tom Hanks está no elenco?")["texto"])
        self.assertIn("Elenco:", self.pedir("Qual o elenco?")["texto"])

    def test_pergunta_sim_ou_nao_do_diretor(self):
        """'O Nolan dirigiu esse?' responde Sim ou Não."""
        filmes.restaurar_contexto([usuario.chave_filme(self.filme("Interestelar"))])
        self.assertIn("Sim! Christopher Nolan dirigiu Interestelar", self.pedir("O Nolan dirigiu esse?")["texto"])
        self.assertIn("Não, James Cameron não dirigiu", self.pedir("O James Cameron dirigiu esse?")["texto"])

    def test_titulo_com_mais_assunto_nao_e_direto(self):
        """'Um filme parecido com Shrek' continua sendo pedido relativo."""
        self.assertIsNone(filmes.titulo_pedido_diretamente("Quero um filme parecido com Shrek"))
        self.assertIsNotNone(filmes.titulo_pedido_diretamente("Me fala de Interestelar"))


# =========================================================
# 19. CATÁLOGO REAL (só no modo --completo)
# =========================================================
@apenas_modo_completo
class TestCatalogoReal(TesteCineAI):

    def test_catalogo_carregado(self):
        """O catálogo tem filmes, e todos têm id, sinopse e gênero."""
        self.assertGreater(len(filmes.filmes), 100)
        for filme in filmes.filmes:
            self.assertTrue(filme.get("sinopse") and filme.get("genero"), filme.get("nome"))

    def test_avaliacoes_importadas(self):
        """Dos títulos JÁ consultados na OMDb, a maioria tem alguma nota (IMDb ou Rotten)."""
        consultados = [filme for filme in filmes.filmes if filme.get("omdb_consultado")]
        if len(consultados) < 50:
            self.skipTest("poucos títulos consultados na OMDb ainda (rode o importar_avaliacoes.py)")
        com_nota = sum(
            1 for filme in consultados
            if filmes.nota_da_critica(filme) or filme.get("nota_imdb")
        )
        self.assertGreater(com_nota / len(consultados), 0.8)

    def test_ids_unicos(self):
        """Nenhum filme (ou série) aparece duas vezes."""
        chaves = [usuario.chave_filme(filme) for filme in filmes.filmes if filme.get("id") is not None]
        self.assertEqual(len(chaves), len(set(chaves)))


# =========================================================
# EXECUÇÃO
# =========================================================
if __name__ == "__main__":
    print(f"Modo: {'COMPLETO' if MODO_COMPLETO else 'RÁPIDO'}  |  {len(filmes.filmes)} filmes\n")

    programa = unittest.main(verbosity=2, exit=False)
    resultado = programa.result

    shutil.rmtree(PASTA_TEMPORARIA, ignore_errors=True)

    total = resultado.testsRun
    falhas = len(resultado.failures) + len(resultado.errors)
    pulados = len(resultado.skipped)

    print("\n" + "=" * 60)
    if falhas == 0:
        print(f"✅ Tudo certo! {total - pulados} testes passaram ({pulados} pulados).")
    else:
        print(f"❌ {falhas} de {total} testes falharam. Veja os detalhes acima.")
    print("=" * 60)

    sys.exit(1 if falhas else 0)
