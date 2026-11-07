"""Comandos CLI para consultar ejercicios de la API de wger."""

import json
import re

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



if __name__ == "__main__":
    app()
