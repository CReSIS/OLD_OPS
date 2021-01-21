"""
Reorder the fields in all migrations such that they match the order of the 
fields in the corresponding models files.

Author: Reece Mathews
"""

import os
import os.path
import ast
import re

from typing import List, Dict, Optional, Tuple

APPS_PATH = "conf/django/ops/"  # TODO[reece]: take from command line

MIGRATION_MATCH = "[0-9]+_.*\\.py"  # Parse only migrations which match this regex
ONLY_INITIAL_MIGRATIONS = True  # Only edit initial migrations

# Order to place models in migrations (first in list goes at top of migration, etc)
# Unlisted models are left alone
# Used to prevent frames model from being created before segments, therefore requiring
#    an AddField call which places the segment field in the wrong column -- causing
#    parse errors in pg_bulkload
MODEL_PRIORITIES = ["season_groups", "locations", "seasons", "radars", "segments"]
# Models for which any AddField calls should be removed in favor of inserting the field
#    into the corresponding expected position in CreateModel
ADD_FIELD_CONSOLIDATIONS = ["frames"]

# Type aliases
ModelFieldsDict = Dict[str, List[str]]  # Map models to a list of their fields
FieldLocationDict = Dict[str, int]  # Map field names to their line numbers


class ModelLocation:
    """Location of fields in a migration file for a model."""

    def __init__(self, model_name: str):
        self.model_name = model_name  # Name of model

        # Line index of CreateModel operation start and end (inclusive)
        self.operation_lines: Optional[Tuple[int, int]] = None
        # Line index of fields list in CreateModel func
        self.field_line_start: Optional[int] = None
        # Field names present in the CreateModel func
        self.fields = []
        # Location of AddFields funcs
        self.AddField_locations = {}


def parse_models(models_path: str) -> List[ModelLocation]:
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


def parse_migration(migration_path: str) -> Tuple[Dict[str, ModelLocation], bool]:
    """
    Find the line numbers for each field of each model.

    :return:
        - model_locations: Location of field lines for each model in migration file
        - continue_migration: Flag denoting migration parse should halt when False
            Set False when migration is determined not to be initial and
            ONLY_INITIAL_MIGRATIONS is True
    """

    with open(migration_path) as f:
        migration_content = f.read()
        tree = ast.parse(migration_content)

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

    model_locations: Dict[str, ModelLocation] = {}

    # Parse operations assignment to find models
    for operation in operations.elts:

        operation_type = operation.func.attr
        operation_lines = (operation.lineno - 1, operation.end_lineno - 1)

        for parameter in operation.keywords:
            # Handle CreateModel migrations
            if operation_type == "CreateModel":
                if parameter.arg == "name":
                    model_name: str = parameter.value.s
                elif parameter.arg == "fields":
                    field_stmts = parameter.value.elts
                    fields_line_index = parameter.lineno - 1

            # Handle AddField migrations
            elif operation_type == "AddFields":
                if parameter.arg == "model_name":
                    model_name: str = parameter.value.s
                elif parameter.arg == "name":
                    AddField_name = parameter.value.s
                elif parameter.arg == "field":
                    fields_line_index = parameter.lineno - 1

        tmp_model_location = ModelLocation(model_name)
        model_location = model_locations.setdefault(model_name, tmp_model_location)
        if operation_type == "CreateModel":
            model_location.field_line_start = fields_line_index
            model_location.operation_lines = operation_lines
        elif operation_type == "AddFields":
            model_location.AddField_locations[AddField_name] = fields_line_index

        # Determine field line numbers
        for field_stmt in field_stmts:
            field_name = field_stmt.elts[0].s
            model_location.fields.append(field_name)

    return model_locations, True


def reorder(models: ModelFieldsDict, migration: Dict[str, ModelLocation], migration_path: str):
    """Reorder the given migration in-place.

    :param models: Maps model names to a list of fields in the expected order
    :param migration: Maps model names to fields and their respective current locations
    :param migration_path: The path to the migration file
    """

    # Get contents of migration file and split into lines
    with open(migration_path) as f:
        migrations_content = f.read()

    new_content = migrations_content.split("\n")

    for model in migration:
        model_location = migration[model]
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
