"""
Reorder the fields in all migrations such that they match the order of the 
fields in the corresponding models files.

Author: Reece Mathews
"""

import os
import os.path
import ast
import re

from typing import List, Dict, Optional, Set, Tuple

from django.utils.topological_sort import stable_topological_sort


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


class ModelInformation:
    """Location of fields in a migration file for a model."""

    def __init__(self, model_name: str):
        self.model_name = model_name  # Name of model

        # Line index of CreateModel operation start and end (inclusive)
        self.operation_lines: Optional[Tuple[int, int]] = None
        # Line index of fields list in CreateModel func
        self.field_line_start: Optional[int] = None
        # Field names present in the CreateModel func
        self.fields = []
        # Location of AddField funcs
        self.AddField_locations = {}
        # Content of AddField funcs - i.e. the field instantiation 
        self.AddField_objs = {}
        # Set of other models which this model references with foreign keys
        self.dependencies = set()

def parse_models(models_path: str) -> List[ModelInformation]:
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
    field_target_orders: ModelFieldsDict = {}
    for model in models:
        field_target_orders[model.name] = ["id"]  # ID always implicitly made first param
        assignments = (item for item in model.body if type(item) is ast.Assign)
        for assignment in assignments:
            field_names = [target.id for target in assignment.targets]
            field_target_orders[model.name].extend(field_names)

    return field_target_orders


def get_dependencies(parameter, operation_type: str, migration_content: str) -> Set[str]:
    """Get a list of dependencies from a operation stmt."""
    dependencies = set()

    def add_dep(value):
        v = value.value
        if type(v).__module__ == "_ast":
            # Is an object rather than a str literal
            dep = ast.get_source_segment(migration_content, value)
        else:
            dep = str(v)
        dependencies.add(dep)

    if operation_type == "CreateModel":
        for field in parameter.value.elts:
            field_op = field.elts[1]
            if field_op.func.attr == "ForeignKey":
                for param in field_op.keywords:
                    if param.arg == "to":
                        add_dep(param.value)

    elif operation_type == "AddField":
        field_op = parameter.value
        if field_op.func.attr == "ForeignKey":
            for param in field_op.keywords:
                if param.arg == "to":
                    add_dep(param.value)

    return dependencies


def parse_migration(migration_path: str) -> Tuple[Dict[str, ModelInformation], bool]:
    """
    Find the line numbers for each field of each model.

    :return:
        - model_informations: ModelInformation objects for each model in the migration
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

    model_informations: Dict[str, ModelInformation] = {}

    # Parse operations assignment to find models
    for operation in operations.elts:

        operation_type = operation.func.attr
        operation_lines = (operation.lineno - 1, operation.end_lineno - 1)

        dependencies = set()
        for parameter in operation.keywords:
            # Handle CreateModel migrations
            if operation_type == "CreateModel":
                if parameter.arg == "name":
                    model_name: str = parameter.value.s
                elif parameter.arg == "fields":
                    field_stmts = parameter.value.elts
                    fields_line_index = parameter.value.lineno - 1
                    deps = get_dependencies(parameter, operation_type, migration_content)
                    dependencies.update(deps)

            # Handle AddField migrations
            elif operation_type == "AddField":
                if parameter.arg == "model_name":
                    model_name: str = parameter.value.s
                elif parameter.arg == "name":
                    AddField_field_name = parameter.value.s
                elif parameter.arg == "field":
                    AddField_field_obj = ast.get_source_segment(migration_content, parameter.value)
                    deps = get_dependencies(parameter, operation_type, migration_content)
                    dependencies.update(deps)

        tmp_model_location = ModelInformation(model_name)
        model_information = model_informations.setdefault(model_name, tmp_model_location)
        model_information.dependencies = dependencies
        if operation_type == "CreateModel":
            model_information.field_line_start = fields_line_index
            model_information.operation_lines = operation_lines
        elif operation_type == "AddFields":
            model_information.AddField_locations[AddField_field_name] = operation_lines
            model_information.AddField_objs[AddField_field_name] = AddField_field_obj

        # Determine field line numbers
        for field_stmt in field_stmts:
            field_name = field_stmt.elts[0].s
            model_information.fields.append(field_name)

    return model_informations, True


def reorder_CreateModels(model_target_orders: ModelFieldsDict, migration_models: Dict[str, ModelInformation], migration_path: str):
    """Reorder only the CreateModel calls for the given migration in-place. This is 
    done if it is deemed impossible to merge AddField calls into CreateModel calls due
    to complex dependencies.

    :param model_target_orders: Maps model names to a list of fields in the expected order
    :param migration_models: Information objects describing models in migration
    :param migration_path: The path to the migration file
    """

    # Get contents of migration file and split into lines
    with open(migration_path) as f:
        migrations_content = f.read()

    new_content = migrations_content.split("\n")

    for model_name in migration_models:
        model_information = migration_models[model_name]
        target_order = model_target_orders[model_name]

        # Remove field lines from content to be sorted
        field_lines: List[Tuple[str, str]] = []
        for field in model_information.fields:
            field_line = new_content.pop(model_information.field_line_start)
            field_lines.append((field, field_line))

        # Sort field lines by position of field name in target_order
        field_lines.sort(key=lambda entry: target_order.index(entry[0]))
        # Re-insert field lines into new_content in new order
        for field_ind, field_line in enumerate(field_lines):
            new_content.insert(model_information.field_line_start + field_ind, field_line[1])

    # Write updated migration to file
    new_content = "\n".join(new_content)
    with open(migration_path, "w") as f:
        f.write(new_content)


def get_order(migration_models: Dict[str, ModelInformation], app_name: str) -> List[str]:
    """Determine the order the models should be placed in such that dependencies 
    are all resolved linearly. Performs a topological sort (from Django) on the 
    dependency_graph."""

    def remove_prefix(s: str, prefix: str) -> str:
        """Remove the prefix from the given string. This method is added in Python 3.9.
        Implementing here as this script is intended for Python 3.8."""
        s = str(s)
        if s.startswith(prefix):
            return s[len(prefix):]
        return s

    dependency_graph = {}
    nodes = set(migration_models.keys())
    for model_name in migration_models:
        model_info = migration_models[model_name]
        dependencies = {remove_prefix(dep, app_name + ".") for dep in model_info.dependencies}
        dependency_graph[model_name] = dependencies
        nodes.update(dependencies)

    for node in nodes:
        dependency_graph.setdefault(node, set())

    return stable_topological_sort(nodes, dependency_graph)


def reorder_migration(field_target_orders: ModelFieldsDict, migration_models: Dict[str, ModelInformation], migration_path: str, app_name: str):
    """Attempt to reorder the entire migration so that table columns match order
    in the corresponding models.py file. Uses a topological sort to determine order of
    CreateModel calls such that no AddField calls are necessary later -- allowing all
    fields to be instantiated within the CreateModel calls in the expected order.

    :param model_target_orders: Maps model names to a list of fields in the expected order
    :param migration_models: Information objects describing models in migration
    :param migration_path: The path to the migration file
    :param app_name: The name of the app this migration is for
    """

    # Get contents of migration file and split into lines
    with open(migration_path) as f:
        migrations_content = f.read()

    model_order = get_order(migration_models, app_name)


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
        field_target_orders = parse_models(models_path)  # Get the expected order of fields

        for migration_name in migrations:
            current_migration_path = migrations_path + migration_name
            # Get the current order of fields
            model_informations, continue_parse = parse_migration(current_migration_path)

            if not continue_parse:
                continue

            reorder_migration(field_target_orders, model_informations, current_migration_path, app)


if __name__ == "__main__":
    reorder_all()
