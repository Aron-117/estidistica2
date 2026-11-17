"""Planificador web de estudio ejecutado con la biblioteca estándar de Python.

Inicia la aplicación con ``python pg1.py`` y abre http://127.0.0.1:8000.
"""

from __future__ import annotations

import html
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from uuid import uuid4


HOST = "127.0.0.1"
PORT = 8000
DATA_FILE = Path(__file__).with_name("tareas_estudio.json")
MAX_FORM_BYTES = 8_192
SUBJECTS = ("Matemáticas", "Programación", "Lectura", "Otro")
PRIORITIES = ("Baja", "Media", "Alta")
FOCUS_MINUTES = (15, 25, 45, 60)


def load_tasks() -> list[dict[str, object]]:
    """Carga las tareas guardadas o devuelve una lista vacía la primera vez."""
    if not DATA_FILE.exists():
        return []

    tasks = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    if not isinstance(tasks, list):
        raise ValueError("El archivo de tareas debe contener una lista.")

    for task in tasks:
        if (
            not isinstance(task, dict)
            or not isinstance(task.get("id"), str)
            or not isinstance(task.get("title"), str)
            or task.get("subject") not in SUBJECTS
            or task.get("priority") not in PRIORITIES
            or task.get("minutes") not in FOCUS_MINUTES
            or type(task.get("done")) is not bool
        ):
            raise ValueError("Una tarea guardada tiene un formato no válido.")
    return tasks


