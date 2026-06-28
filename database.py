import json
import os
import re
import sqlite3
import unicodedata
from contextlib import closing
from datetime import datetime
from pathlib import Path

from werkzeug.security import generate_password_hash


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = Path(os.environ.get("DATABASE_PATH", DATA_DIR / "minhas_ferramentas.db"))

DEFAULT_CATEGORIES = [
    ("Cybersegurança", "#35d0ff", 10),
    ("IA", "#7cf7c8", 20),
    ("Monitoramento", "#9ea7ff", 30),
    ("Utilidades", "#ffd166", 40),
    ("Análise", "#f471b5", 50),
    ("Verificação", "#00b8a9", 60),
    ("Outros", "#94a3b8", 70),
]

DEFAULT_TOOLS = [
    ("IA ou Real?", "Verificação", "Análise estimativa para textos, imagens, áudios e vídeos com sinais técnicos de geração por IA.", "Ferramenta criada para apoiar verificações digitais rápidas com relatório técnico, explicação simples e sinais organizados.", ["IA", "verificação", "conteúdo digital"], ["Análise de conteúdo digital", "Relatório técnico", "Explicação simples"], "/static/images/tool-ai-real.png", "#35d0ff", 10, 1, 1, 0),
    ("Sentinel Vision", "Monitoramento", "Monitoramento visual para operações de segurança, leitura de placas e acompanhamento de ocorrências.", "Painel operacional para equipes que precisam acompanhar câmeras, eventos, alertas e indicadores em tempo real.", ["monitoramento", "segurança", "câmeras"], ["Indicadores em tempo real", "Controle de ocorrências", "Visual institucional"], "/static/images/tool-sentinel.png", "#7cf7c8", 20, 1, 0, 0),
    ("BetVision Analytics", "Análise", "Painel de jogos, estatísticas e leitura rápida de oportunidades para acompanhamento esportivo.", "Ambiente analítico com foco em partidas, placares, métricas e sinais visuais para tomada de decisão com contexto.", ["esportes", "analytics", "placar"], ["Lista de jogos", "Cards estatísticos", "Base para dados em tempo real"], "/static/images/tool-betvision.png", "#ffd166", 30, 1, 0, 1),
    ("Painel de Links Inteligentes", "Utilidades", "Organize links, sistemas internos e atalhos importantes em uma vitrine rápida e segura.", "Ferramenta utilitária para concentrar acessos essenciais em uma página com busca, categorias e controle administrativo.", ["links", "produtividade", "hub"], ["Busca instantânea", "Organização por categoria", "Destaques visuais"], "/static/images/tool-links.png", "#9ea7ff", 40, 0, 1, 0),
]


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_connection():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with closing(get_connection()) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                slug TEXT NOT NULL UNIQUE,
                color TEXT NOT NULL DEFAULT '#35d0ff',
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tools (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                slug TEXT NOT NULL UNIQUE,
                short_description TEXT NOT NULL,
                full_description TEXT NOT NULL,
                category_id INTEGER,
                tags TEXT NOT NULL DEFAULT '[]',
                features TEXT NOT NULL DEFAULT '[]',
                screenshots TEXT NOT NULL DEFAULT '[]',
                image_url TEXT,
                link TEXT,
                version TEXT NOT NULL DEFAULT '1.0',
                status TEXT NOT NULL DEFAULT 'Ativo',
                card_color TEXT NOT NULL DEFAULT '#35d0ff',
                featured INTEGER NOT NULL DEFAULT 0,
                is_new INTEGER NOT NULL DEFAULT 0,
                is_beta INTEGER NOT NULL DEFAULT 0,
                hidden INTEGER NOT NULL DEFAULT 0,
                sort_order INTEGER NOT NULL DEFAULT 0,
                access_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS administrators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        seed_defaults(conn)
        conn.commit()


def seed_defaults(conn):
    for name, color, sort_order in DEFAULT_CATEGORIES:
        conn.execute(
            "INSERT OR IGNORE INTO categories (name, slug, color, sort_order, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (name, slugify(name), color, sort_order, now(), now()),
        )
    if conn.execute("SELECT COUNT(*) AS total FROM tools").fetchone()["total"] == 0:
        for name, category_name, short_description, full_description, tags, features, image_url, color, order, featured, is_new, is_beta in DEFAULT_TOOLS:
            category = conn.execute("SELECT id FROM categories WHERE name = ?", (category_name,)).fetchone()
            insert_tool(
                conn,
                {
                    "name": name,
                    "short_description": short_description,
                    "full_description": full_description,
                    "category_id": category["id"] if category else None,
                    "tags": tags,
                    "features": features,
                    "screenshots": [],
                    "image_url": image_url,
                    "link": "#",
                    "version": "1.0",
                    "status": "Ativo",
                    "card_color": color,
                    "featured": featured,
                    "is_new": is_new,
                    "is_beta": is_beta,
                    "hidden": 0,
                    "sort_order": order,
                },
            )
    if conn.execute("SELECT COUNT(*) AS total FROM administrators").fetchone()["total"] == 0:
        username = os.environ.get("ADMIN_USERNAME", "admin")
        password_hash = os.environ.get("ADMIN_PASSWORD_HASH") or generate_password_hash(os.environ.get("ADMIN_PASSWORD", "admin123"))
        conn.execute(
            "INSERT INTO administrators (username, password_hash, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (username, password_hash, now(), now()),
        )


def slugify(value):
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower() or "item"


def unique_slug(conn, table, base_slug, current_id=None):
    slug = base_slug
    suffix = 2
    while True:
        if current_id:
            exists = conn.execute(f"SELECT id FROM {table} WHERE slug = ? AND id != ?", (slug, current_id)).fetchone()
        else:
            exists = conn.execute(f"SELECT id FROM {table} WHERE slug = ?", (slug,)).fetchone()
        if not exists:
            return slug
        slug = f"{base_slug}-{suffix}"
        suffix += 1


def json_list(value):
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False)
    if not value:
        return "[]"
    return json.dumps([item.strip() for item in str(value).split(",") if item.strip()], ensure_ascii=False)


