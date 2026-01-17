import logging
from typing import Optional, List
from internal.storage.postgres_client import PostgresClient
from internal.research.models import (
    ResearchTemplate,
    validate_template_schema
)

logger = logging.getLogger(__name__)


class TemplateManager:
    """Business logic layer for research template management"""

    def __init__(self, postgres_client: PostgresClient):
        self.pg = postgres_client
        logger.info("TemplateManager initialized")

    def create_template(
        self,
        name: str,
        description: str,
        schema_json: dict,
        system_prompt: Optional[str] = None,
        seed_questions: Optional[List[str]] = None
    ) -> str:
        """
        Create a new research template

        Returns template_id
        """
        errors = validate_template_schema(schema_json)
        if errors:
            raise ValueError(f"Invalid schema: {', '.join(errors)}")

        template_id = self.pg.create_template(
            name=name,
            description=description,
            schema_json=schema_json,
            system_prompt=system_prompt,
            seed_questions=seed_questions
        )
        
        logger.info(f"Created template '{name}' with id: {template_id}")
        return template_id

    def get_template(self, template_id: str) -> Optional[ResearchTemplate]:
        """Get template by ID"""
        result = self.pg.get_template(template_id)
        if not result:
            return None
        
        created_at = result.get('created_at')
        return ResearchTemplate(
            id=str(result['id']),
            name=result['name'],
            description=result['description'],
            schema_json=result['schema_json'],
            system_prompt=result.get('system_prompt'),
            seed_questions=result.get('seed_questions'),
            created_at=created_at.isoformat() if created_at else None
        )

    def get_template_by_name(self, name: str) -> Optional[ResearchTemplate]:
        """Get template by name"""
        result = self.pg.get_template_by_name(name)
        if not result:
            return None
        
        created_at = result.get('created_at')
        return ResearchTemplate(
            id=str(result['id']),
            name=result['name'],
            description=result['description'],
            schema_json=result['schema_json'],
            system_prompt=result.get('system_prompt'),
            seed_questions=result.get('seed_questions'),
            created_at=created_at.isoformat() if created_at else None
        )

    def list_templates(self) -> List[ResearchTemplate]:
        """List all templates"""
        results = self.pg.list_templates()
        templates = []
        for r in results:
            created_at = r.get('created_at')
            templates.append(ResearchTemplate(
                id=str(r['id']),
                name=r['name'],
                description=r['description'],
                schema_json=r['schema_json'],
                system_prompt=r.get('system_prompt'),
                seed_questions=r.get('seed_questions'),
                created_at=created_at.isoformat() if created_at else None
            ))
        return templates

    def update_template(
        self,
        template_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        schema_json: Optional[dict] = None,
        system_prompt: Optional[str] = None,
        seed_questions: Optional[List[str]] = None
    ) -> bool:
        """
        Update an existing template

        Returns True if update successful, False otherwise
        """
        if not any([name, description, schema_json, system_prompt, seed_questions]):
            raise ValueError("At least one field must be provided for update")

        updates = {}
        if name is not None:
            updates['name'] = name
        if description is not None:
            updates['description'] = description
        if schema_json is not None:
            errors = validate_template_schema(schema_json)
            if errors:
                raise ValueError(f"Invalid schema: {', '.join(errors)}")
            from psycopg2.extras import Json
            updates['schema_json'] = Json(schema_json)
        if system_prompt is not None:
            updates['system_prompt'] = system_prompt
        if seed_questions is not None:
            from psycopg2.extras import Json
            updates['seed_questions'] = Json(seed_questions)

        success = self.pg.update_template(template_id, **updates)
        if success:
            logger.info(f"Updated template {template_id}")
        return success

    def delete_template(self, template_id: str) -> bool:
        """
        Delete a template

        Returns True if deleted, False otherwise
        """
        success = self.pg.delete_template(template_id)
        if success:
            logger.info(f"Deleted template {template_id}")
        return success

    def select_template(
        self,
        query: str,
        confidence_threshold: float = 0.6
    ):
        """
        Select best matching template using LLM based on query

        Returns TemplateSelectionResult or None if no match above threshold
        """
        from internal.research.models import TemplateSelectionResult
        from ollama import Client
        import json

        templates = self.list_templates()
        
        if not templates:
            logger.warning("No templates available for selection")
            return TemplateSelectionResult(
                template_id=None,
                template_name=None,
                confidence=0.0,
                reason="No templates available"
            )
        
        if len(templates) == 1:
            template = templates[0]
            return TemplateSelectionResult(
                template_id=template.id,
                template_name=template.name,
                confidence=1.0,
                reason="Only template available"
            )

        template_summaries = []
        for t in templates:
            fields = ", ".join(t.get_all_fields().keys())
            summary = {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "fields": fields
            }
            template_summaries.append(summary)

        prompt = f"""You are a research assistant that selects the best template for a research query.

Research Query: "{query}"

Available Templates:
{json.dumps(template_summaries, indent=2)}

Select the BEST matching template for this query. Consider:
1. The domain/topic of the query
2. The types of information the user likely wants
3. The fields defined in each template

Respond in JSON format:
{{
    "selected_template_id": "template_id or null if none match well",
    "confidence": 0.0 to 1.0,
    "reason": "brief explanation of your choice"
}}

Select a template only if you are confident it's a good match (confidence >= {confidence_threshold}). Otherwise, set selected_template_id to null."""

        try:
            client = Client(host='http://localhost:11434')
            response = client.chat(
                model='llama3.2',
                messages=[{'role': 'user', 'content': prompt}],
                format='json'
            )
            
            result_text = response['message']['content']
            result = json.loads(result_text)
            
            selected_id = result.get('selected_template_id')
            confidence = float(result.get('confidence', 0.0))
            reason = result.get('reason', 'No reason provided')
            
            if selected_id and confidence >= confidence_threshold:
                template = next((t for t in templates if t.id == selected_id), None)
                if template:
                    logger.info(
                        f"Selected template '{template.name}' "
                        f"with confidence {confidence:.2f}"
                    )
                    return TemplateSelectionResult(
                        template_id=selected_id,
                        template_name=template.name,
                        confidence=confidence,
                        reason=reason
                    )
            
            logger.info(
                f"No template selected (confidence {confidence:.2f} < {confidence_threshold})"
            )
            return TemplateSelectionResult(
                template_id=None,
                template_name=None,
                confidence=confidence,
                reason=reason
            )
            
        except Exception as e:
            logger.error(f"Error during template selection: {e}")
            return TemplateSelectionResult(
                template_id=None,
                template_name=None,
                confidence=0.0,
                reason=f"LLM selection failed: {str(e)}"
            )
