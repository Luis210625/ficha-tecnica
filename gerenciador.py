"""
gerenciador.py
===============
Classe central do sistema: GerenciadorFichas.

Responsável por:
    - Manter a lista de fichas técnicas em memória
    - Persistir/carregar os dados em JSON (pathlib + json)
    - CRUD completo (adicionar, editar, excluir, listar)
    - Busca por nome ou categoria
    - Controle de estoque básico (quantidade usada x estoque atual)
    - Relatório de custo médio por categoria
"""

import json
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime

from models import FichaTecnica, Ingrediente


class GerenciadorFichas:
    """Gerencia o ciclo de vida das fichas técnicas e o estoque de ingredientes."""

    def __init__(self, arquivo_dados: str = "dados/fichas.json"):
        self.arquivo_dados = Path(arquivo_dados)
        self.fichas: List[FichaTecnica] = []
        self.estoque: Dict[str, dict] = {}  # nome_normalizado -> {"nome", "quantidade", "unidade"}
        self.config: Dict[str, float] = {
            "margem_padrao": 65.0,
            "custo_mao_de_obra_hora_padrao": 0.0,
        }
        self._proximo_id: int = 1
        self.carregar_dados()

    # ------------------------------------------------------------------ #
    # Persistência (JSON)
    # ------------------------------------------------------------------ #

    def carregar_dados(self) -> None:
        """Carrega fichas e estoque do arquivo JSON, se existir."""
        if not self.arquivo_dados.exists():
            self.fichas = []
            self.estoque = {}
            self._proximo_id = 1
            return

        try:
            with open(self.arquivo_dados, "r", encoding="utf-8") as f:
                conteudo = json.load(f)
        except (json.JSONDecodeError, OSError) as erro:
            raise RuntimeError(
                f"Não foi possível ler o arquivo de dados '{self.arquivo_dados}': {erro}"
            )

        fichas_dict = conteudo.get("fichas", [])
        self.fichas = [FichaTecnica.from_dict(f) for f in fichas_dict]
        self.estoque = conteudo.get("estoque", {})
        self.config.update(conteudo.get("config", {}))
        self._proximo_id = conteudo.get("proximo_id", (max([f.id for f in self.fichas], default=0) + 1))

    def salvar_dados(self) -> None:
        """Salva fichas e estoque no arquivo JSON (cria a pasta se necessário)."""
        self.arquivo_dados.parent.mkdir(parents=True, exist_ok=True)
        conteudo = {
            "fichas": [f.to_dict() for f in self.fichas],
            "estoque": self.estoque,
            "config": self.config,
            "proximo_id": self._proximo_id,
            "atualizado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
        }
        try:
            with open(self.arquivo_dados, "w", encoding="utf-8") as f:
                json.dump(conteudo, f, ensure_ascii=False, indent=2)
        except OSError as erro:
            raise RuntimeError(f"Não foi possível salvar os dados: {erro}")

    # ------------------------------------------------------------------ #
    # Configurações padrão (usadas para preencher novas fichas)
    # ------------------------------------------------------------------ #

    def atualizar_config(self, margem_padrao: Optional[float] = None,
                          custo_mao_de_obra_hora_padrao: Optional[float] = None) -> None:
        """Atualiza as configurações padrão do sistema (margem e custo de mão de obra)."""
        if margem_padrao is not None:
            if not (0 <= margem_padrao < 100):
                raise ValueError("A margem padrão deve estar entre 0 e 99.9%.")
            self.config["margem_padrao"] = margem_padrao
        if custo_mao_de_obra_hora_padrao is not None:
            if custo_mao_de_obra_hora_padrao < 0:
                raise ValueError("O custo de mão de obra por hora não pode ser negativo.")
            self.config["custo_mao_de_obra_hora_padrao"] = custo_mao_de_obra_hora_padrao
        self.salvar_dados()

    # ------------------------------------------------------------------ #
    # CRUD de fichas técnicas
    # ------------------------------------------------------------------ #

    def adicionar_ficha(
        self,
        nome: str,
        categoria: str,
        porcao_rendimento: str,
        ingredientes: List[Ingrediente],
        modo_preparo: List[str],
        tempo_preparo_min: int,
        alergenicos: Optional[List[str]] = None,
        observacoes: str = "",
        margem_lucro_desejada: float = 65.0,
        custo_mao_de_obra_hora: float = 0.0,
        preco_venda_manual: Optional[float] = None,
    ) -> FichaTecnica:
        """Cria e adiciona uma nova ficha técnica, retornando a ficha criada."""
        ficha = FichaTecnica(
            id=self._proximo_id,
            nome=nome,
            categoria=categoria,
            porcao_rendimento=porcao_rendimento,
            ingredientes=ingredientes,
            modo_preparo=modo_preparo,
            tempo_preparo_min=tempo_preparo_min,
            alergenicos=alergenicos or [],
            observacoes=observacoes,
            margem_lucro_desejada=margem_lucro_desejada,
            custo_mao_de_obra_hora=custo_mao_de_obra_hora,
            preco_venda_manual=preco_venda_manual,
        )
        self.fichas.append(ficha)
        self._proximo_id += 1
        self.salvar_dados()
        return ficha

    def obter_ficha(self, id_ficha: int) -> Optional[FichaTecnica]:
        """Retorna a ficha com o ID informado, ou None se não existir."""
        return next((f for f in self.fichas if f.id == id_ficha), None)

    def editar_ficha(self, id_ficha: int, **campos) -> FichaTecnica:
        """
        Edita campos de uma ficha existente.
        `campos` aceita qualquer atributo válido de FichaTecnica
        (ex.: nome="Nova Pizza", tempo_preparo_min=20).
        """
        ficha = self.obter_ficha(id_ficha)
        if ficha is None:
            raise ValueError(f"Ficha técnica com ID {id_ficha} não encontrada.")

        for chave, valor in campos.items():
            if not hasattr(ficha, chave):
                raise ValueError(f"Campo inválido para edição: '{chave}'.")
            setattr(ficha, chave, valor)

        ficha.data_atualizacao = datetime.now().strftime("%d/%m/%Y %H:%M")
        ficha.__post_init__()  # revalida os dados após a edição
        self.salvar_dados()
        return ficha

    def excluir_ficha(self, id_ficha: int) -> bool:
        """Remove uma ficha técnica pelo ID. Retorna True se removida."""
        ficha = self.obter_ficha(id_ficha)
        if ficha is None:
            return False
        self.fichas.remove(ficha)
        self.salvar_dados()
        return True

    def listar_fichas(self, categoria: Optional[str] = None) -> List[FichaTecnica]:
        """Lista todas as fichas, opcionalmente filtradas por categoria exata."""
        if categoria:
            return [f for f in self.fichas if f.categoria.lower() == categoria.lower()]
        return list(self.fichas)

    def buscar(self, termo: str) -> List[FichaTecnica]:
        """Busca fichas cujo nome OU categoria contenham o termo (case-insensitive)."""
        termo = termo.strip().lower()
        if not termo:
            return []
        return [
            f for f in self.fichas
            if termo in f.nome.lower() or termo in f.categoria.lower()
        ]

    # ------------------------------------------------------------------ #
    # Relatórios
    # ------------------------------------------------------------------ #

    def relatorio_custo_medio_por_categoria(self) -> Dict[str, dict]:
        """
        Retorna, para cada categoria presente, um resumo com:
        quantidade de fichas, custo médio, preço médio e food cost médio.
        """
        categorias: Dict[str, List[FichaTecnica]] = {}
        for f in self.fichas:
            categorias.setdefault(f.categoria, []).append(f)

        relatorio = {}
        for categoria, lista in categorias.items():
            qtd = len(lista)
            custo_medio = round(sum(f.custo_total_producao for f in lista) / qtd, 2)
            preco_medio = round(sum(f.preco_venda_final for f in lista) / qtd, 2)
            food_cost_medio = round(sum(f.food_cost_percentual for f in lista) / qtd, 2)
            margem_media = round(sum(f.margem_lucro_percentual for f in lista) / qtd, 2)
            relatorio[categoria] = {
                "quantidade_fichas": qtd,
                "custo_medio": custo_medio,
                "preco_medio": preco_medio,
                "food_cost_medio": food_cost_medio,
                "margem_media": margem_media,
            }
        return relatorio

    # ------------------------------------------------------------------ #
    # Controle de estoque básico
    # ------------------------------------------------------------------ #
    # O estoque é global (por ingrediente), compartilhado entre todas as
    # fichas que usam aquele ingrediente — assim como funciona na prática
    # em uma cozinha real.

    @staticmethod
    def _normalizar(nome: str) -> str:
        return nome.strip().lower()

    def adicionar_estoque(self, nome_ingrediente: str, quantidade: float, unidade: str) -> None:
        """Adiciona (repõe) quantidade de um ingrediente no estoque."""
        if quantidade <= 0:
            raise ValueError("A quantidade a adicionar deve ser maior que zero.")
        chave = self._normalizar(nome_ingrediente)
        if chave in self.estoque:
            if self.estoque[chave]["unidade"] != unidade:
                raise ValueError(
                    f"O ingrediente '{nome_ingrediente}' já está em estoque na unidade "
                    f"'{self.estoque[chave]['unidade']}'. Use a mesma unidade."
                )
            self.estoque[chave]["quantidade"] += quantidade
        else:
            self.estoque[chave] = {
                "nome": nome_ingrediente.strip(),
                "quantidade": quantidade,
                "unidade": unidade,
            }
        self.salvar_dados()

    def listar_estoque(self) -> List[dict]:
        """Retorna a lista de itens em estoque, ordenada por nome."""
        return sorted(self.estoque.values(), key=lambda i: i["nome"].lower())

    def verificar_estoque_ficha(self, id_ficha: int) -> dict:
        """
        Verifica, para a ficha informada, quantas porções podem ser produzidas
        com o estoque atual, e quais ingredientes faltam (se houver).
        """
        ficha = self.obter_ficha(id_ficha)
        if ficha is None:
            raise ValueError(f"Ficha técnica com ID {id_ficha} não encontrada.")

        porcoes_possiveis = []
        faltando = []
        for ing in ficha.ingredientes:
            chave = self._normalizar(ing.nome)
            item_estoque = self.estoque.get(chave)
            disponivel = item_estoque["quantidade"] if item_estoque else 0.0
            if disponivel < ing.quantidade:
                faltando.append({
                    "ingrediente": ing.nome,
                    "necessario": ing.quantidade,
                    "disponivel": disponivel,
                    "unidade": ing.unidade,
                })
            porcoes_possiveis.append(disponivel // ing.quantidade if ing.quantidade > 0 else 0)

        return {
            "ficha": ficha.nome,
            "porcoes_possiveis": int(min(porcoes_possiveis)) if porcoes_possiveis else 0,
            "ingredientes_faltando": faltando,
        }

    def dar_baixa_estoque(self, id_ficha: int, porcoes: int = 1) -> dict:
        """
        Dá baixa no estoque referente à produção de N porções da ficha.
        Só efetua a baixa se houver estoque suficiente de TODOS os ingredientes;
        caso contrário, retorna a lista de itens insuficientes sem alterar nada.
        """
        if porcoes <= 0:
            raise ValueError("O número de porções deve ser maior que zero.")

        ficha = self.obter_ficha(id_ficha)
        if ficha is None:
            raise ValueError(f"Ficha técnica com ID {id_ficha} não encontrada.")

        # 1ª passada: verifica se há estoque suficiente para tudo
        insuficientes = []
        for ing in ficha.ingredientes:
            chave = self._normalizar(ing.nome)
            necessario = ing.quantidade * porcoes
            disponivel = self.estoque.get(chave, {}).get("quantidade", 0.0)
            if disponivel < necessario:
                insuficientes.append({
                    "ingrediente": ing.nome,
                    "necessario": necessario,
                    "disponivel": disponivel,
                    "unidade": ing.unidade,
                })

        if insuficientes:
            return {"sucesso": False, "ingredientes_insuficientes": insuficientes}

        # 2ª passada: efetua a baixa
        for ing in ficha.ingredientes:
            chave = self._normalizar(ing.nome)
            self.estoque[chave]["quantidade"] = round(
                self.estoque[chave]["quantidade"] - (ing.quantidade * porcoes), 3
            )

        self.salvar_dados()
        return {"sucesso": True, "ingredientes_insuficientes": []}