def decode_json_list(value):
    try:
        decoded = json.loads(value or "[]")
    except json.JSONDecodeError:
        return []
    return decoded if isinstance(decoded, list) else []


def row_to_tool(row):
    if not row:
        return None
    item = dict(row)
    item["tags"] = decode_json_list(item.get("tags"))
    item["features"] = decode_json_list(item.get("features"))
    item["screenshots"] = decode_json_list(item.get("screenshots"))
    for key in ("featured", "is_new", "is_beta", "hidden"):
        item[key] = bool(item.get(key))
    return item


def list_categories():
    with closing(get_connection()) as conn:
        rows = conn.execute(
            """
            SELECT categories.*, COUNT(tools.id) AS tool_count
            FROM categories
            LEFT JOIN tools ON tools.category_id = categories.id
            GROUP BY categories.id
            ORDER BY categories.sort_order ASC, categories.name ASC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_category(category_id):
    with closing(get_connection()) as conn:
        row = conn.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()
    return dict(row) if row else None


def create_category(name, color="#35d0ff", sort_order=0):
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            "INSERT INTO categories (name, slug, color, sort_order, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (name, unique_slug(conn, "categories", slugify(name)), color, int(sort_order or 0), now(), now()),
        )
        conn.commit()
        return cursor.lastrowid


def update_category(category_id, name, color="#35d0ff", sort_order=0):
    with closing(get_connection()) as conn:
        conn.execute(
            "UPDATE categories SET name = ?, slug = ?, color = ?, sort_order = ?, updated_at = ? WHERE id = ?",
            (name, unique_slug(conn, "categories", slugify(name), category_id), color, int(sort_order or 0), now(), category_id),
        )
        conn.commit()


def delete_category(category_id):
    with closing(get_connection()) as conn:
        count = conn.execute("SELECT COUNT(*) AS total FROM tools WHERE category_id = ?", (category_id,)).fetchone()["total"]
        if count:
            return False
        conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        conn.commit()
        return True


def list_tools(include_hidden=False):
    where = "" if include_hidden else "WHERE tools.hidden = 0"
    with closing(get_connection()) as conn:
        rows = conn.execute(
            f"""
            SELECT tools.*, categories.name AS category_name, categories.slug AS category_slug, categories.color AS category_color
            FROM tools
            LEFT JOIN categories ON categories.id = tools.category_id
            {where}
            ORDER BY tools.sort_order ASC, tools.featured DESC, tools.updated_at DESC, tools.name ASC
            """
        ).fetchall()
    return [row_to_tool(row) for row in rows]


def get_tool(tool_id, include_hidden=False):
    hidden_clause = "" if include_hidden else "AND tools.hidden = 0"
    with closing(get_connection()) as conn:
        row = conn.execute(
            f"""
            SELECT tools.*, categories.name AS category_name, categories.slug AS category_slug, categories.color AS category_color
            FROM tools
            LEFT JOIN categories ON categories.id = tools.category_id
            WHERE tools.id = ? {hidden_clause}
            """,
            (tool_id,),
        ).fetchone()
    return row_to_tool(row)


def get_tool_by_slug(slug, include_hidden=False):
    hidden_clause = "" if include_hidden else "AND tools.hidden = 0"
    with closing(get_connection()) as conn:
        row = conn.execute(
            f"""
            SELECT tools.*, categories.name AS category_name, categories.slug AS category_slug, categories.color AS category_color
            FROM tools
            LEFT JOIN categories ON categories.id = tools.category_id
            WHERE tools.slug = ? {hidden_clause}
            """,
            (slug,),
        ).fetchone()
    return row_to_tool(row)


def insert_tool(conn, data):
    cursor = conn.execute(
        """
        INSERT INTO tools (
            name, slug, short_description, full_description, category_id, tags, features,
            screenshots, image_url, link, version, status, card_color, featured, is_new,
            is_beta, hidden, sort_order, access_count, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["name"],
            unique_slug(conn, "tools", slugify(data["name"])),
            data.get("short_description", ""),
            data.get("full_description", ""),
            data.get("category_id"),
            json_list(data.get("tags")),
            json_list(data.get("features")),
            json_list(data.get("screenshots")),
            data.get("image_url", ""),
            data.get("link", ""),
            data.get("version", "1.0"),
            data.get("status", "Ativo"),
            data.get("card_color", "#35d0ff"),
            int(bool(data.get("featured"))),
            int(bool(data.get("is_new"))),
            int(bool(data.get("is_beta"))),
            int(bool(data.get("hidden"))),
            int(data.get("sort_order") or 0),
            int(data.get("access_count") or 0),
            now(),
            now(),
        ),
    )
    return cursor.lastrowid


