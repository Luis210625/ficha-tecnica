"""
models.py
=========
Modelos de dados do Sistema de Fichas Técnicas.

Contém as classes que representam um ingrediente e uma ficha técnica
completa, incluindo todas as propriedades calculadas (custo, margem,
food cost, etc).

Convenção de custo dos ingredientes:
    O "custo_unitario" de um ingrediente é o preço por UNIDADE DE MEDIDA
    informada em "unidade" (ex.: se unidade = "g", custo_unitario é o
    preço por grama). O custo_total do ingrediente é sempre calculado
    automaticamente como quantidade * custo_unitario.

Convenção de margem de lucro:
    A "margem_lucro_desejada" é entendida como percentual sobre o PREÇO
    DE VENDA (não sobre o custo) — é a mesma lógica usada no cálculo de
    Food Cost %. Assim:
        preco_venda = custo_total_producao / (1 - margem_desejada / 100)
        food_cost_% = 100 - margem_%
    Essa é a forma mais usada no food service para precificação.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Optional


# Categorias sugeridas (o usuário pode digitar outra, se preferir)
CATEGORIAS_PADRAO = [
    "Pizza",
    "Massa",
    "Entrada",
    "Salada",
    "Sobremesa",
    "Bebida",
    "Outro",
]

# Unidades de medida aceitas para os ingredientes
UNIDADES_VALIDAS = ["g", "kg", "ml", "l", "un"]

# Alergênicos mais comuns em pizzarias/restaurantes (sugestão rápida na CLI)
ALERGENICOS_COMUNS = [
    "Glúten",
    "Lactose",
    "Ovo",
    "Amendoim",
    "Frutos do mar",
    "Soja",
    "Nozes/Castanhas",
]


@dataclass
class Ingrediente:
    """Representa um ingrediente dentro de uma ficha técnica."""

    nome: str
    quantidade: float          # quantidade usada na receita
    unidade: str                # g, kg, ml, l ou un
    custo_unitario: float       # custo por unidade de medida (ex.: R$/g)

    def __post_init__(self):
        # Validações básicas de integridade dos dados
        if not self.nome or not self.nome.strip():
            raise ValueError("O nome do ingrediente não pode ser vazio.")
        if self.quantidade <= 0:
            raise ValueError(f"Quantidade inválida para '{self.nome}': deve ser maior que zero.")
        if self.custo_unitario < 0:
            raise ValueError(f"Custo unitário inválido para '{self.nome}': não pode ser negativo.")
        if self.unidade not in UNIDADES_VALIDAS:
            raise ValueError(
                f"Unidade inválida para '{self.nome}': '{self.unidade}'. "
                f"Use uma de: {', '.join(UNIDADES_VALIDAS)}."
            )
        self.nome = self.nome.strip()

    @property
    def custo_total(self) -> float:
        """Custo total do ingrediente na receita (quantidade x custo unitário)."""
        return round(self.quantidade * self.custo_unitario, 2)

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(dados: dict) -> "Ingrediente":
        return Ingrediente(
            nome=dados["nome"],
            quantidade=float(dados["quantidade"]),
            unidade=dados["unidade"],
            custo_unitario=float(dados["custo_unitario"]),
        )


@dataclass
class FichaTecnica:
    """Representa a ficha técnica completa de um prato."""

    id: int
    nome: str
    categoria: str
    porcao_rendimento: str
    ingredientes: List[Ingrediente] = field(default_factory=list)
    modo_preparo: List[str] = field(default_factory=list)
    tempo_preparo_min: int = 0
    alergenicos: List[str] = field(default_factory=list)
    observacoes: str = ""
    margem_lucro_desejada: float = 65.0     # % sobre o preço de venda
    custo_mao_de_obra_hora: float = 0.0      # R$ por hora de mão de obra
    preco_venda_manual: Optional[float] = None  # se definido, sobrepõe o preço sugerido
    data_criacao: str = field(default_factory=lambda: datetime.now().strftime("%d/%m/%Y %H:%M"))
    data_atualizacao: str = field(default_factory=lambda: datetime.now().strftime("%d/%m/%Y %H:%M"))

    def __post_init__(self):
        if not self.nome or not self.nome.strip():
            raise ValueError("O nome do prato não pode ser vazio.")
        if self.tempo_preparo_min < 0:
            raise ValueError("O tempo de preparo não pode ser negativo.")
        if not (0 <= self.margem_lucro_desejada < 100):
            raise ValueError("A margem de lucro desejada deve estar entre 0 e 99.9%.")
        self.nome = self.nome.strip()

    # ---------- Propriedades de custo (sempre calculadas, nunca armazenadas) ----------

    @property
    def custo_ingredientes(self) -> float:
        """Soma do custo de todos os ingredientes da receita."""
        return round(sum(i.custo_total for i in self.ingredientes), 2)

    @property
    def custo_mao_de_obra(self) -> float:
        """Custo de mão de obra proporcional ao tempo de preparo."""
        return round((self.tempo_preparo_min / 60) * self.custo_mao_de_obra_hora, 2)

    @property
    def custo_total_producao(self) -> float:
        """Custo total do prato: ingredientes + mão de obra."""
        return round(self.custo_ingredientes + self.custo_mao_de_obra, 2)

    @property
    def preco_venda_sugerido(self) -> float:
        """Preço sugerido para atingir a margem de lucro desejada."""
        margem = self.margem_lucro_desejada
        if margem >= 100:
            return 0.0
        return round(self.custo_total_producao / (1 - margem / 100), 2)

    @property
    def preco_venda_final(self) -> float:
        """Preço efetivo do prato: manual, se definido, senão o sugerido."""
        if self.preco_venda_manual is not None and self.preco_venda_manual > 0:
            return round(self.preco_venda_manual, 2)
        return self.preco_venda_sugerido

    @property
    def margem_lucro_valor(self) -> float:
        """Margem de lucro em R$, considerando o preço final praticado."""
        return round(self.preco_venda_final - self.custo_total_producao, 2)

    @property
    def margem_lucro_percentual(self) -> float:
        """Margem de lucro em %, considerando o preço final praticado."""
        if self.preco_venda_final <= 0:
            return 0.0
        return round((self.margem_lucro_valor / self.preco_venda_final) * 100, 2)

    @property
    def food_cost_percentual(self) -> float:
        """Food Cost %: percentual do preço de venda consumido pelo custo do prato."""
        if self.preco_venda_final <= 0:
            return 0.0
        return round((self.custo_total_producao / self.preco_venda_final) * 100, 2)

    # ---------- Serialização ----------

    def to_dict(self) -> dict:
        dados = asdict(self)
        dados["ingredientes"] = [i.to_dict() for i in self.ingredientes]
        # Inclui os campos calculados só para leitura/consulta rápida no JSON
        dados["_calculado"] = {
            "custo_ingredientes": self.custo_ingredientes,
            "custo_mao_de_obra": self.custo_mao_de_obra,
            "custo_total_producao": self.custo_total_producao,
            "preco_venda_sugerido": self.preco_venda_sugerido,
            "preco_venda_final": self.preco_venda_final,
            "margem_lucro_valor": self.margem_lucro_valor,
            "margem_lucro_percentual": self.margem_lucro_percentual,
            "food_cost_percentual": self.food_cost_percentual,
        }
        return dados

    @staticmethod
    def from_dict(dados: dict) -> "FichaTecnica":
        ingredientes = [Ingrediente.from_dict(i) for i in dados.get("ingredientes", [])]
        return FichaTecnica(
            id=dados["id"],
            nome=dados["nome"],
            categoria=dados["categoria"],
            porcao_rendimento=dados.get("porcao_rendimento", ""),
            ingredientes=ingredientes,
            modo_preparo=dados.get("modo_preparo", []),
            tempo_preparo_min=dados.get("tempo_preparo_min", 0),
            alergenicos=dados.get("alergenicos", []),
            observacoes=dados.get("observacoes", ""),
            margem_lucro_desejada=dados.get("margem_lucro_desejada", 65.0),
            custo_mao_de_obra_hora=dados.get("custo_mao_de_obra_hora", 0.0),
            preco_venda_manual=dados.get("preco_venda_manual"),
            data_criacao=dados.get("data_criacao", datetime.now().strftime("%d/%m/%Y %H:%M")),
            data_atualizacao=dados.get("data_atualizacao", datetime.now().strftime("%d/%m/%Y %H:%M")),
        )
