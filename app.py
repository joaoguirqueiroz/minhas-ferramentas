import os
import secrets
import time
from functools import wraps
from pathlib import Path

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

from database import (
    create_category,
    create_tool,
    delete_category,
    delete_tool,
    duplicate_tool,
    get_admin_by_username,
    get_category,
    get_dashboard_stats,
    get_tool,
    get_tool_by_slug,
    increment_tool_access,
    init_db,
    list_categories,
    list_tools,
    update_category,
    update_tool,
)


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "static" / "uploads" / "tool_images"
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

if load_dotenv:
    load_dotenv(BASE_DIR / ".env")

LOGIN_ATTEMPTS = {}
MAX_LOGIN_ATTEMPTS = int(os.environ.get("MAX_LOGIN_ATTEMPTS", "5"))
LOGIN_WINDOW_SECONDS = int(os.environ.get("LOGIN_WINDOW_SECONDS", "900"))


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", secrets.token_hex(32))
    app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_UPLOAD_MB", "12")) * 1024 * 1024
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = os.environ.get("FORCE_HTTPS", "0") == "1"

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    init_db()

    @app.context_processor
    def inject_globals():
        return {
            "csrf_token": csrf_token,
            "site_name": "Confira Outras Ferramentas Desenvolvidas por Mim",
        }

    @app.before_request
    def validate_csrf():
        if request.method != "POST":
            return
        expected = session.get("_csrf_token")
        received = request.form.get("csrf_token") or request.headers.get("X-CSRFToken")
        if not expected or not secrets.compare_digest(expected, received or ""):
            abort(400)

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' https://unpkg.com; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; "
            "font-src 'self' data:; connect-src 'self'; frame-ancestors 'none';"
        )
        return response

    @app.route("/")
    def index():
        categories = list_categories()
        tools = list_tools(include_hidden=False)
        return render_template("index.html", tools=tools, categories=categories, stats=get_dashboard_stats())

    @app.route("/ferramenta/<slug>")
    def tool_detail(slug):
        tool = get_tool_by_slug(slug, include_hidden=False)
        if not tool:
            abort(404)
        increment_tool_access(tool["id"])
        related = [
            item
            for item in list_tools(include_hidden=False)
            if item["category_id"] == tool["category_id"] and item["id"] != tool["id"]
        ][:3]
        return render_template("tool_detail.html", tool=tool, related=related)

    @app.route("/admin", methods=["GET", "POST"])
    def admin_login():
        if is_logged_in():
            return redirect(url_for("admin_dashboard"))
        if request.method == "POST":
            ip_address = request.headers.get("X-Forwarded-For", request.remote_addr or "local").split(",")[0].strip()
            if is_rate_limited(ip_address):
                flash("Muitas tentativas. Aguarde alguns minutos antes de tentar novamente.", "danger")
                return render_template("admin/login.html"), 429
            username = (request.form.get("username") or "").strip()
            password = request.form.get("password") or ""
            admin = get_admin_by_username(username)
            if admin and check_password_hash(admin["password_hash"], password):
                LOGIN_ATTEMPTS.pop(ip_address, None)
                session.clear()
                session["admin_id"] = admin["id"]
                session["admin_username"] = admin["username"]
                session["_csrf_token"] = secrets.token_urlsafe(32)
                flash("Login realizado com sucesso.", "success")
                return redirect(url_for("admin_dashboard"))
            record_failed_login(ip_address)
            flash("Usuário ou senha inválidos.", "danger")
        return render_template("admin/login.html")

    @app.route("/admin/logout", methods=["POST"])
    @login_required
    def admin_logout():
        session.clear()
        flash("Você saiu da área administrativa.", "success")
        return redirect(url_for("admin_login"))

    @app.route("/admin/dashboard")
    @login_required
    def admin_dashboard():
        return render_template("admin/dashboard.html", stats=get_dashboard_stats(), tools=list_tools(include_hidden=True), categories=list_categories())

    @app.route("/admin/ferramentas/nova", methods=["GET", "POST"])
    @login_required
    def admin_tool_new():
        categories = list_categories()
        if request.method == "POST":
            payload = tool_payload_from_request()
            if not payload["name"] or not payload["short_description"] or not payload["full_description"]:
                flash("Preencha nome, descrição curta e descrição completa.", "warning")
                return render_template("admin/tool_form.html", tool=None, categories=categories), 422
            image_path = save_uploaded_image(request.files.get("image_file"))
            if image_path:
                payload["image_url"] = image_path
            create_tool(payload)
            flash("Ferramenta adicionada com sucesso.", "success")
            return redirect(url_for("admin_dashboard"))
        return render_template("admin/tool_form.html", tool=None, categories=categories)

    @app.route("/admin/ferramentas/<int:tool_id>/editar", methods=["GET", "POST"])
    @login_required
    def admin_tool_edit(tool_id):
        tool = get_tool(tool_id, include_hidden=True)
        if not tool:
            abort(404)
        categories = list_categories()
        if request.method == "POST":
            payload = tool_payload_from_request()
            if not payload["name"] or not payload["short_description"] or not payload["full_description"]:
                flash("Preencha nome, descrição curta e descrição completa.", "warning")
                return render_template("admin/tool_form.html", tool=tool, categories=categories), 422
            image_path = save_uploaded_image(request.files.get("image_file"))
            if image_path:
                payload["image_url"] = image_path
            elif not payload.get("image_url"):
                payload["image_url"] = tool.get("image_url", "")
            update_tool(tool_id, payload)
            flash("Ferramenta atualizada com sucesso.", "success")
            return redirect(url_for("admin_dashboard"))
        return render_template("admin/tool_form.html", tool=tool, categories=categories)

    @app.route("/admin/ferramentas/<int:tool_id>/excluir", methods=["POST"])
    @login_required
    def admin_tool_delete(tool_id):
        delete_tool(tool_id)
        flash("Ferramenta excluída.", "success")
        return redirect(url_for("admin_dashboard"))

    @app.route("/admin/ferramentas/<int:tool_id>/duplicar", methods=["POST"])
    @login_required
    def admin_tool_duplicate(tool_id):
        new_id = duplicate_tool(tool_id)
        if not new_id:
            abort(404)
        flash("Ferramenta duplicada para edição rápida.", "success")
        return redirect(url_for("admin_tool_edit", tool_id=new_id))

    @app.route("/admin/categorias", methods=["GET", "POST"])
    @login_required
    def admin_categories():
        if request.method == "POST":
            name = (request.form.get("name") or "").strip()
            if name:
                create_category(name=name, color=(request.form.get("color") or "#35d0ff").strip(), sort_order=to_int(request.form.get("sort_order"), 0))
                flash("Categoria criada.", "success")
            else:
                flash("Informe o nome da categoria.", "warning")
            return redirect(url_for("admin_categories"))
        return render_template("admin/categories.html", categories=list_categories())

    @app.route("/admin/categorias/<int:category_id>/editar", methods=["POST"])
    @login_required
    def admin_category_edit(category_id):
        if not get_category(category_id):
            abort(404)
        name = (request.form.get("name") or "").strip()
        if name:
            update_category(category_id, name=name, color=(request.form.get("color") or "#35d0ff").strip(), sort_order=to_int(request.form.get("sort_order"), 0))
            flash("Categoria atualizada.", "success")
        else:
            flash("Informe o nome da categoria.", "warning")
        return redirect(url_for("admin_categories"))

    @app.route("/admin/categorias/<int:category_id>/excluir", methods=["POST"])
    @login_required
    def admin_category_delete(category_id):
        if delete_category(category_id):
            flash("Categoria excluída.", "success")
        else:
            flash("Não é possível excluir uma categoria que ainda possui ferramentas.", "warning")
        return redirect(url_for("admin_categories"))

    @app.errorhandler(400)
    def bad_request(error):
        return render_template("error.html", code=400, title="Solicitação inválida", message="Atualize a página e tente novamente."), 400

    @app.errorhandler(404)
    def not_found(error):
        return render_template("error.html", code=404, title="Página não encontrada", message="O endereço solicitado não existe."), 404

    @app.errorhandler(413)
    def file_too_large(error):
        return render_template("error.html", code=413, title="Arquivo muito grande", message="Envie uma imagem menor."), 413

    @app.errorhandler(500)
    def server_error(error):
        return render_template("error.html", code=500, title="Erro interno", message="Tente novamente em instantes."), 500

    return app


