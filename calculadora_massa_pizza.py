"""
Calculadora de proporções de ingredientes para massa de pizza.

Escala a receita base conforme a quantidade de farinha desejada e ajusta
a proporção entre gelo e água em temperatura ambiente conforme a
temperatura do local onde a massa é feita: em dias mais frios que a
referência, usa-se menos gelo, pois a fermentação já vai demorar mais
por conta própria.

Pensado para ser importado depois em um app.py (Flask, CLI, etc.):

    from calculadora_massa_pizza import calcular_receita
    receita = calcular_receita(farinha_kg=10, temperatura_ambiente=15)
    dados = receita.to_dict()  # pronto pra jsonify() ou pra um template
"""

from dataclasses import dataclass, asdict
from typing import Optional

TEMPERATURA_REFERENCIA = 22.0  # °C em que a receita original foi calibrada

# Proporções por kg de farinha, derivadas da receita original (10 kg de farinha)
GELO_G_POR_KG = 100.0
FERMENTO_G_POR_KG = 1.0
SUCO_TOMATE_ML_POR_KG = 500.0
AGUA_ML_POR_KG = 40.0
SAL_G_POR_KG = 20.0


@dataclass
class ReceitaMassaPizza:
    farinha_kg: float
    gelo_g: float
    fermento_g: float
    suco_tomate_ml: float
    agua_ml: float
    sal_g: float
    diferenca_temperatura: float  # positivo = ambiente mais frio que a referência

    def to_dict(self) -> dict:
        return asdict(self)


def calcular_receita(
    farinha_kg: float = 10.0,
    temperatura_ambiente: float = TEMPERATURA_REFERENCIA,
    sensibilidade_gelo: float = 3.0,
) -> ReceitaMassaPizza:
    """
    Calcula as quantidades de ingredientes para uma massa de pizza.

    farinha_kg: quantidade de farinha desejada, em kg.
    temperatura_ambiente: temperatura do local onde a massa será feita, em °C.
    sensibilidade_gelo: quantos % do gelo-base é deslocado para a água
        (ou vice-versa) a cada grau de diferença em relação aos 22°C de
        referência. Ajuste esse valor conforme a sua experiência prática
        com a massa.
    """
    if farinha_kg < 0:
        raise ValueError("farinha_kg não pode ser negativo")

    gelo_base = farinha_kg * GELO_G_POR_KG
    agua_base = farinha_kg * AGUA_ML_POR_KG
    fermento = farinha_kg * FERMENTO_G_POR_KG
    suco_tomate = farinha_kg * SUCO_TOMATE_ML_POR_KG
    sal = farinha_kg * SAL_G_POR_KG

    total_liquido = gelo_base + agua_base
    diferenca = TEMPERATURA_REFERENCIA - temperatura_ambiente

    deslocamento = gelo_base * (sensibilidade_gelo / 100) * diferenca
    gelo_ajustado = min(max(gelo_base - deslocamento, 0.0), total_liquido)
    agua_ajustada = total_liquido - gelo_ajustado

    return ReceitaMassaPizza(
        farinha_kg=round(farinha_kg, 2),
        gelo_g=round(gelo_ajustado, 1),
        fermento_g=round(fermento, 1),
        suco_tomate_ml=round(suco_tomate, 1),
        agua_ml=round(agua_ajustada, 1),
        sal_g=round(sal, 1),
        diferenca_temperatura=round(diferenca, 1),
    )


def formatar_peso(gramas: float) -> str:
    """Formata um peso em g ou kg, o que for mais legível."""
    if gramas >= 1000:
        return f"{gramas / 1000:.2f} kg"
    return f"{gramas:.0f} g"


def formatar_volume(mililitros: float) -> str:
    """Formata um volume em ml ou L, o que for mais legível."""
    if mililitros >= 1000:
        return f"{mililitros / 1000:.2f} L"
    return f"{mililitros:.0f} ml"


def imprimir_receita(receita: ReceitaMassaPizza) -> None:
    print(f"Farinha de trigo: {receita.farinha_kg:.2f} kg")
    print(f"Gelo: {formatar_peso(receita.gelo_g)}")
    print(f"Fermento: {formatar_peso(receita.fermento_g)}")
    print(f"Suco de tomate: {formatar_volume(receita.suco_tomate_ml)}")
    print(f"Água em temperatura ambiente: {formatar_volume(receita.agua_ml)}")
    print(f"Sal: {formatar_peso(receita.sal_g)}")

    if receita.diferenca_temperatura > 0:
        print(
            f"({receita.diferenca_temperatura}°C mais frio que a referência "
            "de 22°C -> gelo reduzido, água aumentada)"
        )
    elif receita.diferenca_temperatura < 0:
        print(
            f"({abs(receita.diferenca_temperatura)}°C mais quente que a "
            "referência de 22°C -> gelo aumentado, água reduzida)"
        )
    else:
        print("(temperatura igual à referência de 22°C -> receita base, sem ajuste)")


def pedir_float(mensagem: str, valor_padrao: Optional[float] = None) -> float:
    """Pede um número ao usuário pelo terminal, com validação e valor padrão opcional."""
    while True:
        texto = input(mensagem).strip().replace(",", ".")
        if not texto and valor_padrao is not None:
            return valor_padrao
        try:
            return float(texto)
        except ValueError:
            print("Digite um número válido (ex.: 15 ou 15.5).")


if __name__ == "__main__":
    print("Calculadora de massa de pizza")
    print("-" * 30)

    farinha_kg = pedir_float("Quantos kg de farinha? (Enter para 10 kg): ", valor_padrao=10.0)
    temperatura_ambiente = pedir_float("Qual a temperatura ambiente agora, em °C? ")

    print()
    receita = calcular_receita(farinha_kg=farinha_kg, temperatura_ambiente=temperatura_ambiente)
    imprimir_receita(receita)