def create_tool(data):
    with closing(get_connection()) as conn:
        tool_id = insert_tool(conn, data)
        conn.commit()
        return tool_id


def update_tool(tool_id, data):
    with closing(get_connection()) as conn:
        conn.execute(
            """
            UPDATE tools
            SET name = ?, slug = ?, short_description = ?, full_description = ?, category_id = ?,
                tags = ?, features = ?, screenshots = ?, image_url = ?, link = ?, version = ?,
                status = ?, card_color = ?, featured = ?, is_new = ?, is_beta = ?, hidden = ?,
                sort_order = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                data["name"],
                unique_slug(conn, "tools", slugify(data["name"]), tool_id),
                data.get("short_description", ""),
                data.get("full_description", ""),
                data.get("category_id"),
                json_list(data.get("tags")),
                json_list(data.get("features")),
                json_list(data.get("screenshots")),
                data.get("image_url", ""),
                data.get("link", ""),
                data.get("version", "1.0"),
                data.get("status", "Ativo"),
                data.get("card_color", "#35d0ff"),
                int(bool(data.get("featured"))),
                int(bool(data.get("is_new"))),
                int(bool(data.get("is_beta"))),
                int(bool(data.get("hidden"))),
                int(data.get("sort_order") or 0),
                now(),
                tool_id,
            ),
        )
        conn.commit()


def delete_tool(tool_id):
    with closing(get_connection()) as conn:
        conn.execute("DELETE FROM tools WHERE id = ?", (tool_id,))
        conn.commit()


def duplicate_tool(tool_id):
    tool = get_tool(tool_id, include_hidden=True)
    if not tool:
        return None
    data = dict(tool)
    data["name"] = f"{tool['name']} cópia"
    data["access_count"] = 0
    with closing(get_connection()) as conn:
        new_id = insert_tool(conn, data)
        conn.commit()
        return new_id


def increment_tool_access(tool_id):
    with closing(get_connection()) as conn:
        conn.execute("UPDATE tools SET access_count = access_count + 1 WHERE id = ?", (tool_id,))
        conn.commit()


def get_admin_by_username(username):
    with closing(get_connection()) as conn:
        row = conn.execute("SELECT * FROM administrators WHERE username = ?", (username,)).fetchone()
    return dict(row) if row else None


def get_dashboard_stats():
    with closing(get_connection()) as conn:
        totals = conn.execute(
            """
            SELECT
                COUNT(*) AS tools_total,
                SUM(CASE WHEN hidden = 0 THEN 1 ELSE 0 END) AS visible_total,
                SUM(CASE WHEN featured = 1 THEN 1 ELSE 0 END) AS featured_total,
                SUM(access_count) AS access_total
            FROM tools
            """
        ).fetchone()
        categories_total = conn.execute("SELECT COUNT(*) AS total FROM categories").fetchone()["total"]
        latest = conn.execute(
            """
            SELECT tools.*, categories.name AS category_name, categories.slug AS category_slug, categories.color AS category_color
            FROM tools
            LEFT JOIN categories ON categories.id = tools.category_id
            ORDER BY datetime(tools.updated_at) DESC, tools.id DESC
            LIMIT 5
            """
        ).fetchall()
        most_accessed = conn.execute(
            """
            SELECT tools.*, categories.name AS category_name, categories.slug AS category_slug, categories.color AS category_color
            FROM tools
            LEFT JOIN categories ON categories.id = tools.category_id
            ORDER BY tools.access_count DESC, tools.name ASC
            LIMIT 5
            """
        ).fetchall()
    return {
        "tools_total": int(totals["tools_total"] or 0),
        "visible_total": int(totals["visible_total"] or 0),
        "featured_total": int(totals["featured_total"] or 0),
        "access_total": int(totals["access_total"] or 0),
        "categories_total": int(categories_total or 0),
        "latest": [row_to_tool(row) for row in latest],
        "most_accessed": [row_to_tool(row) for row in most_accessed],
    }
