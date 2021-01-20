"""
Reorder the fields in all migrations such that they match the order of the 
fields in the corresponding models files.

Author: Reece Mathews
"""

import os
import os.path
import ast
import re

from typing import List, Dict, Tuple

APPS_PATH = "/var/django/ops/"

MIGRATION_MATCH = "[0-9]+_.*\\.py"  # Parse only migrations which match this regex
ONLY_INITIAL_MIGRATIONS = True  # Only edit initial migrations

# Type aliases
ModelFieldsDict = Dict[str, List[str]]  # Map models to a list of their fields

FieldLocationDict = Dict[str, int]  # Map field names to their line numbers
ModelLocationDict = Dict[str, FieldLocationDict]  # Map model names to field locations


def parse_models(models_path: str) -> ModelFieldsDict:
    """Parse the models file to get models and their fields.

    Uses the ast lib to inspect the abstract syntax trees of the models files
    without running them. Importing the file for inspection would require running all
    top-level code in it which is impossible without setting up a separate django
    project for this one case.

    """
    # Find all top-level classes
    with open(models_path) as f:
        tree = ast.parse(f.read())
    classes = [stmt for stmt in tree.body if isinstance(stmt, ast.ClassDef)]

    # Filter classes for those which inherit from models.Model
    models = []
    for cls in classes:
        for expr in cls.bases:
            if hasattr(expr, "attr") and expr.attr == "Model":
                models.append(cls)
                break

    # Map model names to the fields which are assigned within them
    model_fields: ModelFieldsDict = {}
    for model in models:
        model_fields[model.name] = ["id"]  # ID always implicitly made first param
        assignments = (item for item in model.body if type(item) is ast.Assign)
        for assignment in assignments:
            field_names = [target.id for target in assignment.targets]
            model_fields[model.name].extend(field_names)

    return model_fields


def parse_migration(migration_path: str) -> Tuple[ModelLocationDict, bool]:
    """
    Find the line numbers for each field of each model.

    :return:
        - model_locations: Location of field lines for each model in migration file
        - continue_migration: Flag denoting migration parse should halt when False
            Set False when migration is determined not to be initial and
            ONLY_INITIAL_MIGRATIONS is True
    """

    with open(migration_path) as f:
        migrations_content = f.read()
        tree = ast.parse(migrations_content)

    # Parse tree down to assignments at level of operations declaration
    classes = [item for item in tree.body if isinstance(item, ast.ClassDef)]
    migration_class = [cls for cls in classes if cls.name == "Migration"][0]
    assignments = [item for item in migration_class.body if type(item) is ast.Assign]

    # Search assignments for operations declaration
    operations_found = False
    initial_migration = False
    for stmt in assignments:
        for target in stmt.targets:
            if target.id == "operations":
                operations_found = True
                operations = stmt.value
                break
            if target.id == "initial":
                # This migration is set as an initial migration
                initial_migration = stmt.value.value
        if operations_found:
            break
    else:
        raise Exception("No operations statement found")

    if not initial_migration and ONLY_INITIAL_MIGRATIONS:
        return {}, False

    model_locations: ModelLocationDict = {}

    # Parse operations assignment to find models
    for operation in operations.elts:
        field_locations: FieldLocationDict = {}

        operation_type = operation.func.attr
        if operation_type != "CreateModel":
            continue

        # Determine model name and fields
        for parameter in operation.keywords:
            if parameter.arg == "name":
                model_name: str = parameter.value.s
            elif parameter.arg == "fields":
                field_stmts = parameter.value.elts

        # Determine field line numbers
        # TODO[reece]: Tracking individual line numbers is unnecessary if we assume each entry takes one line
        for field_stmt in field_stmts:
            field_name = field_stmt.elts[0].s
            field_lineno = field_stmt.lineno - 1  # Convert line numbers to line indices

            field_locations[field_name] = field_lineno

        model_locations[model_name] = field_locations

    return model_locations, True


def reorder(models: ModelFieldsDict, migration: ModelLocationDict, migration_path: str):
    """Reorder the given migration in-place.

    :param models: Maps model names to a list of fields in the expected order
    :param migration: Maps model names to fields and their respective current line
                      numbers
    :param migration_path: The path to the migration file
    """

    # Get contents of migration file and split into lines
    with open(migration_path) as f:
        migrations_content = f.read()

    new_content = migrations_content.split("\n")

    for model in migration:
        fields = migration[model]
        starting_line = min(fields.values())

        target_order = models[model]

        # Remove field lines from content to be sorted
        field_lines: List[Tuple[str, str]] = []
        for field in fields:
            field_line = new_content.pop(starting_line)
            field_lines.append((field, field_line))

        # Sort field lines by position of field name in target_order
        field_lines.sort(key=lambda entry: target_order.index(entry[0]))
        # Re-insert field lines into new_content in new order
        for field_ind, field_line in enumerate(field_lines):
            new_content.insert(starting_line + field_ind, field_line[1])

    # Write updated migration to file
    new_content = "\n".join(new_content)
    with open(migration_path, "w") as f:
        f.write(new_content)


def reorder_all():
    """Traverse app directories and find and reorder migrations."""

    # Traverse dirs
    for app in (
        item for item in os.listdir(APPS_PATH) if os.path.isdir(APPS_PATH + item)
    ):
        app_path = APPS_PATH + app + "/"
        app_files = os.listdir(app_path)
        # Skip directories which do not pertain to apps
        if "models.py" not in app_files:
            continue
        if "migrations" not in app_files:
            continue
        migrations_path = app_path + "migrations/"
        migrations_files = os.listdir(migrations_path)
        migrations = [f for f in migrations_files if re.match(MIGRATION_MATCH, f)]

        # Skip directories which do not have any matching migrations made
        if not migrations:
            continue

        models_path = app_path + "models.py"
        models = parse_models(models_path)  # Get the expected order of fields

        for migration_name in migrations:
            current_migration_path = migrations_path + migration_name
            # Get the current order of fields
            migration, continue_parse = parse_migration(current_migration_path)

            if not continue_parse:
                continue

            reorder(models, migration, current_migration_path)


if __name__ == "__main__":
    reorder_all()
