from psycopg2.extras import Json, RealDictCursor
from psycopg2.pool import SimpleConnectionPool
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


@dataclass
class PostgresConfig:
    host: str = "localhost"
    port: int = 5432
    database: str = "bwired_research"
    user: str = "bwired"
    password: str = ""


class PostgresClient:
    def __init__(self, config: PostgresConfig):
        self.config = config
        self.pool = SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            host=config.host,
            port=config.port,
            database=config.database,
            user=config.user,
            password=config.password
        )
        logger.info(f"PostgreSQL connection pool initialized for {config.database}")

    @contextmanager
    def get_connection(self):
        conn = self.pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            self.pool.putconn(conn)

    @contextmanager
    def get_cursor(self, cursor_factory=RealDictCursor):
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=cursor_factory)
            try:
                yield cursor
            finally:
                cursor.close()

    def create_template(
        self,
        name: str,
        description: str,
        schema_json: Dict[str, Any],
        system_prompt: Optional[str] = None,
        seed_questions: Optional[List[str]] = None
    ) -> str:
        with self.get_cursor() as cur:
            cur.execute(
                """
                INSERT INTO research_templates 
                (name, description, schema_json, system_prompt, seed_questions)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (name, description, Json(schema_json), system_prompt, Json(seed_questions))
            )
            result = cur.fetchone()
            return str(result['id'])

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        with self.get_cursor() as cur:
            cur.execute(
                "SELECT * FROM research_templates WHERE id = %s",
                (template_id,)
            )
            result = cur.fetchone()
            return dict(result) if result else None

    def get_template_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        with self.get_cursor() as cur:
            cur.execute(
                "SELECT * FROM research_templates WHERE name = %s",
                (name,)
            )
            result = cur.fetchone()
            return dict(result) if result else None

    def list_templates(self) -> List[Dict[str, Any]]:
        with self.get_cursor() as cur:
            cur.execute("SELECT * FROM research_templates ORDER BY created_at DESC")
            return [dict(row) for row in cur.fetchall()]

    def update_template(self, template_id: str, **updates) -> bool:
        if not updates:
            return False

        set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
        values = list(updates.values())
        values.append(template_id)

        with self.get_cursor() as cur:
            cur.execute(
                f"UPDATE research_templates SET {set_clause} WHERE id = %s",
                values
            )
            return cur.rowcount > 0

    def delete_template(self, template_id: str) -> bool:
        with self.get_cursor() as cur:
            cur.execute(
                "DELETE FROM research_templates WHERE id = %s",
                (template_id,)
            )
            return cur.rowcount > 0

    def create_session(
        self,
        query: str,
        template_id: Optional[str] = None,
        status: str = "searching"
    ) -> str:
        with self.get_cursor() as cur:
            cur.execute(
                """
                INSERT INTO research_sessions (query, template_id, status)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (query, template_id, status)
            )
            result = cur.fetchone()
            return str(result['id'])

    def update_session_status(
        self,
        session_id: str,
        status: str,
        progress: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> bool:
        with self.get_cursor() as cur:
            cur.execute(
                """
                UPDATE research_sessions 
                SET status = %s, progress = COALESCE(%s, progress), error_message = %s
                WHERE id = %s
                """,
                (status, Json(progress) if progress else None, error_message, session_id)
            )
            return cur.rowcount > 0

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self.get_cursor() as cur:
            cur.execute(
                "SELECT * FROM research_sessions WHERE id = %s",
                (session_id,)
            )
            result = cur.fetchone()
            return dict(result) if result else None

    def store_search_results(
        self,
        session_id: str,
        seed_question: str,
        urls: List[Dict[str, Any]]
    ) -> None:
        with self.get_cursor() as cur:
            for url_data in urls:
                cur.execute(
                    """
                    INSERT INTO search_results 
                    (session_id, seed_question, url, title, snippet, relevance_score)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        session_id,
                        seed_question,
                        url_data.get('url'),
                        url_data.get('title'),
                        url_data.get('snippet'),
                        url_data.get('relevance_score', 0)
                    )
                )

    def get_pending_urls(self, session_id: str) -> List[Dict[str, Any]]:
        with self.get_cursor() as cur:
            cur.execute(
                """
                SELECT * FROM search_results 
                WHERE session_id = %s AND status = 'pending'
                ORDER BY relevance_score DESC
                """,
                (session_id,)
            )
            return [dict(row) for row in cur.fetchall()]

    def update_url_status(self, url_id: str, status: str) -> bool:
        with self.get_cursor() as cur:
            cur.execute(
                "UPDATE search_results SET status = %s WHERE id = %s",
                (status, url_id)
            )
            return cur.rowcount > 0

    def store_raw_document(
        self,
        search_result_id: str,
        content_type: str,
        raw_content: str,
        content_hash: str
    ) -> str:
        with self.get_cursor() as cur:
            cur.execute(
                """
                INSERT INTO raw_documents 
                (search_result_id, content_type, raw_content, content_hash)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (search_result_id, content_type, raw_content, content_hash)
            )
            result = cur.fetchone()
            return str(result['id'])

    def check_content_hash(self, content_hash: str) -> bool:
        with self.get_cursor() as cur:
            cur.execute(
                "SELECT 1 FROM raw_documents WHERE content_hash = %s LIMIT 1",
                (content_hash,)
            )
            return cur.fetchone() is not None

    def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        with self.get_cursor() as cur:
            cur.execute(
                "SELECT * FROM raw_documents WHERE id = %s",
                (doc_id,)
            )
            result = cur.fetchone()
            return dict(result) if result else None

    def mark_crawl_failed(self, result_id: str, error_message: str) -> bool:
        with self.get_cursor() as cur:
            cur.execute(
                "UPDATE search_results SET status = 'failed', error_message = %s WHERE id = %s",
                (error_message, result_id)
            )
            return cur.rowcount > 0

    def store_fact(
        self,
        session_id: str,
        chunk_id: Optional[str],
        source_url: str,
        fact_data: Dict[str, Any],
        confidence: float,
        seed_question: Optional[str] = None
    ) -> str:
        with self.get_cursor() as cur:
            cur.execute(
                """
                INSERT INTO research_facts 
                (session_id, chunk_id, source_url, fact_data, confidence, seed_question)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (session_id, chunk_id, source_url, Json(fact_data), confidence, seed_question)
            )
            result = cur.fetchone()
            return str(result['id'])

    def get_facts_by_session(
        self,
        session_id: str,
        min_confidence: float = 0.7
    ) -> List[Dict[str, Any]]:
        with self.get_cursor() as cur:
            cur.execute(
                """
                SELECT * FROM research_facts 
                WHERE session_id = %s AND confidence >= %s
                ORDER BY confidence DESC
                """,
                (session_id, min_confidence)
            )
            return [dict(row) for row in cur.fetchall()]

    def get_facts_by_question(
        self,
        session_id: str,
        seed_question: str
    ) -> List[Dict[str, Any]]:
        with self.get_cursor() as cur:
            cur.execute(
                """
                SELECT * FROM research_facts
                WHERE session_id = %s AND seed_question = %s
                ORDER BY confidence DESC
                """,
                (session_id, seed_question)
            )
            return [dict(row) for row in cur.fetchall()]

    def store_report_sections(
        self,
        session_id: str,
        executive_summary_overview: str,
        executive_summary_conclusions: List[str],
        executive_summary_confidence: str,
        sections: List[Dict[str, Any]],
        sections_count: int,
        key_insights: List[Dict[str, Any]],
        insights_count: int,
        total_facts_analyzed: int,
        unique_sources_count: int,
        avg_confidence: float,
        domain_counts: Dict[str, str]
    ) -> str:
        with self.get_cursor() as cur:
            cur.execute(
                """
                INSERT INTO research_reports
                (session_id, executive_summary_overview, executive_summary_conclusions,
                 executive_summary_confidence, sections, sections_count, key_insights,
                 insights_count, total_facts_analyzed, unique_sources_count,
                 avg_confidence, domain_counts)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (session_id) DO UPDATE SET
                    executive_summary_overview = EXCLUDED.executive_summary_overview,
                    executive_summary_conclusions = EXCLUDED.executive_summary_conclusions,
                    executive_summary_confidence = EXCLUDED.executive_summary_confidence,
                    sections = EXCLUDED.sections,
                    sections_count = EXCLUDED.sections_count,
                    key_insights = EXCLUDED.key_insights,
                    insights_count = EXCLUDED.insights_count,
                    total_facts_analyzed = EXCLUDED.total_facts_analyzed,
                    unique_sources_count = EXCLUDED.unique_sources_count,
                    avg_confidence = EXCLUDED.avg_confidence,
                    domain_counts = EXCLUDED.domain_counts,
                    updated_at = NOW()
                RETURNING id
                """,
                (
                    session_id,
                    executive_summary_overview,
                    Json(executive_summary_conclusions),
                    executive_summary_confidence,
                    Json(sections),
                    sections_count,
                    Json(key_insights),
                    insights_count,
                    total_facts_analyzed,
                    unique_sources_count,
                    avg_confidence,
                    Json(domain_counts)
                )
            )
            result = cur.fetchone()
            return str(result['id'])

    def get_report_sections(
        self,
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        with self.get_cursor() as cur:
            cur.execute(
                "SELECT * FROM research_reports WHERE session_id = %s",
                (session_id,)
            )
            result = cur.fetchone()
            return dict(result) if result else None

    def has_report(self, session_id: str) -> bool:
        with self.get_cursor() as cur:
            cur.execute(
                "SELECT 1 FROM research_reports WHERE session_id = %s LIMIT 1",
                (session_id,)
            )
            return cur.fetchone() is not None

    def close(self):
        self.pool.closeall()
        logger.info("PostgreSQL connection pool closed")
