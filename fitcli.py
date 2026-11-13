"""Comandos CLI para consultar ejercicios de la API de wger."""

import json
import re
import csv
import html
from collections import Counter
from typing import Optional

import requests
import typer

app = typer.Typer(help="CLI para consultar la API de ejercicios wger")
API_URL = "https://wger.de/api/v2/exerciseinfo/"
HEADERS = {"User-Agent": "ALPCD-TP1-GrupoPruebas/1.0"}


def get_exerciseinfo() -> list[dict[str, object]]:
    """Obtiene todos los ejercicios de la API, siguiendo su paginación."""
    exercises: list[dict[str, object]] = []
    next_url: str | None = API_URL
    parameters: dict[str, str | int] | None = {
        "limit": 100,
        "ordering": "-id",
        "language": 2,
    }

    while next_url is not None:
        try:
            response = requests.get(
                next_url, params=parameters, headers=HEADERS
            )
            response.raise_for_status()
            payload = response.json()
        except requests.exceptions.RequestException as error:
            typer.echo(f"Error de conexión con la API de wger: {error}", err=True)
            raise typer.Exit(code=1) from error
        except ValueError as error:
            typer.echo(
                "La API de wger devolvió una respuesta JSON no válida.", err=True
            )
            raise typer.Exit(code=1) from error

        if not isinstance(payload, dict) or not isinstance(
            payload.get("results"), list
        ):
            typer.echo("La API de wger devolvió una estructura inesperada.", err=True)
            raise typer.Exit(code=1)

        page_next = payload.get("next")
        if not isinstance(page_next, (str, type(None))):
            typer.echo("La API de wger devolvió una paginación no válida.", err=True)
            raise typer.Exit(code=1)

        exercises.extend(
            exercise
            for exercise in payload["results"]
            if isinstance(exercise, dict)
        )
        next_url = page_next
        parameters = None

    return exercises

@app.command(name="list-categories")
def _get_list_of_all_categories() -> list[str]:
    """Obtiene la lista de todas las categorías de ejercicios disponibles."""
    try:
        response = requests.get("https://wger.de/api/v2/exercisecategory/", headers=HEADERS)
        response.raise_for_status()
        payload = response.json()
    except requests.exceptions.RequestException as error:
        typer.echo(f"Error de conexión con la API de wger: {error}", err=True)
        raise typer.Exit(code=1) from error
    except ValueError as error:
        typer.echo("La API de wger devolvió una respuesta JSON no válida.", err=True)
        raise typer.Exit(code=1) from error

    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        typer.echo("La API de wger devolvió una estructura inesperada.", err=True)
        raise typer.Exit(code=1)

    categories: list[str] = []
    for category in payload["results"]:
        if not isinstance(category, dict):
            continue
        name = category.get("name")
        if isinstance(name, str) and name.strip():
            categories.append(name)
    return print(categories)


def _get_name(exercise: dict[str, object]) -> str:
    """Obtiene el nombre en inglés y usa el nombre raíz como alternativa."""
    translations = exercise.get("translations")
    if isinstance(translations, list):
        for translation in translations:
            if not isinstance(translation, dict):
                continue
            translated_description = translation.get("name")
            if (
                translation.get("language") == 2
                and isinstance(translated_description, str)
                and translated_description.strip()
            ):
                return translated_description
    return "Unknown"


def _get_category(exercise: dict[str, object]) -> str:
    """Extrae el nombre de categoría, tolerando valores ausentes o inválidos."""
    category = exercise.get("category")
    if isinstance(category, dict):
        name = category.get("name")
        if isinstance(name, str) and name.strip():
            return name
    return "Unknown"


def _get_muscles(exercise: dict[str, object]) -> list[str]:
    """Extrae los nombres ingleses de los músculos disponibles."""
    muscles = exercise.get("muscles")
    if not isinstance(muscles, list):
        return []

    names: list[str] = []
    for muscle in muscles:
        if not isinstance(muscle, dict):
            continue
        name = muscle.get("name_en") or muscle.get("name")
        if isinstance(name, str) and name.strip():
            names.append(name)
    return names


def _get_equipment(exercise: dict[str, object]) -> list[str]:
    """Extrae los nombres del equipo o indica que no se requiere."""
    equipment = exercise.get("equipment")
    if not isinstance(equipment, list):
        return ["No equipment"]

    names: list[str] = []
    for item in equipment:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if isinstance(name, str) and name.strip():
            names.append(name)
    return names or ["No equipment"]

# A)

@app.command()
def top(n: int = typer.Argument(..., help="Número de ejercicios recientes")) -> None:
    """Lista directamente desde la API los N ejercicios más recientes."""
    final_results: list[dict[str, object]] = []
    for exercise in get_exerciseinfo()[:n]:
        final_results.append(
            {
                "name": _get_name(exercise),
                "category": _get_category(exercise),
                "equipment": _get_equipment(exercise),
            }
        )

    typer.echo(json.dumps(final_results, indent=4, ensure_ascii=False))

