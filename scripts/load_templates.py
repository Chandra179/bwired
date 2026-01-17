#!/usr/bin/env python
"""
Load research templates from JSON files into PostgreSQL

Usage:
    python scripts/load_templates.py --directory templates/
    python scripts/load_templates.py --file templates/historical_economy_events.json
    python scripts/load_templates.py --directory templates/ --dry-run
"""

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from internal.config import load_config
from internal.storage.postgres_client import PostgresClient, PostgresConfig
from internal.research.template_manager import TemplateManager
from internal.research.models import validate_template_schema

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_template_from_file(file_path: str) -> dict:
    """Load template JSON from file"""
    logger.info(f"Loading template from {file_path}")
    
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    required_fields = ['name', 'description', 'schema_json']
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Template missing required field: {field}")
    
    return data


def validate_template(data: dict) -> bool:
    """Validate template structure"""
    errors = validate_template_schema(data.get('schema_json', {}))
    if errors:
        logger.error(f"Schema validation errors: {', '.join(errors)}")
        return False
    return True


def upsert_template(
    manager: TemplateManager,
    data: dict,
    dry_run: bool = False,
    verbose: bool = False
) -> str:
    """
    Insert or update template
    
    Returns: 'created', 'updated', 'skipped', or 'error'
    """
    name = data['name']
    
    if not validate_template(data):
        return 'error'
    
    existing = manager.get_template_by_name(name)
    
    if existing:
        if dry_run:
            logger.info(f"[DRY RUN] Would update template: {name}")
            return 'updated'
        
        if existing.id is None:
            logger.error(f"Template {name} has invalid ID")
            return 'error'
        
        try:
            manager.update_template(
                template_id=existing.id,
                name=data.get('name'),
                description=data.get('description'),
                schema_json=data.get('schema_json'),
                system_prompt=data.get('system_prompt'),
                seed_questions=data.get('seed_questions')
            )
            logger.info(f"Updated template: {name}")
            return 'updated'
        except Exception as e:
            logger.error(f"Failed to update template {name}: {e}")
            return 'error'
    else:
        if dry_run:
            logger.info(f"[DRY RUN] Would create template: {name}")
            return 'created'
        
        try:
            manager.create_template(
                name=data['name'],
                description=data['description'],
                schema_json=data['schema_json'],
                system_prompt=data.get('system_prompt'),
                seed_questions=data.get('seed_questions')
            )
            logger.info(f"Created template: {name}")
            return 'created'
        except Exception as e:
            logger.error(f"Failed to create template {name}: {e}")
            return 'error'


def load_templates_from_directory(
    manager: TemplateManager,
    directory: str,
    dry_run: bool = False,
    verbose: bool = False
) -> dict:
    """Load all template JSON files from directory"""
    results = {
        'total': 0,
        'created': 0,
        'updated': 0,
        'skipped': 0,
        'error': 0
    }
    
    dir_path = Path(directory)
    if not dir_path.exists():
        logger.error(f"Directory not found: {directory}")
        return results
    
    json_files = sorted(dir_path.glob('*.json'))
    if not json_files:
        logger.warning(f"No JSON files found in {directory}")
        return results
    
    for json_file in json_files:
        results['total'] += 1
        
        try:
            data = load_template_from_file(str(json_file))
            result = upsert_template(manager, data, dry_run, verbose)
            results[result] = results.get(result, 0) + 1
            
            if verbose:
                logger.info(f"Processed: {json_file.name} -> {result}")
                
        except Exception as e:
            logger.error(f"Error processing {json_file.name}: {e}")
            results['error'] += 1
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description='Load research templates into PostgreSQL'
    )
    parser.add_argument(
        '--directory', '-d',
        default='templates/',
        help='Directory containing template JSON files'
    )
    parser.add_argument(
        '--file', '-f',
        help='Single template file to load'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate without making changes'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Path to config file'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        config = load_config(args.config)
        
        if config.research is None:
            logger.error("Research configuration not found in config file")
            sys.exit(1)
        
        postgres_config = PostgresConfig(
            host=config.research.postgres.host,
            port=config.research.postgres.port,
            database=config.research.postgres.database,
            user=config.research.postgres.user,
            password=config.research.postgres.password
        )
        
        logger.info(f"Connecting to PostgreSQL: {postgres_config.host}:{postgres_config.port}/{postgres_config.database}")
        logger.info(f"User: {postgres_config.user}")
        logger.info(f"Password: {'*' * len(postgres_config.password) if postgres_config.password else 'NONE'}")
        
        pg_client = PostgresClient(postgres_config)
        manager = TemplateManager(pg_client)
        
        logger.info("=" * 60)
        logger.info("Template Loading Script")
        logger.info("=" * 60)
        
        if args.file:
            logger.info(f"Loading single file: {args.file}")
            data = load_template_from_file(args.file)
            result = upsert_template(manager, data, args.dry_run, args.verbose)
            print(f"\nResult: {result}")
        else:
            logger.info(f"Loading from directory: {args.directory}")
            results = load_templates_from_directory(
                manager, args.directory, args.dry_run, args.verbose
            )
            
            logger.info("=" * 60)
            logger.info("Summary:")
            logger.info(f"  Total files: {results['total']}")
            logger.info(f"  Created: {results['created']}")
            logger.info(f"  Updated: {results['updated']}")
            logger.info(f"  Errors: {results['error']}")
            logger.info("=" * 60)
            
            if results['error'] > 0:
                sys.exit(1)
        
        pg_client.close()
        
    except Exception as e:
        logger.error(f"Script failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
