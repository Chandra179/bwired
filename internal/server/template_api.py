"""Template management endpoints."""

import logging
from typing import List

from fastapi import APIRouter, HTTPException, status, Depends

from internal.research.template_manager import TemplateManager
from internal.research.models import validate_template_schema
from internal.server.dependencies import get_template_manager
from internal.server.schemas.research import (
    TemplateCreateRequest,
    TemplateUpdateRequest,
    TemplateResponse,
)
from internal.server.errors import (
    handle_not_found,
    handle_validation_error,
    log_and_raise_internal_error,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/research/templates", tags=["templates"])


@router.get("", response_model=List[dict], summary="List all research templates")
async def list_templates(
    manager: TemplateManager = Depends(get_template_manager),
) -> List[dict]:
    """Retrieve all available research templates."""
    try:
        templates = manager.list_templates()
        return [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "created_at": t.created_at,
                "field_count": len(t.get_all_fields()),
            }
            for t in templates
        ]
    except Exception as e:
        log_and_raise_internal_error("retrieve templates", e)


@router.post(
    "",
    response_model=TemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new research template",
    description="Creates a new template for structured data extraction with validation.",
)
async def create_template(
    request_data: TemplateCreateRequest,
    manager: TemplateManager = Depends(get_template_manager),
) -> TemplateResponse:
    """Create a new research template."""
    try:
        errors = validate_template_schema(request_data.schema_json)
        if errors:
            handle_validation_error(f"Schema validation failed: {', '.join(errors)}")

        template_id = manager.create_template(
            name=request_data.name,
            description=request_data.description,
            schema_json=request_data.schema_json,
            system_prompt=request_data.system_prompt,
            seed_questions=request_data.seed_questions,
        )

        template = manager.get_template(template_id)

        if not template:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Template created but failed to retrieve",
            )

        return TemplateResponse(
            id=template.id or "",
            name=template.name,
            description=template.description,
            schema_json=template.schema_json,
            system_prompt=template.system_prompt,
            seed_questions=template.seed_questions,
            created_at=template.created_at or "",
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error creating template: {e}")
        handle_validation_error(str(e))
    except Exception as e:
        log_and_raise_internal_error("create template", e)


@router.get(
    "/{template_id}",
    response_model=TemplateResponse,
    summary="Get a specific research template",
    description="Retrieves the full details of a research template by ID.",
)
async def get_template(
    template_id: str, manager: TemplateManager = Depends(get_template_manager)
) -> TemplateResponse:
    """Get a specific research template by ID."""
    try:
        template = manager.get_template(template_id)

        if not template:
            handle_not_found("Template", template_id)

        return TemplateResponse(
            id=template.id or "",
            name=template.name,
            description=template.description,
            schema_json=template.schema_json,
            system_prompt=template.system_prompt,
            seed_questions=template.seed_questions,
            created_at=template.created_at or "",
        )

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise_internal_error("retrieve template", e)


@router.put(
    "/{template_id}",
    response_model=TemplateResponse,
    summary="Update a research template",
    description="Updates an existing research template. Supports partial updates.",
)
async def update_template(
    template_id: str,
    request_data: TemplateUpdateRequest,
    manager: TemplateManager = Depends(get_template_manager),
) -> TemplateResponse:
    """Update an existing research template."""
    try:
        if request_data.schema_json:
            errors = validate_template_schema(request_data.schema_json)
            if errors:
                handle_validation_error(
                    f"Schema validation failed: {', '.join(errors)}"
                )

        template = manager.get_template(template_id)

        if not template:
            handle_not_found("Template", template_id)

        success = manager.update_template(
            template_id=template_id,
            name=request_data.name,
            description=request_data.description,
            schema_json=request_data.schema_json,
            system_prompt=request_data.system_prompt,
            seed_questions=request_data.seed_questions,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update template",
            )

        updated_template = manager.get_template(template_id)

        if not updated_template:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Template updated but failed to retrieve",
            )

        return TemplateResponse(
            id=updated_template.id or "",
            name=updated_template.name,
            description=updated_template.description,
            schema_json=updated_template.schema_json,
            system_prompt=updated_template.system_prompt,
            seed_questions=updated_template.seed_questions,
            created_at=updated_template.created_at or "",
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating template: {e}")
        handle_validation_error(str(e))
    except Exception as e:
        log_and_raise_internal_error("update template", e)


@router.delete(
    "/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a research template",
    description="Deletes a research template by ID.",
)
async def delete_template(
    template_id: str, manager: TemplateManager = Depends(get_template_manager)
) -> None:
    """Delete a research template by ID."""
    try:
        template = manager.get_template(template_id)

        if not template:
            handle_not_found("Template", template_id)

        success = manager.delete_template(template_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete template",
            )

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise_internal_error("delete template", e)