# B)

@app.command()
def search(search: str, limit: int) -> None:
    """Busca ejercicios por categoría o músculo en la API completa."""
    search_lower = search.casefold()
    final_results: list[dict[str, object]] = []
    for exercise in get_exerciseinfo():
        if len(final_results) >= limit:
            break

        category = _get_category(exercise)
        muscles = _get_muscles(exercise)
        searchable_values = [category, *muscles]

        if any(search_lower in value.casefold() for value in searchable_values):
            final_results.append(
                {
                    "name": _get_name(exercise),
                    "category": category,
                    "muscles": muscles,
                    "equipment": _get_equipment(exercise),
                }
            )
    if len(final_results) < limit:
        typer.echo(
            f"Se encontraron {len(final_results)} resultados para la búsqueda '{search}'."
        )
        
    typer.echo(json.dumps(final_results, indent=4, ensure_ascii=False))


# C)

@app.command(name="type")
def _get_type_exercise_by_id(exercise_id: int) -> str:
    """Obtiene el tipo de ejercicio por su ID, devolviendo 'Unknown' si no se encuentra."""
    exercise = next(
        (
            item
            for item in get_exerciseinfo()
            if item.get("id") == exercise_id
        ),
        None,
    )
    if exercise is None:
        typer.echo(f"No se encontró un ejercicio con ID {exercise_id}.", err=True)
        return "Unknown"

    # Extrae los datos necesarios para deducir el tipo.
    category = _get_category(exercise).casefold()
    muscles = _get_muscles(exercise)
    description = ""
    translations = exercise.get("translations")
    if isinstance(translations, list):
        for translation in translations:
            if not isinstance(translation, dict):
                continue
            translated_description = translation.get("description_source")
            if (
                translation.get("language") == 2
                and isinstance(translated_description, str)
                and translated_description.strip()
            ):
                description = translated_description
                break

    # Comprueba si es compuesto según la descripción o los músculos implicados.
    if re.search(r"\b(compound|multi-joint)\b", description) or len(muscles) >= 3:
        effort_type = "compound"
    # Comprueba si es aislado según la descripción o el único músculo implicado.
    elif re.search(r"\b(isolated|isolation|single-joint)\b", description) or len(muscles) == 1:
        effort_type = "isolated"
    else:
        effort_type = "other"

    typer.echo(
        f"Tipo de ejercicio determinado para ID {exercise_id}: {effort_type}. "
        f"Categoría: {category}, Músculos involucrados: {len(muscles)}"
    )
    return effort_type

