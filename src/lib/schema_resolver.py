"""
src/lib/schema_resolver.py
--------------------------
Resolves $ref pointers in fields.json bundles against the common field library.

Usage
-----
    from src.lib.schema_resolver import resolve_fields

    fields = resolve_fields(
        Path("Schemas/fs/collateral_schedule/fields.json"),
        common_root=Path("Schemas/common/fields"),
    )
    # Returns a flat list[dict] identical to the pre-$ref format.
    # Callers see no difference — the $ref machinery is transparent.
"""

import json
import re
from functools import lru_cache
from pathlib import Path

# Pattern for $ref values of the form:
#   common/fields/<lib>.json#/definitions/<field_name>
_REF_PATTERN = re.compile(
    r"^common/fields/(?P<lib>[^/]+)\.json#/definitions/(?P<field_name>.+)$"
)


@lru_cache(maxsize=32)
def _load_common_lib(lib_path: Path) -> dict:
    """Load and cache a common field library file by absolute path."""
    if not lib_path.exists():
        raise FileNotFoundError(
            f"Common field library not found: {lib_path}"
        )
    return json.loads(lib_path.read_text(encoding="utf-8"))


def _resolve_entry(entry: dict, common_root: Path) -> dict:
    """
    Resolve a single fields array entry.

    If the entry contains a ``$ref`` key, parse it and return the referenced
    field definition from the appropriate common library file.  Plain field
    dicts (no ``$ref``) are returned unchanged.

    Parameters
    ----------
    entry:
        A single element from a ``fields.json`` ``fields`` array.
    common_root:
        Absolute path to the directory containing common field library files
        (e.g. ``Schemas/common/fields``).

    Returns
    -------
    dict
        The resolved field definition.

    Raises
    ------
    ValueError
        If the ``$ref`` string does not match the expected format.
    KeyError
        If the referenced field name is not found in the library file.
    """
    ref = entry.get("$ref")
    if ref is None:
        # Plain field — return as-is.
        return entry

    match = _REF_PATTERN.match(ref)
    if not match:
        raise ValueError(
            f"Invalid $ref format: '{ref}'. "
            "Expected 'common/fields/<lib>.json#/definitions/<field_name>'."
        )

    lib_name = match.group("lib")
    field_name = match.group("field_name")
    lib_path = common_root / f"{lib_name}.json"

    lib_data = _load_common_lib(lib_path)
    definitions = lib_data.get("definitions", {})

    if field_name not in definitions:
        raise KeyError(
            f"Field '{field_name}' not found in common library "
            f"'{lib_path}'. Available definitions: "
            f"{sorted(definitions.keys())}"
        )

    return definitions[field_name]


def resolve_fields(
    fields_json_path: Path,
    common_root: Path,
) -> list:
    """
    Load a ``fields.json`` file and return its ``fields`` array with all
    ``$ref`` pointers resolved against the common field library.

    Parameters
    ----------
    fields_json_path:
        Path to the schema bundle's ``fields.json`` file.
    common_root:
        Path to the directory containing common field library files
        (e.g. ``Schemas/common/fields``).

    Returns
    -------
    list[dict]
        Flat list of resolved field definitions.  Callers see no difference
        from a ``fields.json`` that contains no ``$ref`` entries.

    Raises
    ------
    FileNotFoundError
        If ``fields_json_path`` or a referenced common library file does not
        exist.
    ValueError
        If a ``$ref`` string does not match the expected format.
    KeyError
        If a referenced field name is not found in the common library.
    """
    if not fields_json_path.exists():
        raise FileNotFoundError(
            f"fields.json not found: {fields_json_path}"
        )

    data = json.loads(fields_json_path.read_text(encoding="utf-8"))
    raw_fields = data.get("fields", [])

    # Resolve each entry, expanding $ref pointers as needed.
    resolved = [_resolve_entry(entry, common_root) for entry in raw_fields]
    return resolved


def load_schema(
    fields_json_path: Path,
    common_root: Path | None = None,
) -> dict:
    """
    Load a ``fields.json`` file and return the full schema dict with the
    ``fields`` key replaced by the resolved (``$ref``-expanded) field list.

    Parameters
    ----------
    fields_json_path:
        Path to the schema bundle's ``fields.json`` file.
    common_root:
        Path to the common field library directory.  Defaults to
        ``<fields_json_path>/../../../common/fields`` (i.e., three levels up
        from the bundle directory, then into ``common/fields``), which matches
        the standard layout::

            Schemas/
              common/fields/          ← common_root (auto-discovered)
              fs/
                collateral_schedule/
                  fields.json         ← fields_json_path

    Returns
    -------
    dict
        The full schema dict with ``fields`` resolved.
    """
    if common_root is None:
        # Auto-discover: go up three levels from the fields.json file
        # (file -> bundle dir -> vertical dir -> Schemas dir) then into
        # common/fields.
        common_root = fields_json_path.parent.parent.parent / "common" / "fields"

    data = json.loads(fields_json_path.read_text(encoding="utf-8"))
    data["fields"] = resolve_fields(fields_json_path, common_root)
    return data
