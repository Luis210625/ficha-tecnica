#!/usr/bin/env python3
"""
main.py
========
Ponto de entrada do Sistema de Fichas Técnicas para Pizzarias e Restaurantes.

Execute com:
    python main.py

Para a versão web (Streamlit), execute em vez disso:
    streamlit run app_streamlit.py
"""

from cli import executar_menu

if __name__ == "__main__":
    try:
        executar_menu()
    except KeyboardInterrupt:
        print("\n\n👋 Programa encerrado pelo usuário. Até logo!")
