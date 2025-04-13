# Processador de Extratos Asaas

## Visão Geral

Ferramenta para processamento e análise de extratos financeiros da plataforma Asaas. Converte extratos PDF em formatos estruturados (CSV/Excel), categoriza transações e gera análises de fluxo de caixa.

## Para Quem Serve

- **Empresas e Empreendedores** usuários da plataforma Asaas
- **Contadores e Financeiros** que analisam extratos da Asaas
- **Analistas de Dados** que transformam PDFs em dados estruturados
- **Gestores** que precisam de insights sobre fluxo de caixa

## Funcionalidades

- Extração de dados de PDF para formato estruturado
- Categorização automática de transações
- Análise de fluxo de caixa com entradas e saídas
- Resumo diário por categoria
- Exportação para CSV e Excel
- Identificação de clientes a partir das descrições

## Bibliotecas Utilizadas

| Biblioteca | Finalidade |
|------------|------------|
| pandas | Manipulação e análise de dados |
| pdfplumber | Extração de texto de PDFs |
| re (stdlib) | Processamento de expressões regulares |
| datetime (stdlib) | Manipulação de datas |
| os (stdlib) | Operações do sistema de arquivos |

## Instalação

```bash
# Ambiente virtual
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate

# Dependências
pip install pandas pdfplumber
```

## Como Usar

```python
from processador_extrato import main

pdf_path = '/caminho/para/seu/Extrato_Asaas.pdf'
main(pdf_path)
```

## Arquivos de Saída

- **CSVs**: movimentacoes.csv, resumo_diario_categoria.csv, totais_diarios.csv
- **Excel**: Contém abas com movimentações, resumos diários, análises por categoria e metadados

## Personalização

Para adicionar novas categorias, modifique a função `get_categoria()`:

```python
def get_categoria(descricao):
    descricao = descricao.lower()
    if "nova_palavra_chave" in descricao:
        return "Nova Categoria"
    # outras categorias...
    else:
        return "Outros"
```

## Limitações

- Depende da estrutura padrão dos extratos Asaas
- A extração de nomes de clientes depende de padrões nas descrições
