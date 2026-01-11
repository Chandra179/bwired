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
    
    This function enables dynamic fact extraction schemas based on
    templates stored in the database. It recursively builds
    Pydantic models that match the JSON schema structure,
    which are then used with Ollama's structured output
    to ensure LLM returns data in the expected format.
    
    Args:
        schema_json: Dictionary mapping field names to type strings or nested schemas
            Examples:
                {"event": "str", "date": "str"}
                {"event": "str", "details": {"location": "str", "participants": "list"}}
            
            Supported type strings: "str", "int", "float", "bool", "list", "dict"
            
            Nested structures:
                - Dict: Creates a nested Pydantic model
                - List: Creates a List[Type] field (type from first element)
    
    Returns:
        A dynamically created Pydantic model class that can be used
        for validation and structured LLM output
    
    Note:
        - All fields are required (uses Ellipsis ...)
        - Lists default to empty list []
        - Nested dicts recursively create nested models
        - Unknown types default to str
    
    Usage:
        schema = {"title": "str", "date": "str", "attendees": "list"}
        EventModel = create_dynamic_model(schema)
        # Now EventModel can be used like any Pydantic model:
        # - Validate data: EventModel(**data)
        # - Generate JSON schema: EventModel.model_json_schema()
        # - Use with Ollama: format=EventModel.model_json_schema()
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
