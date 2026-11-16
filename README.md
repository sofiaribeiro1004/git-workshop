# Git Workshop

Este projecto contém uma ferramenta de linha de comandos para consultar e
organizar exercícios da API pública [wger](https://wger.de/api/v2/).

## Módulos do projecto

### `fitcli.py`

É o único módulo Python do projecto. Define os comandos da aplicação, obtém os
dados da API wger, filtra e classifica exercícios e pode exportar planos de
treino para um ficheiro CSV.

Os resultados apresentados abaixo são exemplos: os exercícios disponíveis
podem mudar consoante os dados publicados na API.

#### Bibliotecas utilizadas

- `json` formata os resultados como JSON.
- `re` procura padrões de texto nas descrições.
- `csv` escreve os planos de treino em formato CSV.
- `html` converte entidades HTML para texto legível.
- `Counter`, de `collections`, agrega as contagens de equipamento.
- `Optional`, de `typing`, indica que a opção de exportação CSV pode não ser
  fornecida.
- `requests` faz os pedidos HTTP à API.
- `typer` define e executa os comandos da linha de comandos.

#### Configuração e acesso à API

- `app` cria a aplicação de linha de comandos com Typer.
- `API_URL` identifica o endereço da API de informação de exercícios.
- `HEADERS` define o cabeçalho enviado nos pedidos HTTP.
- `get_exerciseinfo()` pede exercícios em páginas de 100 registos, ordenados
  pelo identificador em ordem decrescente. Solicita os dados em inglês
  (`language=2`) e segue todas as páginas indicadas pela API.
- Se ocorrer um erro de ligação, uma resposta JSON inválida ou uma estrutura
  inesperada, a aplicação apresenta uma mensagem de erro e termina com código
  diferente de zero.

#### Funções auxiliares de leitura

- `_get_name(exercise)` procura o nome em inglês nas traduções do exercício.
- `_get_category(exercise)` obtém o nome da categoria.
- `_get_muscles(exercise)` devolve os nomes dos músculos, preferindo o nome em
  inglês.
- `_get_equipment(exercise)` devolve os nomes do equipamento; se não houver
  equipamento identificado, devolve `No equipment`.
- `_clean_html(text)` remove etiquetas HTML e converte entidades HTML para
  texto legível.
- `_get_description(exercise)` obtém e limpa a descrição em inglês.
- `_matches_search(exercise, term)` verifica se o termo aparece na categoria
  ou nos músculos do exercício, sem distinguir maiúsculas de minúsculas.
- `_classify_effort(exercise)` classifica o exercício como `compound`,
  `isolated` ou `other`. Usa palavras-chave da descrição e o número de músculos
  associados.
- `_count_equipment(exercises)` conta menções a vários tipos de equipamento
  nas descrições e ordena os resultados da contagem mais elevada para a mais
  baixa.
- `_build_workout(exercises, groups, effort, n)` selecciona até `n` exercícios
  para cada grupo, de acordo com o tipo de esforço pedido.
- `_export_csv(plan, path)` grava o plano num CSV, com uma linha por exercício,
  e devolve o número de registos gravados.

#### Padrões de equipamento

`EQUIPMENT_PATTERNS` associa cada equipamento a uma expressão regular. As
expressões permitem reconhecer algumas variações, como singular e plural ou
escritas com e sem hífen. São considerados, entre outros, halteres, barras,
polias, máquinas, peso corporal, kettlebells, bancos e bandas de resistência.

#### Comandos disponíveis

##### `list-categories`

Obtém as categorias da API e apresenta os nomes que tenham sido recebidos.

```console
python fitcli.py list-categories
['Abs', 'Arms', 'Back', 'Chest', 'Legs', 'Shoulders']
```

##### `top`

Apresenta os exercícios mais recentes, limitados ao número indicado. Cada
resultado contém o nome, a categoria e o equipamento.

```console
python fitcli.py top 1
[
    {
        "name": "Example exercise",
        "category": "Chest",
        "equipment": ["Dumbbell"]
    }
]
```

##### `search`

Procura exercícios cujo nome da categoria ou músculos inclua o termo indicado.
A pesquisa não distingue maiúsculas de minúsculas. O argumento `limit` limita
o número de resultados.

```console
python fitcli.py search chest 1
[
    {
        "name": "Example exercise",
        "category": "Chest",
        "muscles": ["Pectoralis major"],
        "equipment": ["Dumbbell"]
    }
]
```

Se forem encontrados menos exercícios do que o limite pedido, é também
apresentada uma mensagem com o número de resultados.

##### `type`

Determina o tipo de esforço do exercício com o identificador indicado. A
classificação é `compound` quando a descrição indica um exercício composto ou
estão associados pelo menos três músculos; é `isolated` quando a descrição
indica isolamento ou está associado um músculo; nos restantes casos é `other`.

```console
python fitcli.py type 123
Tipo de ejercicio determinado para ID 123: isolated. Categoría: arms, Músculos involucrados: 1
```

Se o identificador não existir, apresenta uma mensagem de erro e indica que o
exercício não foi encontrado.

##### `equipment`

Conta as menções a equipamento nas descrições dos exercícios de uma categoria.
O nome da categoria é comparado sem distinção entre maiúsculas e minúsculas.

```console
python fitcli.py equipment chest
[
    {"dumbbell": 12},
    {"barbell": 8},
    {"bench": 5}
]
```

Se a categoria não existir, apresenta as categorias disponíveis e termina com
um erro.

##### `workout`

Cria um plano de treino com grupos separados por vírgulas, um tipo de esforço
(`compound`, `isolated` ou `any`) e o número máximo de exercícios por grupo.
Grupos vazios e repetidos são ignorados. Exercícios sem nome em inglês não são
incluídos.

```console
python fitcli.py workout biceps,back any 1
{
    "biceps": [
        {
            "name": "Example curl",
            "type": "isolated",
            "category": "Arms",
            "muscles": ["Biceps brachii"],
            "equipment": ["Dumbbell"]
        }
    ],
    "back": []
}
```

É apresentado um aviso para cada grupo sem exercícios correspondentes. Com a
opção `--csv`, o plano é exportado em vez de apresentado como JSON:

```console
python fitcli.py workout biceps,back any 2 --csv plano.csv
Ficheiro exportado: plano.csv (3 registos)
```

O CSV inclui as colunas `group`, `name`, `type`, `category`, `muscles` e
`equipment`. Os valores de músculos e equipamento são escritos na mesma célula,
separados por ponto e vírgula.

#### Execução do programa

No final do módulo, `app()` inicia a aplicação Typer quando `fitcli.py` é
executado directamente. Por exemplo:

```console
python fitcli.py --help
```