def csrf_token():
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


def is_logged_in():
    return bool(session.get("admin_id"))


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not is_logged_in():
            flash("Entre para acessar a área administrativa.", "warning")
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapped


def is_rate_limited(ip_address):
    now_value = time.time()
    attempts = [stamp for stamp in LOGIN_ATTEMPTS.get(ip_address, []) if now_value - stamp < LOGIN_WINDOW_SECONDS]
    LOGIN_ATTEMPTS[ip_address] = attempts
    return len(attempts) >= MAX_LOGIN_ATTEMPTS


def record_failed_login(ip_address):
    LOGIN_ATTEMPTS.setdefault(ip_address, []).append(time.time())


def to_int(value, fallback=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def to_bool(name):
    return request.form.get(name) == "on"


def split_lines(value):
    return [item.strip() for item in (value or "").replace(";", "\n").splitlines() if item.strip()]


def split_tags(value):
    return [item.strip() for item in (value or "").replace(";", ",").replace("\n", ",").split(",") if item.strip()]


def tool_payload_from_request():
    return {
        "name": (request.form.get("name") or "").strip(),
        "short_description": (request.form.get("short_description") or "").strip(),
        "full_description": (request.form.get("full_description") or "").strip(),
        "category_id": to_int(request.form.get("category_id"), None),
        "tags": split_tags(request.form.get("tags")),
        "features": split_lines(request.form.get("features")),
        "screenshots": split_lines(request.form.get("screenshots")),
        "image_url": (request.form.get("image_url") or "").strip(),
        "link": (request.form.get("link") or "").strip(),
        "version": (request.form.get("version") or "1.0").strip(),
        "status": (request.form.get("status") or "Ativo").strip(),
        "card_color": (request.form.get("card_color") or "#35d0ff").strip(),
        "featured": to_bool("featured"),
        "is_new": to_bool("is_new"),
        "is_beta": to_bool("is_beta"),
        "hidden": to_bool("hidden"),
        "sort_order": to_int(request.form.get("sort_order"), 0),
    }


def save_uploaded_image(uploaded):
    if not uploaded or not uploaded.filename:
        return ""
    extension = uploaded.filename.rsplit(".", 1)[-1].lower() if "." in uploaded.filename else ""
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        flash("Imagem ignorada: formato não permitido.", "warning")
        return ""
    safe_name = secure_filename(uploaded.filename) or f"ferramenta.{extension}"
    filename = f"{int(time.time())}_{secrets.token_hex(5)}_{safe_name}"
    destination = UPLOAD_DIR / filename
    uploaded.save(destination)
    return f"/static/uploads/tool_images/{filename}"


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("FLASK_DEBUG") == "1")