def _clean_html(text: str) -> str:
    """Remove as tags HTML e entidades (&amp;, &nbsp;...) de uma descrição."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()
 
 
def _get_description(exercise: dict[str, object]) -> str:
    """Devolve a descrição em inglês do exercício, já sem HTML."""
    translations = exercise.get("translations")
    if isinstance(translations, list):
        for translation in translations:
            if not isinstance(translation, dict) or translation.get("language") != 2:
                continue
            for key in ("description_source", "description"):
                text = translation.get(key)
                if isinstance(text, str) and text.strip():
                    return _clean_html(text)
    return ""
 
 
def _matches_search(exercise: dict[str, object], term: str) -> bool:
    """Mesmo critério da alínea B): o termo aparece na categoria ou num músculo."""
    term = term.casefold()
    searchable_values = [_get_category(exercise), *_get_muscles(exercise)]
    return any(term in value.casefold() for value in searchable_values)
 
 
def _classify_effort(exercise: dict[str, object]) -> str:
    """Mesmas regras da alínea C), numa função reutilizável."""
    muscles = _get_muscles(exercise)
    description = _get_description(exercise)
    if re.search(r"\b(compound|multi-joint)\b", description) or len(muscles) >= 3:
        return "compound"
    if re.search(r"\b(isolated|isolation|single-joint)\b", description) or len(muscles) == 1:
        return "isolated"
    return "other"
 
 
# D)
 
# Uma regex por equipamento: apanha singular/plural e variantes de escrita.
EQUIPMENT_PATTERNS = {
    "barbell": re.compile(r"\bbarbells?\b", re.IGNORECASE),
    "dumbbell": re.compile(r"\bdumb[- ]?bells?\b", re.IGNORECASE),
    "cable": re.compile(r"\b(?:cables?|pulleys?)\b", re.IGNORECASE),
    "machine": re.compile(r"\bmachines?\b", re.IGNORECASE),
    "bodyweight": re.compile(r"\b(?:body[- ]?weight|own weight)\b", re.IGNORECASE),
    "kettlebell": re.compile(r"\bkettle[- ]?bells?\b", re.IGNORECASE),
    "bench": re.compile(r"\bbench(?:es)?\b", re.IGNORECASE),
    "resistance band": re.compile(r"\b(?:resistance )?bands?\b", re.IGNORECASE),
    "ez bar": re.compile(r"\bez[- ]?(?:curl[- ]?)?bars?\b", re.IGNORECASE),
    "pull-up bar": re.compile(r"\b(?:pull|chin)[- ]?up bars?\b", re.IGNORECASE),
}
 
 
def _count_equipment(exercises: list[dict[str, object]]) -> list[dict[str, int]]:
    """Conta as menções a cada equipamento nas descrições dos exercícios."""
    counter = Counter()
    for exercise in exercises:
        description = _get_description(exercise)
        for equipment_name, pattern in EQUIPMENT_PATTERNS.items():
            occurrences = len(pattern.findall(description))
            if occurrences:
                counter[equipment_name] += occurrences
    # most_common() devolve por ordem decrescente de ocorrências
    return [{name: count} for name, count in counter.most_common()]
 
 
@app.command()
def equipment(
    category: str = typer.Argument(..., help="Nome da categoria, ex: chest"),
) -> None:
    """Conta menções a equipamento nas descrições dos exercícios de uma categoria."""
    category = category.strip()
    all_exercises = get_exerciseinfo()
    selected = [
        exercise
        for exercise in all_exercises
        if _get_category(exercise).casefold() == category.casefold()
    ]
 
    if not selected:
        available = sorted({_get_category(e) for e in all_exercises} - {"Unknown"})
        typer.echo(
            f"Categoria '{category}' não encontrada. Disponíveis: {', '.join(available)}",
            err=True,
        )
        raise typer.Exit(code=1)
 
    typer.echo(json.dumps(_count_equipment(selected), indent=4, ensure_ascii=False))
 
 
# E)
 
def _build_workout(
    exercises: list[dict[str, object]], groups: list[str], effort: str, n: int
) -> dict[str, list[dict[str, object]]]:
    """Para cada músculo/categoria escolhe até N exercícios do tipo pedido."""
    plan: dict[str, list[dict[str, object]]] = {}
    for group in groups:
        selected: list[dict[str, object]] = []
        for exercise in exercises:
            if len(selected) >= n:
                break
            if not _matches_search(exercise, group):          # alínea B)
                continue
            name = _get_name(exercise)
            if name == "Unknown":                              # sem nome em inglês
                continue
            effort_type = _classify_effort(exercise)          # alínea C)
            if effort != "any" and effort_type != effort:
                continue
            selected.append(
                {
                    "name": name,
                    "type": effort_type,
                    "category": _get_category(exercise),
                    "muscles": _get_muscles(exercise),
                    "equipment": _get_equipment(exercise),
                }
            )
        if not selected:
            typer.echo(f"Aviso: nenhum exercício encontrado para '{group}'.", err=True)
        plan[group] = selected
    return plan
 
 
def _export_csv(plan: dict[str, list[dict[str, object]]], path: str) -> int:
    """Escreve o plano num CSV (uma linha por exercício) e devolve o nº de registos."""
    fields = ["group", "name", "type", "category", "muscles", "equipment"]
    records = 0
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for group, exercises in plan.items():
            for exercise in exercises:
                writer.writerow(
                    {
                        **exercise,
                        "group": group,
                        # uma célula de CSV não guarda listas, por isso juntamos
                        "muscles": "; ".join(exercise["muscles"]),
                        "equipment": "; ".join(exercise["equipment"]),
                    }
                )
                records += 1
    return records
 
 
@app.command()
def workout(
    groups: str = typer.Argument(..., help="Músculos/categorias separados por vírgula, ex: biceps,back"),
    effort: str = typer.Argument(..., help="compound, isolated ou any"),
    n: int = typer.Argument(..., min=1, help="Máximo de exercícios por músculo/categoria"),
    csv_file: Optional[str] = typer.Option(None, "--csv", help="Exporta o plano para CSV"),
) -> None:
    """Gera um plano de treino personalizado."""
    effort = effort.strip().casefold()
    if effort not in ("compound", "isolated", "any"):
        typer.echo("O tipo de esforço tem de ser: compound, isolated ou any.", err=True)
        raise typer.Exit(code=1)
 
    group_list: list[str] = []
    for g in groups.split(","):
        g = g.strip().casefold()
        if g and g not in group_list:      # ignora vazios e repetidos
            group_list.append(g)
    if not group_list:
        typer.echo("Indica pelo menos um músculo ou categoria.", err=True)
        raise typer.Exit(code=1)
 
    # Os dados são pedidos à API uma única vez e usados para todos os grupos.
    plan = _build_workout(get_exerciseinfo(), group_list, effort, n)
 
    if csv_file:
        try:
            records = _export_csv(plan, csv_file)
        except OSError as error:
            typer.echo(f"Não foi possível escrever '{csv_file}': {error}", err=True)
            raise typer.Exit(code=1) from error
        typer.echo(f"Ficheiro exportado: {csv_file} ({records} registos)")
    else:
        typer.echo(json.dumps(plan, indent=4, ensure_ascii=False))

 
 
if __name__ == "__main__":
    app()