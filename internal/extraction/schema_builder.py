"""
Dynamic Pydantic model builder from JSON schema.

Converts research template JSON schemas into runtime Pydantic models
for structured LLM extraction.
"""

from typing import Any, Dict, List, Optional, Type, Union
from pydantic import BaseModel, Field, create_model
import logging

logger = logging.getLogger(__name__)


def json_type_to_python(field_def: Dict[str, Any], field_name: str = "") -> tuple[Any, Any]:
    """
    Convert JSON schema type definition to Python type annotation and default.
    
    Args:
        field_def: JSON schema field definition
        field_name: Name of the field (for nested model naming)
        
    Returns:
        Tuple of (python_type, field_default)
    """
    field_type = field_def.get("type", "string")
    description = field_def.get("description", "")
    required = field_def.get("required", True)
    
    # Determine the default value based on required status
    default = ... if required else None
    
    if field_type == "string":
        python_type = str if required else Optional[str]
        return (python_type, Field(default=default, description=description))
    
    elif field_type == "integer":
        python_type = int if required else Optional[int]
        return (python_type, Field(default=default, description=description))
    
    elif field_type == "float" or field_type == "number":
        python_type = float if required else Optional[float]
        return (python_type, Field(default=default, description=description))
    
    elif field_type == "boolean":
        python_type = bool if required else Optional[bool]
        return (python_type, Field(default=default, description=description))
    
    elif field_type == "array":
        items_def = field_def.get("items", {"type": "string"})
        item_type = _get_item_type(items_def, f"{field_name}Item")
        python_type = List[item_type] if required else Optional[List[item_type]]
        return (python_type, Field(default=default, description=description))
    
    elif field_type == "object":
        properties = field_def.get("properties", {})
        if properties:
            # Create a nested model for the object
            nested_model = _build_nested_model(properties, f"{field_name}Model")
            python_type = nested_model if required else Optional[nested_model]
            return (python_type, Field(default=default, description=description))
        else:
            # Generic dict if no properties specified
            python_type = Dict[str, Any] if required else Optional[Dict[str, Any]]
            return (python_type, Field(default=default, description=description))
    
    else:
        # Default to string for unknown types
        logger.warning(f"Unknown type '{field_type}' for field '{field_name}', defaulting to str")
        python_type = str if required else Optional[str]
        return (python_type, Field(default=default, description=description))


def _get_item_type(items_def: Dict[str, Any], name_hint: str) -> Type:
    """
    Get the Python type for array items.
    
    Args:
        items_def: JSON schema for array items
        name_hint: Hint for naming nested models
        
    Returns:
        Python type for the items
    """
    item_type = items_def.get("type", "string")
    
    if item_type == "string":
        return str
    elif item_type == "integer":
        return int
    elif item_type == "float" or item_type == "number":
        return float
    elif item_type == "boolean":
        return bool
    elif item_type == "object":
        properties = items_def.get("properties", {})
        if properties:
            return _build_nested_model(properties, name_hint)
        return Dict[str, Any]
    else:
        return str


def _build_nested_model(properties: Dict[str, Any], model_name: str) -> Type[BaseModel]:
    """
    Build a nested Pydantic model from JSON schema properties.
    
    Args:
        properties: JSON schema properties dict
        model_name: Name for the generated model
        
    Returns:
        Dynamically created Pydantic model class
    """
    field_definitions = {}
    
    for prop_name, prop_def in properties.items():
        python_type, field_default = json_type_to_python(prop_def, prop_name)
        field_definitions[prop_name] = (python_type, field_default)
    
    return create_model(model_name, **field_definitions)


def build_pydantic_model(
    template_schema: Dict[str, Any],
    model_name: str = "ExtractedFact"
) -> Type[BaseModel]:
    """
    Dynamically create a Pydantic model from a research template schema.
    
    Args:
        template_schema: JSON schema from ResearchTemplate.schema_json
                        Expected format: {"fields": {"field_name": {"type": "...", ...}}}
        model_name: Name for the generated model class
        
    Returns:
        Dynamically created Pydantic model class
        
    Example:
        >>> schema = {
        ...     "fields": {
        ...         "event_name": {"type": "string", "description": "Name of event"},
        ...         "year": {"type": "integer"},
        ...         "causes": {"type": "array", "items": {"type": "string"}}
        ...     }
        ... }
        >>> Model = build_pydantic_model(schema)
        >>> instance = Model(event_name="Crisis", year=2008, causes=["debt", "risk"])
    """
    fields = template_schema.get("fields", {})
    
    if not fields:
        raise ValueError("Template schema must contain 'fields' key with field definitions")
    
    field_definitions = {}
    
    for field_name, field_def in fields.items():
        try:
            python_type, field_default = json_type_to_python(field_def, field_name)
            field_definitions[field_name] = (python_type, field_default)
        except Exception as e:
            logger.error(f"Error processing field '{field_name}': {e}")
            raise ValueError(f"Invalid field definition for '{field_name}': {e}")
    
    # Create the dynamic model
    model = create_model(model_name, **field_definitions)
    
    logger.info(f"Built Pydantic model '{model_name}' with {len(field_definitions)} fields")
    
    return model


def build_extraction_model_with_confidence(
    template_schema: Dict[str, Any],
    model_name: str = "ExtractedFactWithConfidence"
) -> Type[BaseModel]:
    """
    Build an extraction model that includes a confidence score field.
    
    This wraps the base extracted data with metadata fields useful for
    fact validation and storage.
    
    Args:
        template_schema: JSON schema from template
        model_name: Name for the model
        
    Returns:
        Pydantic model with extracted_data and confidence_score fields
    """
    # Build the base fact model
    base_model = build_pydantic_model(template_schema, f"{model_name}Data")
    
    # Create wrapper model with confidence
    wrapper = create_model(
        model_name,
        extracted_data=(base_model, Field(..., description="The extracted structured data")),
        confidence_score=(float, Field(
            default=0.8,
            ge=0.0,
            le=1.0,
            description="Confidence score from 0.0 to 1.0 indicating extraction reliability"
        )),
        extraction_notes=(Optional[str], Field(
            default=None,
            description="Optional notes about the extraction quality or any uncertainties"
        ))
    )
    
    return wrapper


def validate_schema_for_extraction(template_schema: Dict[str, Any]) -> List[str]:
    """
    Validate that a template schema can be used for extraction.
    
    Args:
        template_schema: JSON schema to validate
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    if "fields" not in template_schema:
        errors.append("Schema must contain 'fields' key")
        return errors
    
    fields = template_schema["fields"]
    
    if not isinstance(fields, dict):
        errors.append("'fields' must be a dictionary")
        return errors
    
    if not fields:
        errors.append("'fields' cannot be empty")
        return errors
    
    valid_types = {"string", "integer", "float", "number", "boolean", "array", "object"}
    
    for field_name, field_def in fields.items():
        if not isinstance(field_def, dict):
            errors.append(f"Field '{field_name}' must be a dictionary")
            continue
        
        if "type" not in field_def:
            errors.append(f"Field '{field_name}' must have a 'type'")
            continue
        
        field_type = field_def["type"]
        if field_type not in valid_types:
            errors.append(f"Field '{field_name}' has invalid type '{field_type}'")
        
        # Validate array items
        if field_type == "array" and "items" not in field_def:
            errors.append(f"Array field '{field_name}' should have 'items' definition")
        
        # Validate object properties
        if field_type == "object" and "properties" not in field_def:
            # This is a warning, not an error - will default to Dict[str, Any]
            logger.warning(f"Object field '{field_name}' has no 'properties', will use Dict[str, Any]")
    
    return errors
