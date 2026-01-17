#!/bin/bash

set -e

MIGRATIONS_DIR="migrations"
DOCKER_CONTAINER="postgres_db"
DB_NAME="bwired_research"
DB_USER="bwired"

echo "Running database migrations..."

for migration_file in "$MIGRATIONS_DIR"/*.sql; do
    if [ ! -f "$migration_file" ]; then
        echo "No migration files found in $MIGRATIONS_DIR"
        exit 0
    fi

    filename=$(basename "$migration_file")
    version=${filename%%_*}

    check_version=$(docker compose exec -T postgres psql -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT 1 FROM schema_migrations WHERE version = '$version' LIMIT 1;" 2>/dev/null || echo "")

    if [ "$check_version" = "1" ]; then
        echo "✓ Already applied: $filename"
    else
        echo "→ Applying: $filename"
        docker compose exec -T postgres psql -U "$DB_USER" -d "$DB_NAME" < "$migration_file"

        if docker compose exec -T postgres psql -U "$DB_USER" -d "$DB_NAME" -c "INSERT INTO schema_migrations (version) VALUES ('$version');" 2>/dev/null; then
            echo "✓ Applied: $filename"
        else
            echo "✗ Failed to record migration: $filename"
            exit 1
        fi
    fi
done

echo "All migrations completed successfully"
