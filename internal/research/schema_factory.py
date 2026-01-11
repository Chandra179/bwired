import logging
from typing import Any, Dict, List, Type, Union
from pydantic import BaseModel, create_model, Field

logger = logging.getLogger(__name__)

TYPE_MAPPING = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": List,
    "dict": Dict,
}


def create_dynamic_model(schema_json: Dict[str, Any]) -> Type[BaseModel]:
    """
    Create a Pydantic model from JSON schema definition.

    Args:
        schema_json: Dictionary mapping field names to type strings or nested schemas
            Examples:
                {"event": "str", "date": "str"}
                {"event": "str", "details": {"location": "str", "participants": "list"}}

    Returns:
        A dynamically created Pydantic model class
    """
    fields = {}

    for field_name, field_type in schema_json.items():
        if isinstance(field_type, str):
            python_type = TYPE_MAPPING.get(field_type, str)
            fields[field_name] = (python_type, ...)
        elif isinstance(field_type, dict):
            nested_model = create_dynamic_model(field_type)
            fields[field_name] = (nested_model, ...)
        elif isinstance(field_type, list) and len(field_type) > 0:
            item_type = field_type[0]
            if isinstance(item_type, str):
                python_type = TYPE_MAPPING.get(item_type, str)
                fields[field_name] = (List[python_type], [])
            elif isinstance(item_type, dict):
                nested_model = create_dynamic_model(item_type)
                fields[field_name] = (List[nested_model], [])
            else:
                fields[field_name] = (List[str], [])
        else:
            fields[field_name] = (str, ...)

    return create_model("DynamicModel", __base__=BaseModel, **fields)
