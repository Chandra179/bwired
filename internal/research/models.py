from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class TemplateField:
    """Schema field definition for template"""
    type: str
    description: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None
    items_type: Optional[str] = None
    required: bool = True

    def __post_init__(self):
        valid_types = {"string", "integer", "float", "array", "object", "boolean"}
        if self.type not in valid_types:
            raise ValueError(
                f"Invalid field type '{self.type}'. "
                f"Must be one of: {valid_types}"
            )


@dataclass
class ResearchTemplate:
    """Research template model for structured data extraction"""
    id: Optional[str] = None
    name: str = ""
    description: str = ""
    schema_json: Dict[str, Any] = field(default_factory=dict)
    system_prompt: Optional[str] = None
    seed_questions: Optional[List[str]] = None
    created_at: Optional[str] = None

    def __post_init__(self):
        if not self.name:
            raise ValueError("Template name cannot be empty")
        if not self.description:
            raise ValueError("Template description cannot be empty")
        if not self.schema_json:
            raise ValueError("Template schema_json cannot be empty")

    def get_field(self, field_name: str) -> Optional[TemplateField]:
        """Get a field definition from schema"""
        fields = self.schema_json.get("fields", {})
        if field_name not in fields:
            return None
        
        field_data = fields[field_name]
        return TemplateField(
            type=field_data.get("type", "string"),
            description=field_data.get("description"),
            properties=field_data.get("properties"),
            items_type=field_data.get("items_type"),
            required=field_data.get("required", True)
        )

    def get_all_fields(self) -> Dict[str, TemplateField]:
        """Get all field definitions from schema"""
        result = {}
        fields = self.schema_json.get("fields", {})
        for name, field_data in fields.items():
            result[name] = TemplateField(
                type=field_data.get("type", "string"),
                description=field_data.get("description"),
                properties=field_data.get("properties"),
                items_type=field_data.get("items_type"),
                required=field_data.get("required", True)
            )
        return result


@dataclass
class TemplateCreateRequest:
    """DTO for creating a new template"""
    name: str
    description: str
    schema_json: Dict[str, Any]
    system_prompt: Optional[str] = None
    seed_questions: Optional[List[str]] = None


@dataclass
class TemplateUpdateRequest:
    """DTO for updating an existing template"""
    name: Optional[str] = None
    description: Optional[str] = None
    schema_json: Optional[Dict[str, Any]] = None
    system_prompt: Optional[str] = None
    seed_questions: Optional[List[str]] = None


@dataclass
class TemplateSelectionResult:
    """Result from LLM-based template selection"""
    template_id: Optional[str]
    template_name: Optional[str]
    confidence: float
    reason: Optional[str] = None


def validate_template_schema(schema: Dict[str, Any]) -> List[str]:
    """
    Validate template schema structure
    Returns list of error messages (empty if valid)
    """
    errors = []
    
    if "fields" not in schema:
        errors.append("Schema must contain 'fields' key")
        return errors
    
    fields = schema["fields"]
    if not isinstance(fields, dict):
        errors.append("'fields' must be a dictionary")
        return errors
    
    if not fields:
        errors.append("'fields' dictionary cannot be empty")
        return errors
    
    for field_name, field_data in fields.items():
        if not isinstance(field_data, dict):
            errors.append(f"Field '{field_name}' must be a dictionary")
            continue
        
        if "type" not in field_data:
            errors.append(f"Field '{field_name}' must have a 'type'")
            continue
        
        field_type = field_data["type"]
        valid_types = {"string", "integer", "float", "array", "object", "boolean"}
        if field_type not in valid_types:
            errors.append(
                f"Field '{field_name}' has invalid type '{field_type}'. "
                f"Must be one of: {valid_types}"
            )
        
        if field_type == "object" and "properties" not in field_data:
            errors.append(f"Object field '{field_name}' must have 'properties'")
        
        if field_type == "array" and "items" not in field_data:
            errors.append(f"Array field '{field_name}' must have 'items'")
    
    return errors
