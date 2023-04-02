from dataclasses import MISSING, field
from typing import Any, Callable, Dict


##############################################################
# These fields exist as helpers to write more clear code.
#
# Allowing us to from:
#   entity_id: UUIDType = field(
#       default=None,
#       metadata=dict(dump_only=True, metadata=dict(help='Unique ID of the entity.', filterable=True))
#   )
# to
#   entity_id: UUIDType = optional_field(dump_only=True, help='Unique ID of the entity.')
##############################################################
def required_field(
    default: Any = None,
    default_factory: Callable = MISSING,
    dump_only: bool = False,
    load_only: bool = False,
    description: str = None,
    # Marshmallow Schema metadata
    metadata: Dict[str, Any] = None,
    # Marshmallow Schema kwargs
    **schema_kwargs,
):
    if default_factory != MISSING and default is None:
        default = MISSING

    ma_meta = {} if metadata is None else metadata.copy()
    if description is not None:
        ma_meta['description'] = description

    return field(
        default=default,
        default_factory=default_factory,
        metadata=dict(
            **{} if schema_kwargs is None else schema_kwargs,
            required=True,
            dump_only=dump_only,
            load_only=load_only,
            metadata=ma_meta,
        ),
    )


def optional_field(
    default: Any = None,
    default_factory: Callable = MISSING,
    dump_only: bool = False,
    load_only: bool = False,
    description: str = None,
    # Marshmallow Schema metadata
    metadata: Dict[str, Any] = None,
    # Marshmallow Schema kwargs
    **schema_kwargs,
):
    if default_factory != MISSING and default is None:
        default = MISSING

    ma_meta = {} if metadata is None else metadata.copy()
    if description is not None:
        ma_meta['description'] = description

    return field(
        default=default,
        default_factory=default_factory,
        metadata=dict(
            **{} if schema_kwargs is None else schema_kwargs,
            required=False,
            dump_only=dump_only,
            load_only=load_only,
            metadata=ma_meta,
        ),
    )


def dump_only_field(
    default: Any = None,
    default_factory: Callable = MISSING,
    description: str = None,
    # Marshmallow Schema metadata
    metadata: Dict[str, Any] = None,
    # Marshmallow Schema kwargs
    **schema_kwargs,
):
    return optional_field(
        default=default,
        default_factory=default_factory,
        dump_only=True,
        description=description,
        metadata=metadata,
        **schema_kwargs,
    )