def save_tasks(tasks: list[dict[str, object]]) -> None:
    """Guarda la lista de tareas en formato JSON legible."""
    DATA_FILE.write_text(
        json.dumps(tasks, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def render_page(tasks: list[dict[str, object]], selected_filter: str) -> str:
    """Construye la página HTML con formulario, filtros y resumen."""
    completed = sum(task["done"] is True for task in tasks)
    remaining = len(tasks) - completed
    progress = round(completed / len(tasks) * 100) if tasks else 0

    visible_tasks = [
        task
        for task in tasks
        if selected_filter == "todas"
        or (selected_filter == "pendientes" and task["done"] is False)
        or (selected_filter == "completadas" and task["done"] is True)
    ]

    task_cards = []
    for task in visible_tasks:
        task_id = html.escape(str(task["id"]), quote=True)
        title = html.escape(str(task["title"]), quote=True)
        subject = html.escape(str(task["subject"]))
        priority = html.escape(str(task["priority"]))
        is_done = task["done"] is True
        state_class = " task-done" if is_done else ""
        checked_label = "Reabrir tarea" if is_done else "Completar tarea"
        task_cards.append(
            f"""
            <article class="task-card{state_class}">
              <form action="/toggle" method="post">
                <input type="hidden" name="id" value="{task_id}">
                <button class="check-button" type="submit"
                        aria-label="{checked_label}">{'✓' if is_done else ''}</button>
              </form>
              <div class="task-copy">
                <h3>{title}</h3>
                <p>{subject} <span>·</span> {task["minutes"]} min</p>
              </div>
              <span class="priority priority-{priority.lower()}">{priority}</span>
              <form action="/delete" method="post">
                <input type="hidden" name="id" value="{task_id}">
                <button class="delete-button" type="submit" aria-label="Eliminar {title}">×</button>
              </form>
            </article>
            """
        )

    if not task_cards:
        empty_message = (
            "No hay tareas en este filtro. ¡Agrega una para empezar!"
            if not tasks
            else "No hay tareas que mostrar en este filtro."
        )
        task_content = f'<div class="empty-state"><span>✦</span><p>{empty_message}</p></div>'
    else:
        task_content = "\n".join(task_cards)

    filters = (("todas", "Todas"), ("pendientes", "Pendientes"), ("completadas", "Completadas"))
    filter_links = "\n".join(
        f'<a class="filter{" active" if selected_filter == value else ""}" '
        f'href="/?estado={value}">{label}</a>'
        for value, label in filters
    )

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Enfoque — Planificador de estudio</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #202b3c;
      --muted: #788396;
      --paper: #fff;
      --canvas: #f5f7fb;
      --purple: #6c63e8;
      --line: #e9ecf3;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--canvas);
      color: var(--ink);
      font: 16px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif;
    }}
    button, input, select {{ font: inherit; }}
    .topbar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      max-width: 1080px;
      margin: auto;
      padding: 22px 24px;
    }}
    .brand {{ display: flex; align-items: center; gap: 10px; font-weight: 800; }}
    .brand-mark {{
      display: grid;
      width: 36px;
      height: 36px;
      place-items: center;
      border-radius: 12px;
      background: var(--purple);
      color: white;
    }}
    .today {{ color: var(--muted); font-size: .9rem; }}
    main {{ max-width: 1080px; margin: 25px auto 70px; padding: 0 24px; }}
    .welcome {{ margin-bottom: 24px; }}
    .eyebrow {{ color: var(--purple); font-size: .78rem; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }}
    h1 {{ margin: 5px 0 4px; font-size: clamp(1.7rem, 4vw, 2.35rem); letter-spacing: -.04em; }}
    .subtitle {{ margin: 0; color: var(--muted); }}
    .dashboard {{ display: grid; grid-template-columns: 1.55fr 1fr; gap: 20px; }}
    .panel, .stat-card {{ border: 1px solid var(--line); border-radius: 18px; background: var(--paper); }}
    .panel {{ padding: 24px; }}
    .panel-heading {{ display: flex; align-items: center; justify-content: space-between; gap: 12px; }}
    h2 {{ margin: 0; font-size: 1.15rem; }}
    .task-count {{ color: var(--muted); font-size: .88rem; }}
    .filters {{ display: flex; gap: 7px; margin: 18px 0; }}
    .filter {{ padding: 7px 12px; border-radius: 9px; color: var(--muted); font-size: .87rem; text-decoration: none; }}
    .filter.active {{ background: #eeedff; color: var(--purple); font-weight: 700; }}
    .task-list {{ display: grid; gap: 10px; }}
    .task-card {{ display: flex; align-items: center; gap: 12px; padding: 13px; border: 1px solid var(--line); border-radius: 13px; }}
    .task-copy {{ min-width: 0; flex: 1; }}
    .task-copy h3 {{ overflow-wrap: anywhere; margin: 0; font-size: .95rem; }}
    .task-copy p {{ margin: 3px 0 0; color: var(--muted); font-size: .81rem; }}
    .task-copy p span {{ padding: 0 4px; }}
    .task-done .task-copy h3 {{ color: #929aaa; text-decoration: line-through; }}
    .check-button {{
      width: 25px;
      height: 25px;
      border: 1.5px solid #cbd1dd;
      border-radius: 8px;
      background: white;
      color: white;
      cursor: pointer;
    }}
    .task-done .check-button {{ border-color: var(--purple); background: var(--purple); }}
    .priority {{ padding: 4px 8px; border-radius: 7px; font-size: .73rem; font-weight: 700; }}
    .priority-baja {{ background: #e8f7ef; color: #31845a; }}
    .priority-media {{ background: #fff5df; color: #a76b08; }}
    .priority-alta {{ background: #ffebeb; color: #c34e4e; }}
    .delete-button {{ border: 0; background: transparent; color: #a0a8b5; cursor: pointer; font-size: 1.3rem; }}
    .delete-button:hover {{ color: #c34e4e; }}
    .empty-state {{ padding: 35px 10px; color: var(--muted); text-align: center; }}
    .empty-state span {{ color: #f0b848; font-size: 1.6rem; }}
    .empty-state p {{ margin: 5px 0 0; }}
    .side-column {{ display: grid; align-content: start; gap: 16px; }}
    .stats {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }}
    .stat-card {{ padding: 17px; }}
    .stat-number {{ display: block; font-size: 1.65rem; font-weight: 800; letter-spacing: -.04em; }}
    .stat-label {{ color: var(--muted); font-size: .81rem; }}
    .progress-panel {{ padding: 19px; }}
    .progress-row {{ display: flex; justify-content: space-between; gap: 10px; font-size: .9rem; font-weight: 700; }}
    .progress-row span:last-child {{ color: var(--purple); }}
    .progress-track {{ height: 9px; margin-top: 13px; overflow: hidden; border-radius: 9px; background: #eeeff5; }}
    .progress-fill {{ width: {progress}%; height: 100%; border-radius: inherit; background: linear-gradient(90deg, #897cf2, #5d62df); }}
    .add-panel {{ padding: 21px; }}
    .add-panel h2 {{ margin-bottom: 15px; }}
    .field {{ display: grid; gap: 6px; margin-top: 11px; }}
    .field label {{ font-size: .81rem; font-weight: 700; }}
    .field input, .field select {{ width: 100%; padding: 10px 11px; border: 1px solid var(--line); border-radius: 9px; background: white; color: var(--ink); }}
    .field input:focus, .field select:focus {{ outline: 2px solid #d6d3ff; border-color: var(--purple); }}
    .form-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
    .submit-button {{ width: 100%; margin-top: 16px; padding: 11px; border: 0; border-radius: 10px; background: var(--purple); color: white; cursor: pointer; font-weight: 750; }}
    .submit-button:hover {{ background: #5b52d4; }}
    .tip {{ padding: 15px 17px; border-radius: 14px; background: #eeedff; color: #514bb1; font-size: .85rem; }}
    .tip strong {{ display: block; margin-bottom: 3px; }}
    @media (max-width: 760px) {{
      main {{ margin-top: 10px; }}
      .dashboard {{ grid-template-columns: 1fr; }}
      .side-column {{ grid-row: 1; }}
      .topbar {{ padding: 17px 20px; }}
    }}
    @media (max-width: 430px) {{
      main {{ padding: 0 14px; }}
      .panel {{ padding: 17px; }}
      .priority {{ display: none; }}
      .today {{ font-size: .78rem; }}
    }}
  </style>
</head>
<body>
  <header class="topbar">
    <div class="brand"><span class="brand-mark">✦</span> enfoque</div>
    <span class="today">Tu espacio para aprender mejor</span>
  </header>
  <main>
    <section class="welcome">
      <span class="eyebrow">Planificador personal</span>
      <h1>Hola, ¡a concentrarse!</h1>
      <p class="subtitle">Organiza tus tareas y avanza a tu propio ritmo.</p>
    </section>
    <div class="dashboard">
      <section class="panel">
        <div class="panel-heading">
          <h2>Mis tareas</h2>
          <span class="task-count">{len(tasks)} en total</span>
        </div>
        <nav class="filters" aria-label="Filtrar tareas">{filter_links}</nav>
        <div class="task-list">{task_content}</div>
      </section>
      <aside class="side-column">
        <div class="stats">
          <div class="stat-card"><span class="stat-number">{remaining}</span><span class="stat-label">Por hacer</span></div>
          <div class="stat-card"><span class="stat-number">{completed}</span><span class="stat-label">Completadas</span></div>
        </div>
        <section class="panel progress-panel">
          <div class="progress-row"><span>Progreso del día</span><span>{progress}%</span></div>
          <div class="progress-track" role="progressbar" aria-label="Progreso de tareas"
               aria-valuenow="{progress}" aria-valuemin="0" aria-valuemax="100">
            <div class="progress-fill"></div>
          </div>
        </section>
        <section class="panel add-panel">
          <h2>Agregar una tarea</h2>
          <form action="/add" method="post">
            <div class="field">
              <label for="title">¿Qué vas a estudiar?</label>
              <input id="title" name="title" type="text" maxlength="90"
                     placeholder="Ej. Repasar integrales" required>
            </div>
            <div class="form-row">
              <div class="field">
                <label for="subject">Materia</label>
                <select id="subject" name="subject">
                  {''.join(f'<option>{html.escape(subject)}</option>' for subject in SUBJECTS)}
                </select>
              </div>
              <div class="field">
                <label for="priority">Prioridad</label>
                <select id="priority" name="priority">
                  {''.join(f'<option>{priority}</option>' for priority in PRIORITIES)}
                </select>
              </div>
            </div>
            <div class="field">
              <label for="minutes">Tiempo de enfoque</label>
              <select id="minutes" name="minutes">
                {''.join(f'<option value="{minute}">{minute} minutos</option>' for minute in FOCUS_MINUTES)}
              </select>
            </div>
            <button class="submit-button" type="submit">＋ Añadir a mi lista</button>
          </form>
        </section>
        <div class="tip"><strong>Un consejo</strong>Divide una tarea grande en sesiones cortas y celebra cada avance.</div>
      </aside>
    </div>
  </main>
</body>
</html>"""


class StudyPlannerHandler(BaseHTTPRequestHandler):
    """Maneja las páginas y acciones del planificador."""

    def send_html(self, body: str, status: int = 200) -> None:
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def show_error(self, message: str, status: int) -> None:
        safe_message = html.escape(message)
        self.send_html(
            f"""<!doctype html><html lang="es"><meta charset="utf-8">
            <title>Error — Enfoque</title><body style="font:16px system-ui;max-width:600px;margin:4rem auto;padding:1rem">
            <h1>No se pudo completar la acción</h1><p>{safe_message}</p>
            <a href="/">Volver al planificador</a></body></html>""",
            status,
        )

    def read_form(self) -> dict[str, list[str]]:
        length = int(self.headers.get("Content-Length", "0"))
        if length < 0:
            raise ValueError("El formulario no es válido.")
        if length > MAX_FORM_BYTES:
            raise OverflowError
        raw_body = self.rfile.read(length).decode("utf-8")
        return parse_qs(raw_body, keep_blank_values=True)

    @staticmethod
    def form_value(form: dict[str, list[str]], name: str) -> str:
        values = form.get(name, [])
        return values[0] if values else ""

    def do_GET(self) -> None:
        parsed_url = urlparse(self.path)
        if parsed_url.path != "/":
            self.show_error("La página solicitada no existe.", 404)
            return

        selected_filter = parse_qs(parsed_url.query).get("estado", ["todas"])[0]
        if selected_filter not in ("todas", "pendientes", "completadas"):
            selected_filter = "todas"

        try:
            tasks = load_tasks()
        except (OSError, json.JSONDecodeError, ValueError) as error:
            self.show_error(f"No se pudieron leer las tareas: {error}", 500)
            return
        self.send_html(render_page(tasks, selected_filter))

    def do_POST(self) -> None:
        route = urlparse(self.path).path
        if route not in ("/add", "/toggle", "/delete"):
            self.show_error("La acción solicitada no existe.", 404)
            return

        try:
            form = self.read_form()
        except OverflowError:
            self.show_error("El formulario es demasiado grande.", 413)
            return
        except (UnicodeDecodeError, ValueError):
            self.show_error("Los datos del formulario no son válidos.", 400)
            return

        try:
            tasks = load_tasks()
        except (OSError, json.JSONDecodeError, ValueError) as error:
            self.show_error(f"No se pudieron leer las tareas: {error}", 500)
            return

        if route == "/add":
            title = self.form_value(form, "title").strip()
            subject = self.form_value(form, "subject")
            priority = self.form_value(form, "priority")
            minutes_text = self.form_value(form, "minutes")
            if not title or len(title) > 90:
                self.show_error("Escribe un título de entre 1 y 90 caracteres.", 400)
                return
            if subject not in SUBJECTS or priority not in PRIORITIES:
                self.show_error("Selecciona una materia y una prioridad válidas.", 400)
                return
            try:
                minutes = int(minutes_text)
            except ValueError:
                self.show_error("Selecciona un tiempo de enfoque válido.", 400)
                return
            if minutes not in FOCUS_MINUTES:
                self.show_error("Selecciona un tiempo de enfoque válido.", 400)
                return
            tasks.append(
                {
                    "id": uuid4().hex,
                    "title": title,
                    "subject": subject,
                    "priority": priority,
                    "minutes": minutes,
                    "done": False,
                }
            )
        else:
            task_id = self.form_value(form, "id")
            task = next((item for item in tasks if item["id"] == task_id), None)
            if task is None:
                self.show_error("La tarea ya no existe o su identificador no es válido.", 404)
                return
            if route == "/toggle":
                task["done"] = not task["done"]
            else:
                tasks.remove(task)

        try:
            save_tasks(tasks)
        except OSError as error:
            self.show_error(f"No se pudieron guardar las tareas: {error}", 500)
            return

        self.send_response(303)
        self.send_header("Location", "/")
        self.end_headers()

    def log_message(self, format_string: str, *args: object) -> None:
        print(f"[{self.log_date_time_string()}] {format_string % args}")


if __name__ == "__main__":
    print(f"Planificador listo en http://{HOST}:{PORT} (Ctrl+C para detener)")
    HTTPServer((HOST, PORT), StudyPlannerHandler).serve_forever()
    #pueden agreagar mas cosas