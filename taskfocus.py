# TaskFocus — Dark GUI Task Manager (Dark Mode, Purple Accent)
# -----------------------------------------------------------
# Features (v1.0):
#   • Dark GUI built with CustomTkinter (purple accent theme)
#   • Persistent JSON storage at C:\\Users\\Public\\Documents\\tasks.json
#   • Tabs: Today, All Tasks, Add Task, Bulk Import
#   • "Today" shows tasks that can be started (start_date <= today), sorted by
#       Priority (High→Medium→Low), Deadline (soonest first), Start Date
#   • New-day focus dialog: choose which tasks to focus on today (⭐)
#   • Edit and mark as done manually; toggle Focus status
#   • Scrollable task lists
#   • tkcalendar DateEntry for Start Date / Deadline pickers
#
# Usage:
#   pip install customtkinter tkcalendar
#   python taskfocus.py
#
# Notes:
#   • All comments and strings are in English, as requested.
#   • You can customize defaults in the CONFIG section.

import itertools
import json
import os
import sys
import re
import math
from datetime import datetime, date, timedelta

import webbrowser
from collections import defaultdict
from urllib.parse import urlparse

import tkinter as tk
from tkinter import messagebox

try:
    import customtkinter as ctk
except ImportError:
    print("Please install customtkinter: pip install customtkinter")
    raise

try:
    from tkcalendar import DateEntry
except ImportError:
    print("Please install tkcalendar: pip install tkcalendar")
    raise

try:
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None
    FigureCanvasTkAgg = None

try:
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None
    FigureCanvasTkAgg = None

try:
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None
    FigureCanvasTkAgg = None

try:
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None
    FigureCanvasTkAgg = None

# -------------------------------
# CONFIG
# -------------------------------
DATA_DIR = r"C:\\Users\\Public\\Documents"  # persistent location
DATA_FILE = os.path.join(DATA_DIR, "tasks.json")
THEME_FILE = os.path.join(DATA_DIR, "taskfocus_purple_theme.json")
APP_TITLE = "TaskFocus"

TASK_TYPES = ["Make", "Ask", "Arrange", "Control"]
PRIORITIES = ["High", "Medium", "Low"]
STATUSES = ["open", "done"]

# -------------------------------
# Helpers
# -------------------------------

def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)


def write_purple_theme_if_missing():
    """Create a minimal CustomTkinter theme JSON with purple accent."""
    if os.path.exists(THEME_FILE):
        return
    theme = {
        "_name": "taskfocus-purple",
        "CTk": {
            "fg_color": ["#1F1F1F", "#1F1F1F"],
            "top_fg_color": ["#1A1A1A", "#1A1A1A"],
            "text_color": ["#111111", "#F1F1F1"],
            "text_color_disabled": ["#8A8A8A", "#6D6D6D"],
            "scaling": 1.0,
            "corner_radius": 12
        },
        "CTkButton": {
            "corner_radius": 10,
            "border_width": 0,
            "fg_color": ["#8B5CF6", "#6D28D9"],
            "hover_color": ["#7C3AED", "#5B21B6"],
            "text_color": ["#FFFFFF", "#FFFFFF"],
            "text_color_disabled": ["#8A8A8A", "#6D6D6D"]
        },
        "CTkFrame": {
            "corner_radius": 16,
            "border_width": 0,
            "fg_color": ["#262626", "#262626"],
            "top_fg_color": ["#1F1F1F", "#1F1F1F"]
        },
        "CTkEntry": {
            "corner_radius": 8,
            "border_width": 0,
            "fg_color": ["#2C2C2C", "#2C2C2C"],
            "border_color": ["#3F3F46", "#3F3F46"],
            "text_color": ["#E5E7EB", "#E5E7EB"],
            "placeholder_text_color": ["#9CA3AF", "#9CA3AF"]
        },
        "CTkOptionMenu": {
            "corner_radius": 8,
            "fg_color": ["#3B3B3B", "#3B3B3B"],
            "button_color": ["#8B5CF6", "#6D28D9"],
            "button_hover_color": ["#7C3AED", "#5B21B6"],
            "text_color": ["#E5E7EB", "#E5E7EB"],
            "dropdown_color": ["#2C2C2C", "#2C2C2C"],
            "dropdown_text_color": ["#E5E7EB", "#E5E7EB"]
        },
        "CTkScrollableFrame": {
            "label_text_color": ["#E5E7EB", "#E5E7EB"],
            "fg_color": ["#1F1F1F", "#1F1F1F"],
            "top_fg_color": ["#1F1F1F", "#1F1F1F"]
        },
        "CTkLabel": {
            "text_color": ["#E5E7EB", "#E5E7EB"]
        },
        "CTkCheckBox": {
            "border_color": ["#8B5CF6", "#6D28D9"],
            "fg_color": ["#8B5CF6", "#6D28D9"],
            "hover_color": ["#7C3AED", "#5B21B6"],
            "text_color": ["#E5E7EB", "#E5E7EB"]
        }
    }
    with open(THEME_FILE, "w", encoding="utf-8") as f:
        json.dump(theme, f, indent=2)


def parse_date(s: str):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        try:
            return datetime.strptime(s, "%d.%m.%Y").date()  # alternative format
        except ValueError:
            return None


def today_str():
    return date.today().strftime("%Y-%m-%d")


PRIORITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}


def sort_key(task: dict):
    pr = PRIORITY_ORDER.get(task.get("priority", "Medium"), 1)
    # Missing/invalid deadlines go to the end
    dl = parse_date(task.get("deadline", "")) or date(9999, 12, 31)
    sd = parse_date(task.get("start_date", "")) or date(9999, 12, 31)
    created = None
    try:
        created = datetime.fromisoformat(task.get("created_at", ""))
    except Exception:
        created = datetime(2099, 1, 1)
    return (pr, dl, sd, created)


def create_dark_date_entry(master) -> DateEntry:
    """Return a DateEntry that matches the dark UI theme."""
    entry = DateEntry(
        master,
        date_pattern='yyyy-mm-dd',
        font=("Segoe UI", 14),
        background="#1E1B4B",
        foreground="#E5E7EB",
        borderwidth=0,
        width=16,
        selectbackground="#8B5CF6",
        selectforeground="#F9FAFB",
        fieldbackground="#111827",
        normalbackground="#1E1B4B",
        normalforeground="#F9FAFB",
        headersbackground="#312E81",
        headersforeground="#E5E7EB",
    )
    try:
        entry.configure(
            insertbackground="#F9FAFB",
            disabledbackground="#1F2937",
            disabledforeground="#6B7280",
        )
    except (tk.TclError, AttributeError):
        # Some tkcalendar builds forward unknown options to the popup Calendar
        # widget, which does not accept these entry-specific attributes. Fail
        # quietly so the dark styling still applies wherever supported.
        pass
    try:
        cal = entry._top_cal  # type: ignore[attr-defined]
        cal.configure(
            background="#111827",
            foreground="#F9FAFB",
            selectbackground="#8B5CF6",
            selectforeground="#F9FAFB",
            headersbackground="#312E81",
            headersforeground="#E5E7EB",
            weekendbackground="#1E1B4B",
            weekendforeground="#F3F4F6",
            othermonthbackground="#111827",
            othermonthforeground="#6B7280",
            disableddaybackground="#1F2937",
            disableddayforeground="#6B7280",
        )
        try:
            cal.configure(font=("Segoe UI", 12))
        except tk.TclError:
            pass
    except Exception:
        # Fallback quietly if tkcalendar internals change.
        pass
    return entry


URL_REGEX = re.compile(r'https?://[^\s<>"\']+')
TRAILING_URL_CHARS = ")]},.;'\":>"


def _normalize_url(raw: str) -> str | None:
    url = raw.strip()
    while url and url[-1] in TRAILING_URL_CHARS:
        url = url[:-1]
    if not url:
        return None
    if url.startswith("www."):
        url = "https://" + url
    if not url.lower().startswith(("http://", "https://")):
        return None
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return None
    return url


def gather_task_links(task: dict) -> list[str]:
    texts = [task.get("description", "")]
    for session in task.get("sessions", []):
        texts.append(session.get("note", ""))
    seen: set[str] = set()
    links: list[str] = []
    for text in texts:
        if not text:
            continue
        for match in URL_REGEX.findall(text):
            url = _normalize_url(match)
            if url and url.lower() not in seen:
                seen.add(url.lower())
                links.append(url)
    return links


def parse_session_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def iso_to_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except Exception:
        return None


def make_textbox_copyable(textbox: ctk.CTkTextbox):
    textbox.configure(state="disabled", wrap="word")

    def enable():
        textbox.configure(state="normal")

    def disable():
        textbox.configure(state="disabled")

    def copy_selection() -> None:
        enable()
        try:
            text = textbox.get("sel.first", "sel.last")
        except tk.TclError:
            text = ""
        if text:
            textbox.clipboard_clear()
            textbox.clipboard_append(text)
        textbox.after_idle(disable)

    def select_all():
        enable()
        textbox.tag_add("sel", "1.0", "end-1c")
        textbox.after_idle(disable)

    def block_edit(event):
        modifiers = event.state
        if modifiers & (0x4 | 0x20000 | 0x100000):  # Control or Command
            key = event.keysym.lower()
            if key == "c":
                copy_selection()
            elif key == "a":
                select_all()
        return "break"

    def on_mouse_down(_event):
        enable()

    def on_mouse_up(_event):
        textbox.after_idle(disable)

    def show_menu(event):
        enable()
        menu = tk.Menu(textbox, tearoff=0)
        menu.add_command(label="Copy", command=copy_selection)
        menu.add_command(label="Select All", command=select_all)
        try:
            menu.tk_popup(event.x_root, event.y_root)
            menu.grab_release()
        finally:
            textbox.after_idle(disable)
        return "break"

    def on_copy(_event=None):
        copy_selection()
        return "break"

    def on_select_all(_event=None):
        select_all()
        return "break"

    textbox.bind("<Key>", block_edit)
    textbox.bind("<Button-1>", on_mouse_down)
    textbox.bind("<B1-Motion>", lambda _event: None)
    textbox.bind("<ButtonRelease-1>", on_mouse_up)
    textbox.bind("<FocusOut>", lambda _event: disable())
    textbox.bind("<Control-c>", on_copy)
    textbox.bind("<Control-a>", on_select_all)
    textbox.bind("<Command-c>", on_copy)
    textbox.bind("<Command-a>", on_select_all)
    textbox.bind("<Button-3>", show_menu)
    textbox.bind("<Button-2>", show_menu)


def shorten_url_display(url: str, max_length: int = 36) -> str:
    parsed = urlparse(url)
    display = url
    if parsed.netloc:
        display = parsed.netloc + parsed.path
    if len(display) > max_length:
        return display[: max_length - 1] + "…"
    return display


def parse_minutes_input(raw: str) -> int:
    """Parse flexible minute input supporting m, h, and H:MM formats."""
    if raw is None:
        raise ValueError("No time entered")
    value = raw.strip().lower().replace(" ", "")
    if not value:
        raise ValueError("No time entered")

    try:
        if ":" in value:
            hours_str, mins_str = value.split(":", 1)
            hours = int(hours_str.strip() or 0)
            minutes = int(mins_str.strip() or 0)
            total = hours * 60 + minutes
        elif "h" in value:
            hours_part, minutes_part = value.split("h", 1)
            hours = float(hours_part) if hours_part else 0.0
            minutes_text = minutes_part.replace("m", "") if minutes_part else ""
            minutes = float(minutes_text) if minutes_text else 0.0
            total = int(round(hours * 60 + minutes))
        else:
            suffix = value[-1] if value[-1].isalpha() else ""
            number_part = value[:-1] if suffix else value
            amount = float(number_part)
            if suffix == "h":
                total = int(round(amount * 60))
            else:
                total = int(round(amount))
    except (TypeError, ValueError):
        raise ValueError("Invalid time format") from None

    if total <= 0:
        raise ValueError("Time must be greater than zero")
    return total


# -------------------------------
# Storage
# -------------------------------
class TaskStore:
    def __init__(self, path):
        self.path = path
        self.data = {"tasks": [], "meta": {"last_focus_date": None, "people": []}}
        self.load()

    def load(self):
        ensure_dirs()
        if not os.path.exists(self.path):
            self.save()
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
            # Backward compatibility
            if "meta" not in self.data:
                self.data["meta"] = {"last_focus_date": None, "people": []}
            if "people" not in self.data.get("meta", {}):
                self.data["meta"]["people"] = []
            # Ensure defaults on old tasks
            for task in self.data.get("tasks", []):
                self._ensure_task_defaults(task)
                self.register_people(task.get("who_asked"), task.get("assignee"))
        except Exception:
            # Create fresh if corrupted
            self.data = {"tasks": [], "meta": {"last_focus_date": None, "people": []}}
            self.save()

    def save(self):
        ensure_dirs()
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    # --- Task operations ---
    def _ensure_task_defaults(self, task: dict):
        task.setdefault("description", "")
        task.setdefault("assignee", "")
        task.setdefault("time_spent_minutes", 0)
        task.setdefault("sessions", [])
        task.setdefault("completed_at", None)
        return task

    def _next_id(self) -> int:
        if not self.data["tasks"]:
            return 1
        return max(t.get("id", 0) for t in self.data["tasks"]) + 1

    def add_task(self, task: dict) -> dict:
        task = task.copy()
        task.setdefault("id", self._next_id())
        task.setdefault("type", "Make")
        task.setdefault("priority", "Medium")
        task.setdefault("who_asked", "")
        task.setdefault("start_date", today_str())
        task.setdefault("deadline", "")
        task.setdefault("status", "open")
        task.setdefault("focus", False)
        task.setdefault("created_at", datetime.now().isoformat(timespec="seconds"))
        task.setdefault("completed_at", None)
        self.data["tasks"].append(self._ensure_task_defaults(task))
        self.register_people(task.get("who_asked"), task.get("assignee"))
        self.save()
        return task

    def update_task(self, task_id: int, updates: dict):
        for t in self.data["tasks"]:
            if t.get("id") == task_id:
                t.update(updates)
                self._ensure_task_defaults(t)
                self.register_people(t.get("who_asked"), t.get("assignee"))
                self.save()
                return t
        return None

    def delete_task(self, task_id: int):
        self.data["tasks"] = [t for t in self.data["tasks"] if t.get("id") != task_id]
        self.save()

    def list_tasks(self, status: str | None = None):
        tasks = list(self.data["tasks"])
        if status in STATUSES:
            tasks = [t for t in tasks if t.get("status") == status]
        return tasks

    def register_people(self, *names: str | None):
        names_clean = [n.strip() for n in names if n and n.strip()]
        if not names_clean:
            return
        current = set(self.data.get("meta", {}).get("people", []))
        updated = False
        for name in names_clean:
            if name not in current:
                current.add(name)
                updated = True
        if updated:
            self.data["meta"]["people"] = sorted(current)

    def get_people(self) -> list[str]:
        return list(self.data.get("meta", {}).get("people", []))

    def append_session(self, task_id: int, minutes: int, note: str):
        for t in self.data.get("tasks", []):
            if t.get("id") == task_id:
                self._ensure_task_defaults(t)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                session_entry = {
                    "timestamp": timestamp,
                    "minutes": minutes,
                    "note": note,
                }
                t["sessions"].append(session_entry)
                t["time_spent_minutes"] = int(t.get("time_spent_minutes", 0)) + int(minutes)
                self.save()
                return session_entry
        return None

    def register_people(self, *names: str | None):
        names_clean = [n.strip() for n in names if n and n.strip()]
        if not names_clean:
            return
        current = set(self.data.get("meta", {}).get("people", []))
        updated = False
        for name in names_clean:
            if name not in current:
                current.add(name)
                updated = True
        if updated:
            self.data["meta"]["people"] = sorted(current)

    def get_people(self) -> list[str]:
        return list(self.data.get("meta", {}).get("people", []))

    def append_session(self, task_id: int, minutes: int, note: str):
        for t in self.data.get("tasks", []):
            if t.get("id") == task_id:
                self._ensure_task_defaults(t)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                session_entry = {
                    "timestamp": timestamp,
                    "minutes": minutes,
                    "note": note,
                }
                t["sessions"].append(session_entry)
                t["time_spent_minutes"] = int(t.get("time_spent_minutes", 0)) + int(minutes)
                self.save()
                return session_entry
        return None

    def register_people(self, *names: str | None):
        names_clean = [n.strip() for n in names if n and n.strip()]
        if not names_clean:
            return
        current = set(self.data.get("meta", {}).get("people", []))
        updated = False
        for name in names_clean:
            if name not in current:
                current.add(name)
                updated = True
        if updated:
            self.data["meta"]["people"] = sorted(current)

    def get_people(self) -> list[str]:
        return list(self.data.get("meta", {}).get("people", []))

    def append_session(self, task_id: int, minutes: int, note: str):
        for t in self.data.get("tasks", []):
            if t.get("id") == task_id:
                self._ensure_task_defaults(t)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                session_entry = {
                    "timestamp": timestamp,
                    "minutes": minutes,
                    "note": note,
                }
                t["sessions"].append(session_entry)
                t["time_spent_minutes"] = int(t.get("time_spent_minutes", 0)) + int(minutes)
                self.save()
                return session_entry
        return None

    def register_people(self, *names: str | None):
        names_clean = [n.strip() for n in names if n and n.strip()]
        if not names_clean:
            return
        current = set(self.data.get("meta", {}).get("people", []))
        updated = False
        for name in names_clean:
            if name not in current:
                current.add(name)
                updated = True
        if updated:
            self.data["meta"]["people"] = sorted(current)

    def get_people(self) -> list[str]:
        return list(self.data.get("meta", {}).get("people", []))

    def append_session(self, task_id: int, minutes: int, note: str):
        for t in self.data.get("tasks", []):
            if t.get("id") == task_id:
                self._ensure_task_defaults(t)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                session_entry = {
                    "timestamp": timestamp,
                    "minutes": minutes,
                    "note": note,
                }
                t["sessions"].append(session_entry)
                t["time_spent_minutes"] = int(t.get("time_spent_minutes", 0)) + int(minutes)
                addition = f"[{timestamp}] ({minutes} min)"
                if note:
                    addition += f" {note}"
                existing = t.get("description", "").rstrip()
                if existing:
                    new_desc = existing + "\n" + addition
                else:
                    new_desc = addition
                t["description"] = new_desc
                self.save()
                return session_entry
        return None

    def register_people(self, *names: str | None):
        names_clean = [n.strip() for n in names if n and n.strip()]
        if not names_clean:
            return
        current = set(self.data.get("meta", {}).get("people", []))
        updated = False
        for name in names_clean:
            if name not in current:
                current.add(name)
                updated = True
        if updated:
            self.data["meta"]["people"] = sorted(current)

    def get_people(self) -> list[str]:
        return list(self.data.get("meta", {}).get("people", []))

    def append_session(self, task_id: int, minutes: int, note: str):
        for t in self.data.get("tasks", []):
            if t.get("id") == task_id:
                self._ensure_task_defaults(t)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                session_entry = {
                    "timestamp": timestamp,
                    "minutes": minutes,
                    "note": note,
                }
                t["sessions"].append(session_entry)
                t["time_spent_minutes"] = int(t.get("time_spent_minutes", 0)) + int(minutes)
                addition = f"[{timestamp}] ({minutes} min)"
                if note:
                    addition += f" {note}"
                existing = t.get("description", "").rstrip()
                if existing:
                    new_desc = existing + "\n" + addition
                else:
                    new_desc = addition
                t["description"] = new_desc
                self.save()
                return session_entry
        return None

    def register_people(self, *names: str | None):
        names_clean = [n.strip() for n in names if n and n.strip()]
        if not names_clean:
            return
        current = set(self.data.get("meta", {}).get("people", []))
        updated = False
        for name in names_clean:
            if name not in current:
                current.add(name)
                updated = True
        if updated:
            self.data["meta"]["people"] = sorted(current)

    def get_people(self) -> list[str]:
        return list(self.data.get("meta", {}).get("people", []))

    def append_session(self, task_id: int, minutes: int, note: str):
        for t in self.data.get("tasks", []):
            if t.get("id") == task_id:
                self._ensure_task_defaults(t)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                session_entry = {
                    "timestamp": timestamp,
                    "minutes": minutes,
                    "note": note,
                }
                t["sessions"].append(session_entry)
                t["time_spent_minutes"] = int(t.get("time_spent_minutes", 0)) + int(minutes)
                addition = f"[{timestamp}] ({minutes} min)"
                if note:
                    addition += f" {note}"
                existing = t.get("description", "").rstrip()
                if existing:
                    new_desc = existing + "\n" + addition
                else:
                    new_desc = addition
                t["description"] = new_desc
                self.save()
                return session_entry
        return None

    def register_people(self, *names: str | None):
        names_clean = [n.strip() for n in names if n and n.strip()]
        if not names_clean:
            return
        current = set(self.data.get("meta", {}).get("people", []))
        updated = False
        for name in names_clean:
            if name not in current:
                current.add(name)
                updated = True
        if updated:
            self.data["meta"]["people"] = sorted(current)

    def get_people(self) -> list[str]:
        return list(self.data.get("meta", {}).get("people", []))

    def append_session(self, task_id: int, minutes: int, note: str):
        for t in self.data.get("tasks", []):
            if t.get("id") == task_id:
                self._ensure_task_defaults(t)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                session_entry = {
                    "timestamp": timestamp,
                    "minutes": minutes,
                    "note": note,
                }
                t["sessions"].append(session_entry)
                t["time_spent_minutes"] = int(t.get("time_spent_minutes", 0)) + int(minutes)
                addition = f"[{timestamp}] ({minutes} min)"
                if note:
                    addition += f" {note}"
                existing = t.get("description", "").rstrip()
                if existing:
                    new_desc = existing + "\n" + addition
                else:
                    new_desc = addition
                t["description"] = new_desc
                self.save()
                return session_entry
        return None

    def register_people(self, *names: str | None):
        names_clean = [n.strip() for n in names if n and n.strip()]
        if not names_clean:
            return
        current = set(self.data.get("meta", {}).get("people", []))
        updated = False
        for name in names_clean:
            if name not in current:
                current.add(name)
                updated = True
        if updated:
            self.data["meta"]["people"] = sorted(current)

    def get_people(self) -> list[str]:
        return list(self.data.get("meta", {}).get("people", []))

    def append_session(self, task_id: int, minutes: int, note: str):
        for t in self.data.get("tasks", []):
            if t.get("id") == task_id:
                self._ensure_task_defaults(t)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                session_entry = {
                    "timestamp": timestamp,
                    "minutes": minutes,
                    "note": note,
                }
                t["sessions"].append(session_entry)
                t["time_spent_minutes"] = int(t.get("time_spent_minutes", 0)) + int(minutes)
                addition = f"[{timestamp}] ({minutes} min)"
                if note:
                    addition += f" {note}"
                existing = t.get("description", "").rstrip()
                if existing:
                    new_desc = existing + "\n" + addition
                else:
                    new_desc = addition
                t["description"] = new_desc
                self.save()
                return session_entry
        return None

    def register_people(self, *names: str | None):
        names_clean = [n.strip() for n in names if n and n.strip()]
        if not names_clean:
            return
        current = set(self.data.get("meta", {}).get("people", []))
        updated = False
        for name in names_clean:
            if name not in current:
                current.add(name)
                updated = True
        if updated:
            self.data["meta"]["people"] = sorted(current)

    def get_people(self) -> list[str]:
        return list(self.data.get("meta", {}).get("people", []))

    def append_session(self, task_id: int, minutes: int, note: str):
        for t in self.data.get("tasks", []):
            if t.get("id") == task_id:
                self._ensure_task_defaults(t)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                session_entry = {
                    "timestamp": timestamp,
                    "minutes": minutes,
                    "note": note,
                }
                t["sessions"].append(session_entry)
                t["time_spent_minutes"] = int(t.get("time_spent_minutes", 0)) + int(minutes)
                addition = f"[{timestamp}] ({minutes} min)"
                if note:
                    addition += f" {note}"
                existing = t.get("description", "").rstrip()
                if existing:
                    new_desc = existing + "\n" + addition
                else:
                    new_desc = addition
                t["description"] = new_desc
                self.save()
                return session_entry
        return None

    def register_people(self, *names: str | None):
        names_clean = [n.strip() for n in names if n and n.strip()]
        if not names_clean:
            return
        current = set(self.data.get("meta", {}).get("people", []))
        updated = False
        for name in names_clean:
            if name not in current:
                current.add(name)
                updated = True
        if updated:
            self.data["meta"]["people"] = sorted(current)

    def get_people(self) -> list[str]:
        return list(self.data.get("meta", {}).get("people", []))

    def append_session(self, task_id: int, minutes: int, note: str):
        for t in self.data.get("tasks", []):
            if t.get("id") == task_id:
                self._ensure_task_defaults(t)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                session_entry = {
                    "timestamp": timestamp,
                    "minutes": minutes,
                    "note": note,
                }
                t["sessions"].append(session_entry)
                t["time_spent_minutes"] = int(t.get("time_spent_minutes", 0)) + int(minutes)
                addition = f"[{timestamp}] ({minutes} min)"
                if note:
                    addition += f" {note}"
                existing = t.get("description", "").rstrip()
                if existing:
                    new_desc = existing + "\n" + addition
                else:
                    new_desc = addition
                t["description"] = new_desc
                self.save()
                return session_entry
        return None

    def register_people(self, *names: str | None):
        names_clean = [n.strip() for n in names if n and n.strip()]
        if not names_clean:
            return
        current = set(self.data.get("meta", {}).get("people", []))
        updated = False
        for name in names_clean:
            if name not in current:
                current.add(name)
                updated = True
        if updated:
            self.data["meta"]["people"] = sorted(current)

    def get_people(self) -> list[str]:
        return list(self.data.get("meta", {}).get("people", []))

    def append_session(self, task_id: int, minutes: int, note: str):
        for t in self.data.get("tasks", []):
            if t.get("id") == task_id:
                self._ensure_task_defaults(t)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                session_entry = {
                    "timestamp": timestamp,
                    "minutes": minutes,
                    "note": note,
                }
                t["sessions"].append(session_entry)
                t["time_spent_minutes"] = int(t.get("time_spent_minutes", 0)) + int(minutes)
                addition = f"[{timestamp}] ({minutes} min)"
                if note:
                    addition += f" {note}"
                existing = t.get("description", "").rstrip()
                if existing:
                    new_desc = existing + "\n" + addition
                else:
                    new_desc = addition
                t["description"] = new_desc
                self.save()
                return session_entry
        return None

    def eligible_today(self):
        today = date.today()
        return [
            t for t in self.data["tasks"]
            if t.get("status") == "open" and (parse_date(t.get("start_date", "")) or date(1970,1,1)) <= today
        ]

    def focused_today(self):
        return [t for t in self.eligible_today() if t.get("focus") is True]

    def clear_focus(self):
        for t in self.data["tasks"]:
            if t.get("focus"):
                t["focus"] = False
        self.save()

    def set_focus_for_today(self, selected_ids: list[int]):
        # Clear previous focuses, then set for selected ones
        self.clear_focus()
        for t in self.data["tasks"]:
            if t.get("id") in selected_ids and t.get("status") == "open":
                t["focus"] = True
        self.data["meta"]["last_focus_date"] = today_str()
        self.save()


# -------------------------------
# GUI Components
# -------------------------------
class TaskCard(ctk.CTkFrame):
    def __init__(
        self,
        master,
        task: dict,
        on_edit,
        on_done_toggle,
        on_focus_toggle,
        on_start_timer,
        on_log_time,
        on_postpone,
    ):
        super().__init__(master)
        self.task = task
        self.on_edit = on_edit
        self.on_done_toggle = on_done_toggle
        self.on_focus_toggle = on_focus_toggle
        self.on_start_timer = on_start_timer
        self.on_log_time = on_log_time
        self.on_postpone = on_postpone
        self._layout_mode: str | None = None

        self.configure(
            fg_color="#0F172A",
            corner_radius=18,
            border_width=1,
            border_color="#312E81",
        )
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Left labels container
        self.left_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=(20, 8))

        title_row = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        title_row.pack(anchor="w", fill="x")

        focus_prefix = "⭐ " if task.get("focus") else ""
        self.title_label = ctk.CTkLabel(
            title_row,
            text=f"{focus_prefix}{task.get('title','(no title)')}",
            font=("Segoe UI", 16, "bold"),
            justify="left",
            anchor="w",
        )
        self.title_label.pack(side="left", padx=(0, 6))

        # Priority badge
        pr = task.get("priority", "Medium")
        pr_color = {
            "High": "#F97316",  # orange
            "Medium": "#A78BFA",  # purple-light
            "Low": "#64748B",    # slate
        }.get(pr, "#A78BFA")
        pr_badge = ctk.CTkLabel(
            title_row,
            text=f" {pr} ",
            fg_color=pr_color,
            text_color="#000000",
            corner_radius=8,
        )
        pr_badge.pack(side="left", pady=2)

        # Meta line
        meta = []
        ttype = task.get("type")
        if ttype:
            meta.append(f"Type: {ttype}")
        who = task.get("who_asked")
        if who:
            meta.append(f"Asked by: {who}")
        assignee = task.get("assignee")
        if assignee:
            meta.append(f"Assignee: {assignee}")
        minutes = int(task.get("time_spent_minutes", 0) or 0)
        if minutes:
            hours, mins = divmod(minutes, 60)
            if hours:
                time_text = f"{hours}h {mins}m" if mins else f"{hours}h"
            else:
                time_text = f"{mins}m"
            meta.append(f"Time spent: {time_text}")
        sd = task.get("start_date") or "—"
        dl = task.get("deadline") or "—"
        overdue = False
        if task.get("status") == "open" and parse_date(task.get("deadline", "")):
            if parse_date(task.get("deadline")) < date.today():
                overdue = True
        dl_text = f"Due: {dl}"
        if overdue:
            dl_text += "  (OVERDUE)"
        top_line = " | ".join(meta)
        if top_line:
            meta_text = f"{top_line}\nStart: {sd} | {dl_text}"
        else:
            meta_text = f"Start: {sd} | {dl_text}"
        self.meta_line = ctk.CTkLabel(self.left_frame, text=meta_text, justify="left", anchor="w")
        self.meta_line.pack(anchor="w", pady=(6, 0))

        desc_text = (task.get("description") or "").strip()
        self.desc_box: ctk.CTkTextbox | None = None
        if desc_text:
            height = self._estimate_text_height(desc_text)
            self.desc_label = ctk.CTkLabel(
                self.left_frame,
                text="Description",
                anchor="w",
                justify="left",
                font=("Segoe UI", 13, "bold"),
            )
            self.desc_label.pack(anchor="w", pady=(8, 2))
            self.desc_box = ctk.CTkTextbox(self.left_frame, height=height)
            self.desc_box.pack(fill="x")
            self.desc_box.insert("1.0", desc_text)
            make_textbox_copyable(self.desc_box)

        self.links = gather_task_links(task)
        self.links_frame: ctk.CTkFrame | None = None
        if self.links:
            self.links_label = ctk.CTkLabel(
                self.left_frame,
                text=f"Links ({len(self.links)})",
                anchor="w",
                justify="left",
            )
            self.links_label.pack(anchor="w", pady=(8, 2))
            self.links_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
            self.links_frame.pack(fill="x", pady=(0, 4))
            for url in self.links:
                btn = ctk.CTkButton(
                    self.links_frame,
                    text=f"🔗 {shorten_url_display(url)}",
                    command=lambda url=url: self._open_link(url),
                    height=32,
                    width=0,
                    fg_color="#1E3A8A",
                    hover_color="#1D4ED8",
                    text_color="#E0E7FF",
                    font=("Segoe UI", 13),
                    cursor="hand2",
                )
                btn.pack(fill="x", pady=2)

        # Divider + buttons row
        self.separator = ctk.CTkFrame(self, fg_color="#1F2937", height=2)
        self.separator.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 2))
        self.separator.grid_propagate(False)

        self.btns_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btns_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(4, 18))

        focus_active = bool(task.get("focus"))
        focus_icon = "★" if focus_active else "☆"
        self.focus_btn = self._make_button(
            focus_icon,
            lambda: self.on_focus_toggle(task),
            width=44,
        )
        if focus_active:
            self.focus_btn.configure(
                fg_color="#3730A3",
                hover_color="#312E81",
                text_color="#FACC15",
            )
        else:
            self.focus_btn.configure(
                fg_color="#FACC15",
                hover_color="#EAB308",
                text_color="#111827",
            )

        self.timer_btn = self._make_button(
            "Start work",
            lambda: self.on_start_timer(task),
            width=92,
        )
        self.log_btn = self._make_button(
            "Log time",
            lambda: self.on_log_time(task),
            width=84,
        )
        self.postpone_btn = self._make_button(
            "Postpone",
            lambda: self.on_postpone(task),
            width=92,
            fg_color="#1F2937",
            hover_color="#374151",
        )
        self.edit_btn = self._make_button(
            "Edit",
            lambda: self.on_edit(task),
            width=68,
            fg_color="#374151",
            hover_color="#4B5563",
        )

        done_active = task.get("status") == "done"
        done_text = "Reopen" if done_active else "Done"
        done_fg = "#4B5563" if done_active else "#22C55E"
        done_hover = "#6B7280" if done_active else "#16A34A"
        self.done_btn = self._make_button(
            done_text,
            lambda: self.on_done_toggle(task),
            width=84,
            fg_color=done_fg,
            hover_color=done_hover,
        )

        if not done_active:
            self.done_btn.configure(text_color="#0B1120")

        self._buttons = [
            self.focus_btn,
            self.timer_btn,
            self.log_btn,
            self.postpone_btn,
            self.edit_btn,
            self.done_btn,
        ]
        self._arrange_buttons("inline")

        self.bind("<Configure>", self._on_configure)

    def _open_link(self, url: str):
        webbrowser.open(url)

    def _estimate_text_height(self, text: str) -> int:
        lines = text.count("\n") + 1
        approx = max((len(text) + 79) // 80, 1)
        total_lines = max(lines, approx)
        total_lines = max(1, min(3, total_lines))
        return max(40, total_lines * 24)

    def _make_button(
        self,
        text: str,
        command,
        *,
        width: int,
        fg_color: str = "#4C1D95",
        hover_color: str = "#5B21B6",
        text_color: str = "#F9FAFB",
    ) -> ctk.CTkButton:
        return ctk.CTkButton(
            self.btns_frame,
            text=text,
            command=command,
            width=width,
            height=32,
            fg_color=fg_color,
            hover_color=hover_color,
            text_color=text_color,
            font=("Segoe UI", 12),
            corner_radius=6,
        )

    def _arrange_buttons(self, mode: str):
        for btn in self._buttons:
            btn.pack_forget()
        if mode == "stacked":
            for btn in self._buttons:
                btn.pack(fill="x", padx=4, pady=4)
        else:
            for btn in self._buttons:
                btn.pack(side="left", padx=4)
        self._layout_mode = mode

    def _on_configure(self, _event=None):
        width = max(self.winfo_width(), 1)
        wrap = max(width - 120, 260)
        self.title_label.configure(wraplength=wrap)
        self.meta_line.configure(wraplength=wrap)

        mode = "stacked" if width < 860 else "inline"
        if mode != self._layout_mode:
            self._arrange_buttons(mode)


class TaskEditor(ctk.CTkToplevel):
    def __init__(self, master, task: dict, on_save, people: list[str]):
        super().__init__(master)
        self.title("Edit Task")
        self.geometry("620x640")
        self.resizable(True, True)
        self.task = task.copy()
        self.on_save = on_save
        initial_people = {p for p in people if p}
        initial_people.update({task.get("who_asked", ""), task.get("assignee", "")})
        self.people = sorted({p for p in initial_people if p})

        container = ctk.CTkFrame(self)
        container.pack(fill="both", expand=True, padx=16, pady=16)

        # Title
        ctk.CTkLabel(container, text="Title").grid(row=0, column=0, sticky="w", pady=(0,4))
        self.title_entry = ctk.CTkEntry(container)
        self.title_entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0,8))
        self.title_entry.insert(0, task.get("title", ""))

        # Type + Priority
        ctk.CTkLabel(container, text="Type").grid(row=2, column=0, sticky="w")
        self.type_menu = ctk.CTkOptionMenu(container, values=TASK_TYPES)
        self.type_menu.grid(row=3, column=0, sticky="ew", pady=(0,8))
        self.type_menu.set(task.get("type", TASK_TYPES[0]))

        ctk.CTkLabel(container, text="Priority").grid(row=2, column=1, sticky="w")
        self.pr_menu = ctk.CTkOptionMenu(container, values=PRIORITIES)
        self.pr_menu.grid(row=3, column=1, sticky="ew", pady=(0,8))
        self.pr_menu.set(task.get("priority", PRIORITIES[1]))

        # Who asked & Assignee
        ctk.CTkLabel(container, text="Who asked").grid(row=4, column=0, sticky="w")
        self.who_entry = ctk.CTkComboBox(container, values=self._people_values(), justify="left")
        self.who_entry.grid(row=5, column=0, sticky="ew", pady=(0,8))
        self.who_entry.set(task.get("who_asked", ""))

        ctk.CTkLabel(container, text="Assignee").grid(row=4, column=1, sticky="w")
        self.assignee_entry = ctk.CTkComboBox(container, values=self._people_values(), justify="left")
        self.assignee_entry.grid(row=5, column=1, sticky="ew", pady=(0,8))
        self.assignee_entry.set(task.get("assignee", ""))

        # Start & Deadline (tkcalendar)
        ctk.CTkLabel(container, text="Start Date").grid(row=6, column=0, sticky="w")
        self.start_date = create_dark_date_entry(container)
        self.start_date.grid(row=7, column=0, sticky="ew", pady=(0,8))
        sd = parse_date(task.get("start_date", "")) or date.today()
        self.start_date.set_date(sd)

        ctk.CTkLabel(container, text="Deadline").grid(row=6, column=1, sticky="w")
        self.deadline = create_dark_date_entry(container)
        self.deadline.grid(row=7, column=1, sticky="ew", pady=(0,8))
        dl = parse_date(task.get("deadline", "")) or date.today()
        self.deadline.set_date(dl)

        # Description
        ctk.CTkLabel(container, text="Description").grid(row=8, column=0, columnspan=2, sticky="w")
        self.description_box = ctk.CTkTextbox(container, height=160)
        self.description_box.grid(row=9, column=0, columnspan=2, sticky="nsew", pady=(0,8))
        self.description_box.insert("1.0", task.get("description", ""))

        # Session history (read-only)
        ctk.CTkLabel(container, text="Session history").grid(row=10, column=0, columnspan=2, sticky="w")
        self.history_box = ctk.CTkTextbox(container, height=140)
        self.history_box.grid(row=11, column=0, columnspan=2, sticky="nsew", pady=(0,8))
        self.history_box.insert("1.0", self._format_sessions(task))
        make_textbox_copyable(self.history_box)

        next_row = 12
        self.links = gather_task_links(task)
        if self.links:
            ctk.CTkLabel(container, text=f"Links ({len(self.links)})").grid(row=next_row, column=0, columnspan=2, sticky="w")
            next_row += 1
            links_frame = ctk.CTkFrame(container, fg_color="transparent")
            links_frame.grid(row=next_row, column=0, columnspan=2, sticky="ew", pady=(0,8))
            for url in self.links:
                btn = ctk.CTkButton(
                    links_frame,
                    text=f"🔗 {shorten_url_display(url)}",
                    command=lambda url=url: webbrowser.open(url),
                    height=30,
                    width=0,
                    fg_color="#1E3A8A",
                    hover_color="#1D4ED8",
                    text_color="#E0E7FF",
                    font=("Segoe UI", 13),
                    cursor="hand2",
                )
                btn.pack(fill="x", pady=2)
            next_row += 1

        # Status + Focus
        ctk.CTkLabel(container, text="Status").grid(row=next_row, column=0, sticky="w")
        self.status_menu = ctk.CTkOptionMenu(container, values=STATUSES)
        self.status_menu.grid(row=next_row + 1, column=0, sticky="ew", pady=(0,8))
        self.status_menu.set(task.get("status", "open"))

        self.focus_var = tk.BooleanVar(value=task.get("focus", False))
        self.focus_chk = ctk.CTkCheckBox(container, text="Focus for Today", variable=self.focus_var)
        self.focus_chk.grid(row=next_row + 1, column=1, sticky="w")

        # Buttons
        btns = ctk.CTkFrame(container, fg_color="transparent")
        btns.grid(row=next_row + 2, column=0, columnspan=2, sticky="e", pady=(8,0))
        ctk.CTkButton(btns, text="Cancel", command=self.destroy).pack(side="right", padx=6)
        ctk.CTkButton(btns, text="Save", command=self._save).pack(side="right", padx=6)

        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(9, weight=1)
        container.rowconfigure(11, weight=1)

    def _save(self):
        updated = {
            "title": self.title_entry.get().strip(),
            "type": self.type_menu.get(),
            "priority": self.pr_menu.get(),
            "who_asked": self.who_entry.get().strip(),
            "assignee": self.assignee_entry.get().strip(),
            "start_date": self.start_date.get_date().strftime('%Y-%m-%d'),
            "deadline": self.deadline.get_date().strftime('%Y-%m-%d'),
            "status": self.status_menu.get(),
            "focus": bool(self.focus_var.get()),
            "description": self.description_box.get("1.0", tk.END).strip(),
        }
        if not updated["title"]:
            messagebox.showwarning("Validation", "Title cannot be empty")
            return
        self.on_save(updated)
        self.destroy()

    def _people_values(self) -> list[str]:
        return [""] + self.people

    def _format_sessions(self, task: dict) -> str:
        sessions = task.get("sessions") or []
        if not sessions:
            return "No sessions recorded yet."
        lines = []
        for session in sessions:
            ts = session.get("timestamp", "?")
            minutes = session.get("minutes", 0)
            note = session.get("note", "")
            line = f"{ts} — {minutes} min"
            if note:
                line += f": {note}"
            lines.append(line)
        return "\n".join(lines)


class SessionLogDialog(ctk.CTkToplevel):
    def __init__(
        self,
        master,
        *,
        title: str,
        preset_minutes: int | None = None,
        allow_minutes_edit: bool = True,
        prompt: str,
    ):
        super().__init__(master)
        self.title(title)
        self.geometry("540x440")
        self.minsize(480, 360)
        self.transient(master)
        self.grab_set()
        self.result: tuple[int, str] | None = None

        container = ctk.CTkFrame(self)
        container.pack(fill="both", expand=True, padx=18, pady=18)

        time_label = ctk.CTkLabel(container, text="Minutes spent", font=("Segoe UI", 14, "bold"))
        time_label.pack(anchor="w")

        self.minutes_var = tk.StringVar()
        if preset_minutes is not None:
            self.minutes_var.set(str(preset_minutes))
        self.error_label = ctk.CTkLabel(container, text="", text_color="#F87171")
        self.minutes_entry = ctk.CTkEntry(container, textvariable=self.minutes_var, font=("Segoe UI", 14))
        self.minutes_entry.pack(fill="x", pady=(4, 12))
        if not allow_minutes_edit and preset_minutes is not None:
            self.minutes_entry.configure(state="disabled")
        else:
            self.minutes_var.trace_add("write", lambda *_: self.error_label.configure(text=""))

        ctk.CTkLabel(
            container,
            text=prompt,
            justify="left",
            anchor="w",
        ).pack(anchor="w")

        self.note_box = ctk.CTkTextbox(container, height=220)
        self.note_box.configure(font=("Segoe UI", 13), wrap="word")
        self.note_box.pack(fill="both", expand=True, pady=(8, 12))

        self.error_label.pack(anchor="w", pady=(0, 8))

        btns = ctk.CTkFrame(container, fg_color="transparent")
        btns.pack(fill="x")
        ctk.CTkButton(btns, text="Cancel", command=self._cancel).pack(side="right", padx=6)
        ctk.CTkButton(btns, text="Save", command=self._submit).pack(side="right", padx=6)

        if allow_minutes_edit and preset_minutes is None:
            self.minutes_entry.focus_set()
        else:
            self.note_box.focus_set()

        self.bind("<Return>", self._submit_event)
        self.bind("<Escape>", self._cancel_event)
        self.protocol("WM_DELETE_WINDOW", self._cancel)

    def show(self) -> tuple[int, str] | None:
        self.wait_window()
        return self.result

    def _submit_event(self, _event=None):
        self._submit()

    def _cancel_event(self, _event=None):
        self._cancel()

    def _submit(self):
        try:
            minutes = parse_minutes_input(self.minutes_var.get())
        except ValueError as exc:
            self.error_label.configure(text=str(exc))
            return
        note = self.note_box.get("1.0", tk.END).strip()
        self.result = (minutes, note)
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()


class PostponeDialog(ctk.CTkToplevel):
    def __init__(self, master, task: dict):
        super().__init__(master)
        self.title("Postpone task")
        self.geometry("380x260")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.result: int | None = None

        title = task.get("title", "Task")
        ctk.CTkLabel(
            self,
            text=f"How many days would you like to postpone '{title}'?",
            wraplength=340,
            justify="left",
        ).pack(padx=20, pady=(20, 12))

        quick = ctk.CTkFrame(self, fg_color="transparent")
        quick.pack(pady=(0, 12))

        for days in (1, 2, 3):
            ctk.CTkButton(
                quick,
                text=f"+{days} day" + ("s" if days > 1 else ""),
                command=lambda d=days: self._select(d),
                width=90,
            ).pack(side="left", padx=6)

        custom_frame = ctk.CTkFrame(self, fg_color="transparent")
        custom_frame.pack(fill="x", padx=20)
        ctk.CTkLabel(custom_frame, text="Custom days:").pack(anchor="w")
        self.custom_var = tk.StringVar()
        self.custom_entry = ctk.CTkEntry(custom_frame, textvariable=self.custom_var)
        self.custom_entry.pack(fill="x", pady=(4, 8))
        self.custom_entry.focus_set()

        self.error_label = ctk.CTkLabel(self, text="", text_color="#F87171")
        self.error_label.pack()

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(pady=(12, 16))
        ctk.CTkButton(btns, text="Cancel", command=self._cancel).pack(side="right", padx=6)
        ctk.CTkButton(btns, text="Apply", command=self._apply_custom).pack(side="right", padx=6)

        self.bind("<Return>", self._apply_custom_event)
        self.bind("<Escape>", self._cancel_event)
        self.protocol("WM_DELETE_WINDOW", self._cancel)

    def _select(self, days: int):
        self.result = days
        self.destroy()

    def _apply_custom_event(self, _event=None):
        self._apply_custom()

    def _cancel_event(self, _event=None):
        self._cancel()

    def _apply_custom(self):
        value = (self.custom_var.get() or "").strip()
        if not value:
            self.error_label.configure(text="Please enter the number of days to postpone.")
            return
        try:
            days = int(value)
        except ValueError:
            self.error_label.configure(text="Enter a whole number of days.")
            return
        if days <= 0:
            self.error_label.configure(text="Days must be greater than zero.")
            return
        self.result = days
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()

    def show(self) -> int | None:
        self.wait_window()
        return self.result


class PomodoroWindow(ctk.CTkToplevel):
    def __init__(self, master, task: dict, on_complete, on_close):
        super().__init__(master)
        self.title(f"Timer — {task.get('title', 'Task')}")
        self.geometry("380x280")
        self.resizable(False, False)
        self.on_complete = on_complete
        self.on_close = on_close
        self._after_id: str | None = None
        self._timer_running = False
        self._total_minutes = 0
        self._remaining_seconds = 0
        self._elapsed_seconds = 0

        self.label = ctk.CTkLabel(self, text=f"Task: {task.get('title', '(no title)')}", wraplength=340)
        self.label.pack(pady=(16, 8), padx=16)

        entry_frame = ctk.CTkFrame(self, fg_color="transparent")
        entry_frame.pack(pady=(0, 12))
        ctk.CTkLabel(entry_frame, text="Minutes to focus:").pack(side="left", padx=(0, 8))
        self.minutes_var = tk.StringVar(value="25")
        self.minutes_entry = ctk.CTkEntry(entry_frame, textvariable=self.minutes_var, width=90)
        self.minutes_entry.pack(side="left")

        self.timer_label = ctk.CTkLabel(self, text="00:00", font=("Segoe UI", 28, "bold"))
        self.timer_label.pack(pady=(0, 12))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, 16))
        self.start_btn = ctk.CTkButton(btn_frame, text="Start", command=self._start_timer)
        self.start_btn.pack(side="left", padx=6)
        self.stop_btn = ctk.CTkButton(btn_frame, text="Stop", command=self._stop_timer, state="disabled")
        self.stop_btn.pack(side="left", padx=6)
        self.cancel_btn = ctk.CTkButton(btn_frame, text="Cancel", command=self._cancel_timer)
        self.cancel_btn.pack(side="left", padx=6)

        self.protocol("WM_DELETE_WINDOW", self._on_close_request)

    def _start_timer(self):
        if self._timer_running:
            return
        try:
            minutes = int(self.minutes_var.get())
        except (TypeError, ValueError):
            messagebox.showwarning("Timer", "Please enter a valid number of minutes.")
            return
        if minutes <= 0:
            messagebox.showwarning("Timer", "Minutes must be greater than zero.")
            return
        self._total_minutes = minutes
        self._remaining_seconds = minutes * 60
        self._elapsed_seconds = 0
        self._timer_running = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.minutes_entry.configure(state="disabled")
        self._tick()

    def _tick(self):
        mins, secs = divmod(self._remaining_seconds, 60)
        self.timer_label.configure(text=f"{mins:02d}:{secs:02d}")
        if self._remaining_seconds <= 0:
            self._elapsed_seconds = self._total_minutes * 60
            self._complete_session(ended_early=False)
            return
        self._remaining_seconds -= 1
        self._elapsed_seconds += 1
        self._after_id = self.after(1000, self._tick)

    def _stop_timer(self):
        if not self._timer_running:
            return
        if self._elapsed_seconds <= 0:
            # Nothing tracked yet, treat as cancel.
            self._cancel_timer()
            return
        minutes = max(1, math.ceil(self._elapsed_seconds / 60))
        self._complete_session(ended_early=True, minutes_override=minutes)

    def _cancel_timer(self, confirm: bool = True):
        if self._timer_running and confirm:
            if not messagebox.askyesno("Cancel session?", "Discard this timer session without logging time?"):
                return
        self._halt_timer()
        self._close_window()

    def _complete_session(self, *, ended_early: bool, minutes_override: int | None = None):
        minutes = minutes_override if minutes_override is not None else self._total_minutes
        self._halt_timer()
        if self.on_complete:
            self.on_complete(minutes, ended_early)
        self._close_window()

    def _halt_timer(self):
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        self._timer_running = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.minutes_entry.configure(state="normal")

    def _on_close_request(self):
        if self._timer_running:
            if not messagebox.askyesno("Cancel session?", "Timer is running. Cancel without saving?"):
                return
            self._cancel_timer(confirm=False)
            return
        self._cancel_timer(confirm=False)

    def _close_window(self):
        if self.on_close:
            self.on_close()
        if self.winfo_exists():
            super().destroy()

    def _people_values(self) -> list[str]:
        return [""] + self.people

    def _format_sessions(self, task: dict) -> str:
        sessions = task.get("sessions") or []
        if not sessions:
            return "No sessions recorded yet."
        lines = []
        for session in sessions:
            ts = session.get("timestamp", "?")
            minutes = session.get("minutes", 0)
            note = session.get("note", "")
            line = f"{ts} — {minutes} min"
            if note:
                line += f": {note}"
            lines.append(line)
        return "\n".join(lines)


class SessionLogDialog(ctk.CTkToplevel):
    def __init__(
        self,
        master,
        *,
        title: str,
        preset_minutes: int | None = None,
        allow_minutes_edit: bool = True,
        prompt: str,
    ):
        super().__init__(master)
        self.title(title)
        self.geometry("540x440")
        self.minsize(480, 360)
        self.transient(master)
        self.grab_set()
        self.result: tuple[int, str] | None = None

        container = ctk.CTkFrame(self)
        container.pack(fill="both", expand=True, padx=18, pady=18)

        time_label = ctk.CTkLabel(container, text="Minutes spent", font=("Segoe UI", 14, "bold"))
        time_label.pack(anchor="w")

        self.minutes_var = tk.StringVar()
        if preset_minutes is not None:
            self.minutes_var.set(str(preset_minutes))
        self.error_label = ctk.CTkLabel(container, text="", text_color="#F87171")
        self.minutes_entry = ctk.CTkEntry(container, textvariable=self.minutes_var, font=("Segoe UI", 14))
        self.minutes_entry.pack(fill="x", pady=(4, 12))
        if not allow_minutes_edit and preset_minutes is not None:
            self.minutes_entry.configure(state="disabled")
        else:
            self.minutes_var.trace_add("write", lambda *_: self.error_label.configure(text=""))

        ctk.CTkLabel(
            container,
            text=prompt,
            justify="left",
            anchor="w",
        ).pack(anchor="w")

        self.note_box = ctk.CTkTextbox(container, height=220)
        self.note_box.configure(font=("Segoe UI", 13), wrap="word")
        self.note_box.pack(fill="both", expand=True, pady=(8, 12))

        self.error_label.pack(anchor="w", pady=(0, 8))

        btns = ctk.CTkFrame(container, fg_color="transparent")
        btns.pack(fill="x")
        ctk.CTkButton(btns, text="Cancel", command=self._cancel).pack(side="right", padx=6)
        ctk.CTkButton(btns, text="Save", command=self._submit).pack(side="right", padx=6)

        if allow_minutes_edit and preset_minutes is None:
            self.minutes_entry.focus_set()
        else:
            self.note_box.focus_set()

        self.bind("<Return>", self._submit_event)
        self.bind("<Escape>", self._cancel_event)
        self.protocol("WM_DELETE_WINDOW", self._cancel)

    def show(self) -> tuple[int, str] | None:
        self.wait_window()
        return self.result

    def _submit_event(self, _event=None):
        self._submit()

    def _cancel_event(self, _event=None):
        self._cancel()

    def _submit(self):
        try:
            minutes = parse_minutes_input(self.minutes_var.get())
        except ValueError as exc:
            self.error_label.configure(text=str(exc))
            return
        note = self.note_box.get("1.0", tk.END).strip()
        self.result = (minutes, note)
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()


class PostponeDialog(ctk.CTkToplevel):
    def __init__(self, master, task: dict):
        super().__init__(master)
        self.title("Postpone task")
        self.geometry("380x260")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.result: int | None = None

        title = task.get("title", "Task")
        ctk.CTkLabel(
            self,
            text=f"How many days would you like to postpone '{title}'?",
            wraplength=340,
            justify="left",
        ).pack(padx=20, pady=(20, 12))

        quick = ctk.CTkFrame(self, fg_color="transparent")
        quick.pack(pady=(0, 12))

        for days in (1, 2, 3):
            ctk.CTkButton(
                quick,
                text=f"+{days} day" + ("s" if days > 1 else ""),
                command=lambda d=days: self._select(d),
                width=90,
            ).pack(side="left", padx=6)

        custom_frame = ctk.CTkFrame(self, fg_color="transparent")
        custom_frame.pack(fill="x", padx=20)
        ctk.CTkLabel(custom_frame, text="Custom days:").pack(anchor="w")
        self.custom_var = tk.StringVar()
        self.custom_entry = ctk.CTkEntry(custom_frame, textvariable=self.custom_var)
        self.custom_entry.pack(fill="x", pady=(4, 8))
        self.custom_entry.focus_set()

        self.error_label = ctk.CTkLabel(self, text="", text_color="#F87171")
        self.error_label.pack()

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(pady=(12, 16))
        ctk.CTkButton(btns, text="Cancel", command=self._cancel).pack(side="right", padx=6)
        ctk.CTkButton(btns, text="Apply", command=self._apply_custom).pack(side="right", padx=6)

        self.bind("<Return>", self._apply_custom_event)
        self.bind("<Escape>", self._cancel_event)
        self.protocol("WM_DELETE_WINDOW", self._cancel)

    def _select(self, days: int):
        self.result = days
        self.destroy()

    def _apply_custom_event(self, _event=None):
        self._apply_custom()

    def _cancel_event(self, _event=None):
        self._cancel()

    def _apply_custom(self):
        value = (self.custom_var.get() or "").strip()
        if not value:
            self.error_label.configure(text="Please enter the number of days to postpone.")
            return
        try:
            days = int(value)
        except ValueError:
            self.error_label.configure(text="Enter a whole number of days.")
            return
        if days <= 0:
            self.error_label.configure(text="Days must be greater than zero.")
            return
        self.result = days
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()

    def show(self) -> int | None:
        self.wait_window()
        return self.result


class PomodoroWindow(ctk.CTkToplevel):
    def __init__(self, master, task: dict, on_complete, on_close):
        super().__init__(master)
        self.title(f"Timer — {task.get('title', 'Task')}")
        self.geometry("380x280")
        self.resizable(False, False)
        self.on_complete = on_complete
        self.on_close = on_close
        self._after_id: str | None = None
        self._timer_running = False
        self._total_minutes = 0
        self._remaining_seconds = 0
        self._elapsed_seconds = 0

        self.label = ctk.CTkLabel(self, text=f"Task: {task.get('title', '(no title)')}", wraplength=340)
        self.label.pack(pady=(16, 8), padx=16)

        entry_frame = ctk.CTkFrame(self, fg_color="transparent")
        entry_frame.pack(pady=(0, 12))
        ctk.CTkLabel(entry_frame, text="Minutes to focus:").pack(side="left", padx=(0, 8))
        self.minutes_var = tk.StringVar(value="25")
        self.minutes_entry = ctk.CTkEntry(entry_frame, textvariable=self.minutes_var, width=90)
        self.minutes_entry.pack(side="left")

        self.timer_label = ctk.CTkLabel(self, text="00:00", font=("Segoe UI", 28, "bold"))
        self.timer_label.pack(pady=(0, 12))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, 16))
        self.start_btn = ctk.CTkButton(btn_frame, text="Start", command=self._start_timer)
        self.start_btn.pack(side="left", padx=6)
        self.stop_btn = ctk.CTkButton(btn_frame, text="Stop", command=self._stop_timer, state="disabled")
        self.stop_btn.pack(side="left", padx=6)
        self.cancel_btn = ctk.CTkButton(btn_frame, text="Cancel", command=self._cancel_timer)
        self.cancel_btn.pack(side="left", padx=6)

        self.protocol("WM_DELETE_WINDOW", self._on_close_request)

    def _start_timer(self):
        if self._timer_running:
            return
        try:
            minutes = int(self.minutes_var.get())
        except (TypeError, ValueError):
            messagebox.showwarning("Timer", "Please enter a valid number of minutes.")
            return
        if minutes <= 0:
            messagebox.showwarning("Timer", "Minutes must be greater than zero.")
            return
        self._total_minutes = minutes
        self._remaining_seconds = minutes * 60
        self._elapsed_seconds = 0
        self._timer_running = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.minutes_entry.configure(state="disabled")
        self._tick()

    def _tick(self):
        mins, secs = divmod(self._remaining_seconds, 60)
        self.timer_label.configure(text=f"{mins:02d}:{secs:02d}")
        if self._remaining_seconds <= 0:
            self._elapsed_seconds = self._total_minutes * 60
            self._complete_session(ended_early=False)
            return
        self._remaining_seconds -= 1
        self._elapsed_seconds += 1
        self._after_id = self.after(1000, self._tick)

    def _stop_timer(self):
        if not self._timer_running:
            return
        if self._elapsed_seconds <= 0:
            # Nothing tracked yet, treat as cancel.
            self._cancel_timer()
            return
        minutes = max(1, math.ceil(self._elapsed_seconds / 60))
        self._complete_session(ended_early=True, minutes_override=minutes)

    def _cancel_timer(self, confirm: bool = True):
        if self._timer_running and confirm:
            if not messagebox.askyesno("Cancel session?", "Discard this timer session without logging time?"):
                return
        self._halt_timer()
        self._close_window()

    def _complete_session(self, *, ended_early: bool, minutes_override: int | None = None):
        minutes = minutes_override if minutes_override is not None else self._total_minutes
        self._halt_timer()
        if self.on_complete:
            self.on_complete(minutes, ended_early)
        self._close_window()

    def _halt_timer(self):
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        self._timer_running = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.minutes_entry.configure(state="normal")

    def _on_close_request(self):
        if self._timer_running:
            if not messagebox.askyesno("Cancel session?", "Timer is running. Cancel without saving?"):
                return
            self._cancel_timer(confirm=False)
            return
        self._cancel_timer(confirm=False)

    def _close_window(self):
        if self.on_close:
            self.on_close()
        if self.winfo_exists():
            super().destroy()

    def _people_values(self) -> list[str]:
        return [""] + self.people

    def _format_sessions(self, task: dict) -> str:
        sessions = task.get("sessions") or []
        if not sessions:
            return "No sessions recorded yet."
        lines = []
        for session in sessions:
            ts = session.get("timestamp", "?")
            minutes = session.get("minutes", 0)
            note = session.get("note", "")
            line = f"{ts} — {minutes} min"
            if note:
                line += f": {note}"
            lines.append(line)
        return "\n".join(lines)


class SessionLogDialog(ctk.CTkToplevel):
    def __init__(
        self,
        master,
        *,
        title: str,
        preset_minutes: int | None = None,
        allow_minutes_edit: bool = True,
        prompt: str,
    ):
        super().__init__(master)
        self.title(title)
        self.geometry("540x440")
        self.minsize(480, 360)
        self.transient(master)
        self.grab_set()
        self.result: tuple[int, str] | None = None

        container = ctk.CTkFrame(self)
        container.pack(fill="both", expand=True, padx=18, pady=18)

        time_label = ctk.CTkLabel(container, text="Minutes spent", font=("Segoe UI", 14, "bold"))
        time_label.pack(anchor="w")

        self.minutes_var = tk.StringVar()
        if preset_minutes is not None:
            self.minutes_var.set(str(preset_minutes))
        self.error_label = ctk.CTkLabel(container, text="", text_color="#F87171")
        self.minutes_entry = ctk.CTkEntry(container, textvariable=self.minutes_var, font=("Segoe UI", 14))
        self.minutes_entry.pack(fill="x", pady=(4, 12))
        if not allow_minutes_edit and preset_minutes is not None:
            self.minutes_entry.configure(state="disabled")
        else:
            self.minutes_var.trace_add("write", lambda *_: self.error_label.configure(text=""))

        ctk.CTkLabel(
            container,
            text=prompt,
            justify="left",
            anchor="w",
        ).pack(anchor="w")

        self.note_box = ctk.CTkTextbox(container, height=220)
        self.note_box.configure(font=("Segoe UI", 13), wrap="word")
        self.note_box.pack(fill="both", expand=True, pady=(8, 12))

        self.error_label.pack(anchor="w", pady=(0, 8))

        btns = ctk.CTkFrame(container, fg_color="transparent")
        btns.pack(fill="x")
        ctk.CTkButton(btns, text="Cancel", command=self._cancel).pack(side="right", padx=6)
        ctk.CTkButton(btns, text="Save", command=self._submit).pack(side="right", padx=6)

        if allow_minutes_edit and preset_minutes is None:
            self.minutes_entry.focus_set()
        else:
            self.note_box.focus_set()

        self.bind("<Return>", self._submit_event)
        self.bind("<Escape>", self._cancel_event)
        self.protocol("WM_DELETE_WINDOW", self._cancel)

    def show(self) -> tuple[int, str] | None:
        self.wait_window()
        return self.result

    def _submit_event(self, _event=None):
        self._submit()

    def _cancel_event(self, _event=None):
        self._cancel()

    def _submit(self):
        try:
            minutes = parse_minutes_input(self.minutes_var.get())
        except ValueError as exc:
            self.error_label.configure(text=str(exc))
            return
        note = self.note_box.get("1.0", tk.END).strip()
        self.result = (minutes, note)
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()


class PomodoroWindow(ctk.CTkToplevel):
    def __init__(self, master, task: dict, on_complete, on_close):
        super().__init__(master)
        self.title(f"Timer — {task.get('title', 'Task')}")
        self.geometry("360x260")
        self.resizable(False, False)
        self.on_complete = on_complete
        self.on_close = on_close
        self._after_id = None
        self._timer_running = False
        self._total_minutes = 0
        self._remaining_seconds = 0

        self.label = ctk.CTkLabel(self, text=f"Task: {task.get('title', '(no title)')}", wraplength=320)
        self.label.pack(pady=(16, 8), padx=16)

        entry_frame = ctk.CTkFrame(self, fg_color="transparent")
        entry_frame.pack(pady=(0, 12))
        ctk.CTkLabel(entry_frame, text="Minutes to focus:").pack(side="left", padx=(0, 8))
        self.minutes_var = tk.StringVar(value="25")
        self.minutes_entry = ctk.CTkEntry(entry_frame, textvariable=self.minutes_var, width=80)
        self.minutes_entry.pack(side="left")

        self.timer_label = ctk.CTkLabel(self, text="00:00", font=("Segoe UI", 28, "bold"))
        self.timer_label.pack(pady=(0, 12))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, 16))
        self.start_btn = ctk.CTkButton(btn_frame, text="Start", command=self._start_timer)
        self.start_btn.pack(side="left", padx=6)
        self.stop_btn = ctk.CTkButton(btn_frame, text="Stop", command=self._stop_timer, state="disabled")
        self.stop_btn.pack(side="left", padx=6)

        self.protocol("WM_DELETE_WINDOW", self._on_close_request)

    def _start_timer(self):
        if self._timer_running:
            return
        try:
            minutes = int(self.minutes_var.get())
        except (TypeError, ValueError):
            messagebox.showwarning("Timer", "Please enter a valid number of minutes.")
            return
        if minutes <= 0:
            messagebox.showwarning("Timer", "Minutes must be greater than zero.")
            return
        self._total_minutes = minutes
        self._remaining_seconds = minutes * 60
        self._timer_running = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.minutes_entry.configure(state="disabled")
        self._tick()

    def _tick(self):
        mins, secs = divmod(self._remaining_seconds, 60)
        self.timer_label.configure(text=f"{mins:02d}:{secs:02d}")
        if self._remaining_seconds <= 0:
            self._finish_timer()
            return
        self._remaining_seconds -= 1
        self._after_id = self.after(1000, self._tick)

    def _finish_timer(self):
        self._timer_running = False
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.minutes_entry.configure(state="normal")
        if self.on_complete:
            self.on_complete(self._total_minutes)
        self._cleanup_and_close()

    def _stop_timer(self):
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        self._timer_running = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.minutes_entry.configure(state="normal")
        self._cleanup_and_close()

    def _on_close_request(self):
        if self._timer_running and not messagebox.askyesno("Stop timer?", "Timer is still running. Stop it?"):
            return
        self._stop_timer()

    def _cleanup_and_close(self):
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        self._timer_running = False
        if self.on_close:
            self.on_close()
        if self.winfo_exists():
            super().destroy()

    def _people_values(self) -> list[str]:
        return [""] + self.people

    def _format_sessions(self, task: dict) -> str:
        sessions = task.get("sessions") or []
        if not sessions:
            return "No sessions recorded yet."
        lines = []
        for session in sessions:
            ts = session.get("timestamp", "?")
            minutes = session.get("minutes", 0)
            note = session.get("note", "")
            line = f"{ts} — {minutes} min"
            if note:
                line += f": {note}"
            lines.append(line)
        return "\n".join(lines)


class SessionLogDialog(ctk.CTkToplevel):
    def __init__(
        self,
        master,
        *,
        title: str,
        preset_minutes: int | None = None,
        allow_minutes_edit: bool = True,
        prompt: str,
    ):
        super().__init__(master)
        self.title(title)
        self.geometry("540x440")
        self.minsize(480, 360)
        self.transient(master)
        self.grab_set()
        self.result: tuple[int, str] | None = None

        container = ctk.CTkFrame(self)
        container.pack(fill="both", expand=True, padx=18, pady=18)

        time_label = ctk.CTkLabel(container, text="Minutes spent", font=("Segoe UI", 14, "bold"))
        time_label.pack(anchor="w")

        self.minutes_var = tk.StringVar()
        if preset_minutes is not None:
            self.minutes_var.set(str(preset_minutes))
        self.error_label = ctk.CTkLabel(container, text="", text_color="#F87171")
        self.minutes_entry = ctk.CTkEntry(container, textvariable=self.minutes_var, font=("Segoe UI", 14))
        self.minutes_entry.pack(fill="x", pady=(4, 12))
        if not allow_minutes_edit and preset_minutes is not None:
            self.minutes_entry.configure(state="disabled")
        else:
            self.minutes_var.trace_add("write", lambda *_: self.error_label.configure(text=""))

        ctk.CTkLabel(
            container,
            text=prompt,
            justify="left",
            anchor="w",
        ).pack(anchor="w")

        self.note_box = ctk.CTkTextbox(container, height=220)
        self.note_box.configure(font=("Segoe UI", 13), wrap="word")
        self.note_box.pack(fill="both", expand=True, pady=(8, 12))

        self.error_label.pack(anchor="w", pady=(0, 8))

        btns = ctk.CTkFrame(container, fg_color="transparent")
        btns.pack(fill="x")
        ctk.CTkButton(btns, text="Cancel", command=self._cancel).pack(side="right", padx=6)
        ctk.CTkButton(btns, text="Save", command=self._submit).pack(side="right", padx=6)

        if allow_minutes_edit and preset_minutes is None:
            self.minutes_entry.focus_set()
        else:
            self.note_box.focus_set()

        self.bind("<Return>", self._submit_event)
        self.bind("<Escape>", self._cancel_event)
        self.protocol("WM_DELETE_WINDOW", self._cancel)

    def show(self) -> tuple[int, str] | None:
        self.wait_window()
        return self.result

    def _submit_event(self, _event=None):
        self._submit()

    def _cancel_event(self, _event=None):
        self._cancel()

    def _submit(self):
        try:
            minutes = parse_minutes_input(self.minutes_var.get())
        except ValueError as exc:
            self.error_label.configure(text=str(exc))
            return
        note = self.note_box.get("1.0", tk.END).strip()
        self.result = (minutes, note)
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()


class PomodoroWindow(ctk.CTkToplevel):
    def __init__(self, master, task: dict, on_complete, on_close):
        super().__init__(master)
        self.title(f"Timer — {task.get('title', 'Task')}")
        self.geometry("360x260")
        self.resizable(False, False)
        self.on_complete = on_complete
        self.on_close = on_close
        self._after_id = None
        self._timer_running = False
        self._total_minutes = 0
        self._remaining_seconds = 0

        self.label = ctk.CTkLabel(self, text=f"Task: {task.get('title', '(no title)')}", wraplength=320)
        self.label.pack(pady=(16, 8), padx=16)

        entry_frame = ctk.CTkFrame(self, fg_color="transparent")
        entry_frame.pack(pady=(0, 12))
        ctk.CTkLabel(entry_frame, text="Minutes to focus:").pack(side="left", padx=(0, 8))
        self.minutes_var = tk.StringVar(value="25")
        self.minutes_entry = ctk.CTkEntry(entry_frame, textvariable=self.minutes_var, width=80)
        self.minutes_entry.pack(side="left")

        self.timer_label = ctk.CTkLabel(self, text="00:00", font=("Segoe UI", 28, "bold"))
        self.timer_label.pack(pady=(0, 12))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, 16))
        self.start_btn = ctk.CTkButton(btn_frame, text="Start", command=self._start_timer)
        self.start_btn.pack(side="left", padx=6)
        self.stop_btn = ctk.CTkButton(btn_frame, text="Stop", command=self._stop_timer, state="disabled")
        self.stop_btn.pack(side="left", padx=6)

        self.protocol("WM_DELETE_WINDOW", self._on_close_request)

    def _start_timer(self):
        if self._timer_running:
            return
        try:
            minutes = int(self.minutes_var.get())
        except (TypeError, ValueError):
            messagebox.showwarning("Timer", "Please enter a valid number of minutes.")
            return
        if minutes <= 0:
            messagebox.showwarning("Timer", "Minutes must be greater than zero.")
            return
        self._total_minutes = minutes
        self._remaining_seconds = minutes * 60
        self._timer_running = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.minutes_entry.configure(state="disabled")
        self._tick()

    def _tick(self):
        mins, secs = divmod(self._remaining_seconds, 60)
        self.timer_label.configure(text=f"{mins:02d}:{secs:02d}")
        if self._remaining_seconds <= 0:
            self._finish_timer()
            return
        self._remaining_seconds -= 1
        self._after_id = self.after(1000, self._tick)

    def _finish_timer(self):
        self._timer_running = False
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.minutes_entry.configure(state="normal")
        if self.on_complete:
            self.on_complete(self._total_minutes)
        self._cleanup_and_close()

    def _stop_timer(self):
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        self._timer_running = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.minutes_entry.configure(state="normal")
        self._cleanup_and_close()

    def _on_close_request(self):
        if self._timer_running and not messagebox.askyesno("Stop timer?", "Timer is still running. Stop it?"):
            return
        self._stop_timer()

    def _cleanup_and_close(self):
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        self._timer_running = False
        if self.on_close:
            self.on_close()
        if self.winfo_exists():
            super().destroy()

    def _people_values(self) -> list[str]:
        return [""] + self.people

    def _format_sessions(self, task: dict) -> str:
        sessions = task.get("sessions") or []
        if not sessions:
            return "No sessions recorded yet."
        lines = []
        for session in sessions:
            ts = session.get("timestamp", "?")
            minutes = session.get("minutes", 0)
            note = session.get("note", "")
            line = f"{ts} — {minutes} min"
            if note:
                line += f": {note}"
            lines.append(line)
        return "\n".join(lines)


class SessionLogDialog(ctk.CTkToplevel):
    def __init__(
        self,
        master,
        *,
        title: str,
        preset_minutes: int | None = None,
        allow_minutes_edit: bool = True,
        prompt: str,
    ):
        super().__init__(master)
        self.title(title)
        self.geometry("540x440")
        self.minsize(480, 360)
        self.transient(master)
        self.grab_set()
        self.result: tuple[int, str] | None = None

        container = ctk.CTkFrame(self)
        container.pack(fill="both", expand=True, padx=18, pady=18)

        time_label = ctk.CTkLabel(container, text="Minutes spent", font=("Segoe UI", 14, "bold"))
        time_label.pack(anchor="w")

        self.minutes_var = tk.StringVar()
        if preset_minutes is not None:
            self.minutes_var.set(str(preset_minutes))
        self.error_label = ctk.CTkLabel(container, text="", text_color="#F87171")
        self.minutes_entry = ctk.CTkEntry(container, textvariable=self.minutes_var, font=("Segoe UI", 14))
        self.minutes_entry.pack(fill="x", pady=(4, 12))
        if not allow_minutes_edit and preset_minutes is not None:
            self.minutes_entry.configure(state="disabled")
        else:
            self.minutes_var.trace_add("write", lambda *_: self.error_label.configure(text=""))

        ctk.CTkLabel(
            container,
            text=prompt,
            justify="left",
            anchor="w",
        ).pack(anchor="w")

        self.note_box = ctk.CTkTextbox(container, height=220)
        self.note_box.configure(font=("Segoe UI", 13), wrap="word")
        self.note_box.pack(fill="both", expand=True, pady=(8, 12))

        self.error_label.pack(anchor="w", pady=(0, 8))

        btns = ctk.CTkFrame(container, fg_color="transparent")
        btns.pack(fill="x")
        ctk.CTkButton(btns, text="Cancel", command=self._cancel).pack(side="right", padx=6)
        ctk.CTkButton(btns, text="Save", command=self._submit).pack(side="right", padx=6)

        if allow_minutes_edit and preset_minutes is None:
            self.minutes_entry.focus_set()
        else:
            self.note_box.focus_set()

        self.bind("<Return>", self._submit_event)
        self.bind("<Escape>", self._cancel_event)
        self.protocol("WM_DELETE_WINDOW", self._cancel)

    def show(self) -> tuple[int, str] | None:
        self.wait_window()
        return self.result

    def _submit_event(self, _event=None):
        self._submit()

    def _cancel_event(self, _event=None):
        self._cancel()

    def _submit(self):
        try:
            minutes = parse_minutes_input(self.minutes_var.get())
        except ValueError as exc:
            self.error_label.configure(text=str(exc))
            return
        note = self.note_box.get("1.0", tk.END).strip()
        self.result = (minutes, note)
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()


class PomodoroWindow(ctk.CTkToplevel):
    def __init__(self, master, task: dict, on_complete, on_close):
        super().__init__(master)
        self.title(f"Timer — {task.get('title', 'Task')}")
        self.geometry("360x260")
        self.resizable(False, False)
        self.on_complete = on_complete
        self.on_close = on_close
        self._after_id = None
        self._timer_running = False
        self._total_minutes = 0
        self._remaining_seconds = 0

        self.label = ctk.CTkLabel(self, text=f"Task: {task.get('title', '(no title)')}", wraplength=320)
        self.label.pack(pady=(16, 8), padx=16)

        entry_frame = ctk.CTkFrame(self, fg_color="transparent")
        entry_frame.pack(pady=(0, 12))
        ctk.CTkLabel(entry_frame, text="Minutes to focus:").pack(side="left", padx=(0, 8))
        self.minutes_var = tk.StringVar(value="25")
        self.minutes_entry = ctk.CTkEntry(entry_frame, textvariable=self.minutes_var, width=80)
        self.minutes_entry.pack(side="left")

        self.timer_label = ctk.CTkLabel(self, text="00:00", font=("Segoe UI", 28, "bold"))
        self.timer_label.pack(pady=(0, 12))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, 16))
        self.start_btn = ctk.CTkButton(btn_frame, text="Start", command=self._start_timer)
        self.start_btn.pack(side="left", padx=6)
        self.stop_btn = ctk.CTkButton(btn_frame, text="Stop", command=self._stop_timer, state="disabled")
        self.stop_btn.pack(side="left", padx=6)

        self.protocol("WM_DELETE_WINDOW", self._on_close_request)

    def _start_timer(self):
        if self._timer_running:
            return
        try:
            minutes = int(self.minutes_var.get())
        except (TypeError, ValueError):
            messagebox.showwarning("Timer", "Please enter a valid number of minutes.")
            return
        if minutes <= 0:
            messagebox.showwarning("Timer", "Minutes must be greater than zero.")
            return
        self._total_minutes = minutes
        self._remaining_seconds = minutes * 60
        self._timer_running = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.minutes_entry.configure(state="disabled")
        self._tick()

    def _tick(self):
        mins, secs = divmod(self._remaining_seconds, 60)
        self.timer_label.configure(text=f"{mins:02d}:{secs:02d}")
        if self._remaining_seconds <= 0:
            self._finish_timer()
            return
        self._remaining_seconds -= 1
        self._after_id = self.after(1000, self._tick)

    def _finish_timer(self):
        self._timer_running = False
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.minutes_entry.configure(state="normal")
        if self.on_complete:
            self.on_complete(self._total_minutes)
        self._cleanup_and_close()

    def _stop_timer(self):
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        self._timer_running = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.minutes_entry.configure(state="normal")
        self._cleanup_and_close()

    def _on_close_request(self):
        if self._timer_running and not messagebox.askyesno("Stop timer?", "Timer is still running. Stop it?"):
            return
        self._stop_timer()

    def _cleanup_and_close(self):
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        self._timer_running = False
        if self.on_close:
            self.on_close()
        if self.winfo_exists():
            super().destroy()

    def _people_values(self) -> list[str]:
        return [""] + self.people

    def _format_sessions(self, task: dict) -> str:
        sessions = task.get("sessions") or []
        if not sessions:
            return "No sessions recorded yet."
        lines = []
        for session in sessions:
            ts = session.get("timestamp", "?")
            minutes = session.get("minutes", 0)
            note = session.get("note", "")
            line = f"{ts} — {minutes} min"
            if note:
                line += f": {note}"
            lines.append(line)
        return "\n".join(lines)


class SessionLogDialog(ctk.CTkToplevel):
    def __init__(
        self,
        master,
        *,
        title: str,
        preset_minutes: int | None = None,
        allow_minutes_edit: bool = True,
        prompt: str,
    ):
        super().__init__(master)
        self.title(title)
        self.geometry("540x440")
        self.minsize(480, 360)
        self.transient(master)
        self.grab_set()
        self.result: tuple[int, str] | None = None

        container = ctk.CTkFrame(self)
        container.pack(fill="both", expand=True, padx=18, pady=18)

        time_label = ctk.CTkLabel(container, text="Minutes spent", font=("Segoe UI", 14, "bold"))
        time_label.pack(anchor="w")

        self.minutes_var = tk.StringVar()
        if preset_minutes is not None:
            self.minutes_var.set(str(preset_minutes))
        self.error_label = ctk.CTkLabel(container, text="", text_color="#F87171")
        self.minutes_entry = ctk.CTkEntry(container, textvariable=self.minutes_var, font=("Segoe UI", 14))
        self.minutes_entry.pack(fill="x", pady=(4, 12))
        if not allow_minutes_edit and preset_minutes is not None:
            self.minutes_entry.configure(state="disabled")
        else:
            self.minutes_var.trace_add("write", lambda *_: self.error_label.configure(text=""))

        ctk.CTkLabel(
            container,
            text=prompt,
            justify="left",
            anchor="w",
        ).pack(anchor="w")

        self.note_box = ctk.CTkTextbox(container, height=220)
        self.note_box.configure(font=("Segoe UI", 13), wrap="word")
        self.note_box.pack(fill="both", expand=True, pady=(8, 12))

        self.error_label.pack(anchor="w", pady=(0, 8))

        btns = ctk.CTkFrame(container, fg_color="transparent")
        btns.pack(fill="x")
        ctk.CTkButton(btns, text="Cancel", command=self._cancel).pack(side="right", padx=6)
        ctk.CTkButton(btns, text="Save", command=self._submit).pack(side="right", padx=6)

        if allow_minutes_edit and preset_minutes is None:
            self.minutes_entry.focus_set()
        else:
            self.note_box.focus_set()

        self.bind("<Return>", self._submit_event)
        self.bind("<Escape>", self._cancel_event)
        self.protocol("WM_DELETE_WINDOW", self._cancel)

    def show(self) -> tuple[int, str] | None:
        self.wait_window()
        return self.result

    def _submit_event(self, _event=None):
        self._submit()

    def _cancel_event(self, _event=None):
        self._cancel()

    def _submit(self):
        try:
            minutes = parse_minutes_input(self.minutes_var.get())
        except ValueError as exc:
            self.error_label.configure(text=str(exc))
            return
        note = self.note_box.get("1.0", tk.END).strip()
        self.result = (minutes, note)
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()


class PomodoroWindow(ctk.CTkToplevel):
    def __init__(self, master, task: dict, on_complete, on_close):
        super().__init__(master)
        self.title(f"Timer — {task.get('title', 'Task')}")
        self.geometry("360x260")
        self.resizable(False, False)
        self.on_complete = on_complete
        self.on_close = on_close
        self._after_id = None
        self._timer_running = False
        self._total_minutes = 0
        self._remaining_seconds = 0

        self.label = ctk.CTkLabel(self, text=f"Task: {task.get('title', '(no title)')}", wraplength=320)
        self.label.pack(pady=(16, 8), padx=16)

        entry_frame = ctk.CTkFrame(self, fg_color="transparent")
        entry_frame.pack(pady=(0, 12))
        ctk.CTkLabel(entry_frame, text="Minutes to focus:").pack(side="left", padx=(0, 8))
        self.minutes_var = tk.StringVar(value="25")
        self.minutes_entry = ctk.CTkEntry(entry_frame, textvariable=self.minutes_var, width=80)
        self.minutes_entry.pack(side="left")

        self.timer_label = ctk.CTkLabel(self, text="00:00", font=("Segoe UI", 28, "bold"))
        self.timer_label.pack(pady=(0, 12))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, 16))
        self.start_btn = ctk.CTkButton(btn_frame, text="Start", command=self._start_timer)
        self.start_btn.pack(side="left", padx=6)
        self.stop_btn = ctk.CTkButton(btn_frame, text="Stop", command=self._stop_timer, state="disabled")
        self.stop_btn.pack(side="left", padx=6)

        self.protocol("WM_DELETE_WINDOW", self._on_close_request)

    def _start_timer(self):
        if self._timer_running:
            return
        try:
            minutes = int(self.minutes_var.get())
        except (TypeError, ValueError):
            messagebox.showwarning("Timer", "Please enter a valid number of minutes.")
            return
        if minutes <= 0:
            messagebox.showwarning("Timer", "Minutes must be greater than zero.")
            return
        self._total_minutes = minutes
        self._remaining_seconds = minutes * 60
        self._timer_running = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.minutes_entry.configure(state="disabled")
        self._tick()

    def _tick(self):
        mins, secs = divmod(self._remaining_seconds, 60)
        self.timer_label.configure(text=f"{mins:02d}:{secs:02d}")
        if self._remaining_seconds <= 0:
            self._finish_timer()
            return
        self._remaining_seconds -= 1
        self._after_id = self.after(1000, self._tick)

    def _finish_timer(self):
        self._timer_running = False
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.minutes_entry.configure(state="normal")
        if self.on_complete:
            self.on_complete(self._total_minutes)
        self._cleanup_and_close()

    def _stop_timer(self):
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        self._timer_running = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.minutes_entry.configure(state="normal")
        self._cleanup_and_close()

    def _on_close_request(self):
        if self._timer_running and not messagebox.askyesno("Stop timer?", "Timer is still running. Stop it?"):
            return
        self._stop_timer()

    def _cleanup_and_close(self):
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        self._timer_running = False
        if self.on_close:
            self.on_close()
        if self.winfo_exists():
            super().destroy()

    def _people_values(self) -> list[str]:
        return [""] + self.people

    def _format_sessions(self, task: dict) -> str:
        sessions = task.get("sessions") or []
        if not sessions:
            return "No sessions recorded yet."
        lines = []
        for session in sessions:
            ts = session.get("timestamp", "?")
            minutes = session.get("minutes", 0)
            note = session.get("note", "")
            line = f"{ts} — {minutes} min"
            if note:
                line += f": {note}"
            lines.append(line)
        return "\n".join(lines)


class PomodoroWindow(ctk.CTkToplevel):
    def __init__(self, master, task: dict, on_complete, on_close):
        super().__init__(master)
        self.title(f"Timer — {task.get('title', 'Task')}")
        self.geometry("360x260")
        self.resizable(False, False)
        self.on_complete = on_complete
        self.on_close = on_close
        self._after_id = None
        self._timer_running = False
        self._total_minutes = 0
        self._remaining_seconds = 0

        self.label = ctk.CTkLabel(self, text=f"Task: {task.get('title', '(no title)')}", wraplength=320)
        self.label.pack(pady=(16, 8), padx=16)

        entry_frame = ctk.CTkFrame(self, fg_color="transparent")
        entry_frame.pack(pady=(0, 12))
        ctk.CTkLabel(entry_frame, text="Minutes to focus:").pack(side="left", padx=(0, 8))
        self.minutes_var = tk.StringVar(value="25")
        self.minutes_entry = ctk.CTkEntry(entry_frame, textvariable=self.minutes_var, width=80)
        self.minutes_entry.pack(side="left")

        self.timer_label = ctk.CTkLabel(self, text="00:00", font=("Segoe UI", 28, "bold"))
        self.timer_label.pack(pady=(0, 12))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, 16))
        self.start_btn = ctk.CTkButton(btn_frame, text="Start", command=self._start_timer)
        self.start_btn.pack(side="left", padx=6)
        self.stop_btn = ctk.CTkButton(btn_frame, text="Stop", command=self._stop_timer, state="disabled")
        self.stop_btn.pack(side="left", padx=6)

        self.protocol("WM_DELETE_WINDOW", self._on_close_request)

    def _start_timer(self):
        if self._timer_running:
            return
        try:
            minutes = int(self.minutes_var.get())
        except (TypeError, ValueError):
            messagebox.showwarning("Timer", "Please enter a valid number of minutes.")
            return
        if minutes <= 0:
            messagebox.showwarning("Timer", "Minutes must be greater than zero.")
            return
        self._total_minutes = minutes
        self._remaining_seconds = minutes * 60
        self._timer_running = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.minutes_entry.configure(state="disabled")
        self._tick()

    def _tick(self):
        mins, secs = divmod(self._remaining_seconds, 60)
        self.timer_label.configure(text=f"{mins:02d}:{secs:02d}")
        if self._remaining_seconds <= 0:
            self._finish_timer()
            return
        self._remaining_seconds -= 1
        self._after_id = self.after(1000, self._tick)

    def _finish_timer(self):
        self._timer_running = False
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.minutes_entry.configure(state="normal")
        if self.on_complete:
            self.on_complete(self._total_minutes)
        self._cleanup_and_close()

    def _stop_timer(self):
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        self._timer_running = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.minutes_entry.configure(state="normal")
        self._cleanup_and_close()

    def _on_close_request(self):
        if self._timer_running and not messagebox.askyesno("Stop timer?", "Timer is still running. Stop it?"):
            return
        self._stop_timer()

    def _cleanup_and_close(self):
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        self._timer_running = False
        if self.on_close:
            self.on_close()
        if self.winfo_exists():
            super().destroy()

    def _people_values(self) -> list[str]:
        return [""] + self.people

    def _format_sessions(self, task: dict) -> str:
        sessions = task.get("sessions") or []
        if not sessions:
            return "No sessions recorded yet."
        lines = []
        for session in sessions:
            ts = session.get("timestamp", "?")
            minutes = session.get("minutes", 0)
            note = session.get("note", "")
            line = f"{ts} — {minutes} min"
            if note:
                line += f": {note}"
            lines.append(line)
        return "\n".join(lines)


class PomodoroWindow(ctk.CTkToplevel):
    def __init__(self, master, task: dict, on_complete, on_close):
        super().__init__(master)
        self.title(f"Timer — {task.get('title', 'Task')}")
        self.geometry("360x260")
        self.resizable(False, False)
        self.on_complete = on_complete
        self.on_close = on_close
        self._after_id = None
        self._timer_running = False
        self._total_minutes = 0
        self._remaining_seconds = 0

        self.label = ctk.CTkLabel(self, text=f"Task: {task.get('title', '(no title)')}", wraplength=320)
        self.label.pack(pady=(16, 8), padx=16)

        entry_frame = ctk.CTkFrame(self, fg_color="transparent")
        entry_frame.pack(pady=(0, 12))
        ctk.CTkLabel(entry_frame, text="Minutes to focus:").pack(side="left", padx=(0, 8))
        self.minutes_var = tk.StringVar(value="25")
        self.minutes_entry = ctk.CTkEntry(entry_frame, textvariable=self.minutes_var, width=80)
        self.minutes_entry.pack(side="left")

        self.timer_label = ctk.CTkLabel(self, text="00:00", font=("Segoe UI", 28, "bold"))
        self.timer_label.pack(pady=(0, 12))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, 16))
        self.start_btn = ctk.CTkButton(btn_frame, text="Start", command=self._start_timer)
        self.start_btn.pack(side="left", padx=6)
        self.stop_btn = ctk.CTkButton(btn_frame, text="Stop", command=self._stop_timer, state="disabled")
        self.stop_btn.pack(side="left", padx=6)

        self.protocol("WM_DELETE_WINDOW", self._on_close_request)

    def _start_timer(self):
        if self._timer_running:
            return
        try:
            minutes = int(self.minutes_var.get())
        except (TypeError, ValueError):
            messagebox.showwarning("Timer", "Please enter a valid number of minutes.")
            return
        if minutes <= 0:
            messagebox.showwarning("Timer", "Minutes must be greater than zero.")
            return
        self._total_minutes = minutes
        self._remaining_seconds = minutes * 60
        self._timer_running = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.minutes_entry.configure(state="disabled")
        self._tick()

    def _tick(self):
        mins, secs = divmod(self._remaining_seconds, 60)
        self.timer_label.configure(text=f"{mins:02d}:{secs:02d}")
        if self._remaining_seconds <= 0:
            self._finish_timer()
            return
        self._remaining_seconds -= 1
        self._after_id = self.after(1000, self._tick)

    def _finish_timer(self):
        self._timer_running = False
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.minutes_entry.configure(state="normal")
        if self.on_complete:
            self.on_complete(self._total_minutes)
        self._cleanup_and_close()

    def _stop_timer(self):
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        self._timer_running = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.minutes_entry.configure(state="normal")
        self._cleanup_and_close()

    def _on_close_request(self):
        if self._timer_running and not messagebox.askyesno("Stop timer?", "Timer is still running. Stop it?"):
            return
        self._stop_timer()

    def _cleanup_and_close(self):
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        self._timer_running = False
        if self.on_close:
            self.on_close()
        if self.winfo_exists():
            super().destroy()

    def _people_values(self) -> list[str]:
        return [""] + self.people

    def _format_sessions(self, task: dict) -> str:
        sessions = task.get("sessions") or []
        if not sessions:
            return "No sessions recorded yet."
        lines = []
        for session in sessions:
            ts = session.get("timestamp", "?")
            minutes = session.get("minutes", 0)
            note = session.get("note", "")
            line = f"{ts} — {minutes} min"
            if note:
                line += f": {note}"
            lines.append(line)
        return "\n".join(lines)


class PomodoroWindow(ctk.CTkToplevel):
    def __init__(self, master, task: dict, on_complete, on_close):
        super().__init__(master)
        self.title(f"Timer — {task.get('title', 'Task')}")
        self.geometry("360x260")
        self.resizable(False, False)
        self.on_complete = on_complete
        self.on_close = on_close
        self._after_id = None
        self._timer_running = False
        self._total_minutes = 0
        self._remaining_seconds = 0

        self.label = ctk.CTkLabel(self, text=f"Task: {task.get('title', '(no title)')}", wraplength=320)
        self.label.pack(pady=(16, 8), padx=16)

        entry_frame = ctk.CTkFrame(self, fg_color="transparent")
        entry_frame.pack(pady=(0, 12))
        ctk.CTkLabel(entry_frame, text="Minutes to focus:").pack(side="left", padx=(0, 8))
        self.minutes_var = tk.StringVar(value="25")
        self.minutes_entry = ctk.CTkEntry(entry_frame, textvariable=self.minutes_var, width=80)
        self.minutes_entry.pack(side="left")

        self.timer_label = ctk.CTkLabel(self, text="00:00", font=("Segoe UI", 28, "bold"))
        self.timer_label.pack(pady=(0, 12))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, 16))
        self.start_btn = ctk.CTkButton(btn_frame, text="Start", command=self._start_timer)
        self.start_btn.pack(side="left", padx=6)
        self.stop_btn = ctk.CTkButton(btn_frame, text="Stop", command=self._stop_timer, state="disabled")
        self.stop_btn.pack(side="left", padx=6)

        self.protocol("WM_DELETE_WINDOW", self._on_close_request)

    def _start_timer(self):
        if self._timer_running:
            return
        try:
            minutes = int(self.minutes_var.get())
        except (TypeError, ValueError):
            messagebox.showwarning("Timer", "Please enter a valid number of minutes.")
            return
        if minutes <= 0:
            messagebox.showwarning("Timer", "Minutes must be greater than zero.")
            return
        self._total_minutes = minutes
        self._remaining_seconds = minutes * 60
        self._timer_running = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.minutes_entry.configure(state="disabled")
        self._tick()

    def _tick(self):
        mins, secs = divmod(self._remaining_seconds, 60)
        self.timer_label.configure(text=f"{mins:02d}:{secs:02d}")
        if self._remaining_seconds <= 0:
            self._finish_timer()
            return
        self._remaining_seconds -= 1
        self._after_id = self.after(1000, self._tick)

    def _finish_timer(self):
        self._timer_running = False
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.minutes_entry.configure(state="normal")
        if self.on_complete:
            self.on_complete(self._total_minutes)
        self._cleanup_and_close()

    def _stop_timer(self):
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        self._timer_running = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.minutes_entry.configure(state="normal")
        self._cleanup_and_close()

    def _on_close_request(self):
        if self._timer_running and not messagebox.askyesno("Stop timer?", "Timer is still running. Stop it?"):
            return
        self._stop_timer()

    def _cleanup_and_close(self):
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        self._timer_running = False
        if self.on_close:
            self.on_close()
        if self.winfo_exists():
            super().destroy()


class FocusDialog(ctk.CTkToplevel):
    def __init__(self, master, tasks_sorted, on_confirm):
        super().__init__(master)
        self.title("Select Today's Focus Tasks")
        self.geometry("720x520")
        self.resizable(True, True)
        self.on_confirm = on_confirm

        ctk.CTkLabel(self, text="Good day! Select tasks to focus on today (⭐)", font=("Segoe UI", 16, "bold")).pack(pady=(12,6))

        self.vars = []
        self.ids = []

        sf = ctk.CTkScrollableFrame(self)
        sf.pack(fill="both", expand=True, padx=12, pady=12)

        # Pre-select top 3
        preselect_ids = [t.get("id") for t in tasks_sorted[:3]]

        for t in tasks_sorted:
            var = tk.BooleanVar(value=(t.get("id") in preselect_ids))
            row = ctk.CTkFrame(sf)
            row.pack(fill="x", pady=6)
            cb = ctk.CTkCheckBox(row, text=f"[{t.get('priority')}] {t.get('title')} (Due: {t.get('deadline') or '—'})", variable=var)
            cb.pack(side="left", padx=6)
            self.vars.append(var)
            self.ids.append(t.get("id"))

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", pady=(0,12))
        ctk.CTkButton(btns, text="Skip Today", command=self._skip).pack(side="left", padx=8)
        ctk.CTkButton(btns, text="Confirm", command=self._confirm).pack(side="right", padx=8)

    def _confirm(self):
        selected = [tid for tid, v in zip(self.ids, self.vars) if v.get()]
        self.on_confirm(selected)
        self.destroy()

    def _skip(self):
        self.on_confirm([])
        self.destroy()


class TaskFocusApp(ctk.CTk):
    def __init__(self, store: TaskStore):
        super().__init__()
        self.store = store
        self.title(APP_TITLE)
        self.geometry("1100x750")
        self.minsize(720, 520)
        self.people_options = self.store.get_people()
        self.timer_window = None
        self._layout_mode: str | None = None
        self._widget_scale: float | None = None
        self._responsive_after: str | None = None
        self._pending_width: int | None = None
        self._today_search_job: str | None = None
        self._all_search_job: str | None = None

        self.bind("<Configure>", self._on_window_configure)

        # App header
        header = ctk.CTkFrame(self)
        header.pack(fill="x", padx=16, pady=(16,8))
        ctk.CTkLabel(header, text="🟣 TaskFocus", font=("Segoe UI", 20, "bold")).pack(side="left")
        self.status_label = ctk.CTkLabel(header, text="")
        self.status_label.pack(side="right")

        # Tabs
        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=16, pady=(8,16))
        self.today_tab = self.tabs.add("Today's Tasks")
        self.all_tab = self.tabs.add("All Tasks")
        self.stats_tab = self.tabs.add("Statistics")
        self.add_tab = self.tabs.add("Add Task")
        self.bulk_tab = self.tabs.add("Bulk Import")

        # Build each tab
        self._build_today_tab()
        self._build_all_tab()
        self._build_stats_tab()
        self._build_add_tab()
        self._build_bulk_tab()

        # Initial refresh
        self.refresh_all()

        # Ask focus if new day
        last = self.store.data.get("meta", {}).get("last_focus_date")
        if last != today_str():
            self._prompt_focus_selection()

        # Start on Today's tab
        self.tabs.set("Today's Tasks")

        # Apply responsive layout/sizing after widgets are drawn
        self.after(150, self._initialize_responsive_layout)

    # ----------------------- UI Builders -----------------------
    def _people_option_values(self) -> list[str]:
        return [""] + sorted({p for p in self.people_options if p})

    def _refresh_people_options(self):
        self.people_options = self.store.get_people()
        values = self._people_option_values()
        if hasattr(self, "add_who"):
            self.add_who.configure(values=values)
        if hasattr(self, "add_assignee"):
            self.add_assignee.configure(values=values)

    def _build_today_tab(self):
        # Top bar
        top = ctk.CTkFrame(self.today_tab)
        top.pack(fill="x", pady=(8,8))
        ctk.CTkLabel(top, text="Tasks that can be started today (open status)").pack(side="left", padx=6)
        ctk.CTkButton(top, text="Refresh", command=self.refresh_all).pack(side="right", padx=6)
        self.today_search_var = tk.StringVar()
        self.today_search_var.trace_add("write", self._on_today_search_change)
        ctk.CTkButton(
            top,
            text="Clear",
            width=64,
            command=lambda: self._clear_search(self.today_search_var, "_today_search_job", self._refresh_today_list),
        ).pack(side="right", padx=(6, 0))
        self.today_search_entry = ctk.CTkEntry(
            top,
            placeholder_text="Search…",
            width=220,
            textvariable=self.today_search_var,
        )
        self.today_search_entry.pack(side="right", padx=(6, 0))

        # Scrollable list
        self.today_list = ctk.CTkScrollableFrame(self.today_tab)
        self.today_list.pack(fill="both", expand=True)

    def _build_all_tab(self):
        # Filters bar
        bar = ctk.CTkFrame(self.all_tab)
        bar.pack(fill="x", pady=(8,8))
        ctk.CTkLabel(bar, text="Status:").pack(side="left", padx=(8,4))
        self.status_filter = ctk.CTkOptionMenu(bar, values=["all"] + STATUSES, command=lambda _=None: self._refresh_all_list())
        self.status_filter.pack(side="left")
        self.status_filter.set("all")

        ctk.CTkButton(bar, text="Refresh", command=self._refresh_all_list).pack(side="right", padx=6)
        self.all_search_var = tk.StringVar()
        self.all_search_var.trace_add("write", self._on_all_search_change)
        ctk.CTkButton(
            bar,
            text="Clear",
            width=64,
            command=lambda: self._clear_search(self.all_search_var, "_all_search_job", self._refresh_all_list),
        ).pack(side="right", padx=(6, 0))
        self.all_search_entry = ctk.CTkEntry(
            bar,
            placeholder_text="Search…",
            width=220,
            textvariable=self.all_search_var,
        )
        self.all_search_entry.pack(side="right", padx=(6, 0))

        # List
        self.all_list = ctk.CTkScrollableFrame(self.all_tab)
        self.all_list.pack(fill="both", expand=True)

    def _build_stats_tab(self):
        if not MATPLOTLIB_AVAILABLE:
            container = ctk.CTkFrame(self.stats_tab)
            container.pack(fill="both", expand=True, padx=12, pady=12)
            ctk.CTkLabel(
                container,
                text="Install matplotlib to view statistics charts (pip install matplotlib).",
                wraplength=520,
                justify="center",
            ).pack(expand=True, pady=32)
            self.stats_container = None
            return

        self.stats_container = ctk.CTkScrollableFrame(self.stats_tab)
        self.stats_container.pack(fill="both", expand=True, padx=12, pady=12)

        # Time spent chart section
        self.time_section = ctk.CTkFrame(self.stats_container)
        self.time_section.pack(fill="both", expand=True, pady=(0, 16))
        ctk.CTkLabel(
            self.time_section,
            text="Time spent per task (last 7 days)",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w", padx=8, pady=(8, 4))
        self.time_chart_holder = ctk.CTkFrame(self.time_section, fg_color="#111827", height=360)
        self.time_chart_holder.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.time_chart_holder.pack_propagate(False)
        self.time_canvas: FigureCanvasTkAgg | None = None

        # Burn-down chart section
        self.burn_section = ctk.CTkFrame(self.stats_container)
        self.burn_section.pack(fill="both", expand=True, pady=(0, 16))
        ctk.CTkLabel(
            self.burn_section,
            text="Task burn-down (last 7 days)",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w", padx=8, pady=(8, 4))
        self.burn_chart_holder = ctk.CTkFrame(self.burn_section, fg_color="#111827", height=320)
        self.burn_chart_holder.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.burn_chart_holder.pack_propagate(False)
        self.burn_canvas: FigureCanvasTkAgg | None = None

        # Workload by assignee chart section
        self.workload_section = ctk.CTkFrame(self.stats_container)
        self.workload_section.pack(fill="both", expand=True, pady=(0, 16))
        ctk.CTkLabel(
            self.workload_section,
            text="Open tasks by assignee and priority",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w", padx=8, pady=(8, 4))
        self.workload_chart_holder = ctk.CTkFrame(self.workload_section, fg_color="#111827", height=320)
        self.workload_chart_holder.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.workload_chart_holder.pack_propagate(False)
        self.workload_canvas: FigureCanvasTkAgg | None = None

    def _build_add_tab(self):
        container = ctk.CTkFrame(self.add_tab)
        container.pack(fill="both", expand=True, padx=12, pady=12)
        self.add_container = container

        self.add_title_label = ctk.CTkLabel(container, text="Title")
        self.add_title = ctk.CTkEntry(container)

        self.add_type_label = ctk.CTkLabel(container, text="Type")
        self.add_type = ctk.CTkOptionMenu(container, values=TASK_TYPES)
        self.add_type.set(TASK_TYPES[0])

        self.add_priority_label = ctk.CTkLabel(container, text="Priority")
        self.add_priority = ctk.CTkOptionMenu(container, values=PRIORITIES)
        self.add_priority.set(PRIORITIES[1])

        self.add_who_label = ctk.CTkLabel(container, text="Who asked")
        self.add_who = ctk.CTkComboBox(container, values=self._people_option_values(), justify="left")
        self.add_who.set("")

        self.add_assignee_label = ctk.CTkLabel(container, text="Assignee")
        self.add_assignee = ctk.CTkComboBox(container, values=self._people_option_values(), justify="left")
        self.add_assignee.set("")

        self.add_start_label = ctk.CTkLabel(container, text="Start Date")
        self.add_start = create_dark_date_entry(container)
        self.add_start.set_date(date.today())

        self.add_deadline_label = ctk.CTkLabel(container, text="Deadline")
        self.add_deadline = create_dark_date_entry(container)
        self.add_deadline.set_date(date.today())

        self.add_description_label = ctk.CTkLabel(container, text="Description")
        self.add_description = ctk.CTkTextbox(container, height=160)

        self.add_button_row = ctk.CTkFrame(container, fg_color="transparent")
        ctk.CTkButton(self.add_button_row, text="Clear", command=self._clear_add_form).pack(side="left", padx=6)
        ctk.CTkButton(self.add_button_row, text="Add Task", command=self._add_task_from_form).pack(side="left", padx=6)

        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)

        self._layout_add_form("wide")

    def _layout_add_form(self, mode: str):
        container = self.add_container
        widgets = [
            self.add_title_label,
            self.add_title,
            self.add_type_label,
            self.add_type,
            self.add_priority_label,
            self.add_priority,
            self.add_who_label,
            self.add_who,
            self.add_assignee_label,
            self.add_assignee,
            self.add_start_label,
            self.add_start,
            self.add_deadline_label,
            self.add_deadline,
            self.add_description_label,
            self.add_description,
            self.add_button_row,
        ]
        for w in widgets:
            w.grid_forget()

        for idx in range(0, 20):
            container.rowconfigure(idx, weight=0)

        if mode == "narrow":
            container.grid_columnconfigure(0, weight=1)
            container.grid_columnconfigure(1, weight=0)
            placements = [
                (self.add_title_label, {"row": 0, "column": 0, "sticky": "w"}),
                (self.add_title, {"row": 1, "column": 0, "sticky": "ew", "pady": (0, 8)}),
                (self.add_type_label, {"row": 2, "column": 0, "sticky": "w"}),
                (self.add_type, {"row": 3, "column": 0, "sticky": "ew", "pady": (0, 8)}),
                (self.add_priority_label, {"row": 4, "column": 0, "sticky": "w"}),
                (self.add_priority, {"row": 5, "column": 0, "sticky": "ew", "pady": (0, 8)}),
                (self.add_who_label, {"row": 6, "column": 0, "sticky": "w"}),
                (self.add_who, {"row": 7, "column": 0, "sticky": "ew", "pady": (0, 8)}),
                (self.add_assignee_label, {"row": 8, "column": 0, "sticky": "w"}),
                (self.add_assignee, {"row": 9, "column": 0, "sticky": "ew", "pady": (0, 8)}),
                (self.add_start_label, {"row": 10, "column": 0, "sticky": "w"}),
                (self.add_start, {"row": 11, "column": 0, "sticky": "ew", "pady": (0, 8)}),
                (self.add_deadline_label, {"row": 12, "column": 0, "sticky": "w"}),
                (self.add_deadline, {"row": 13, "column": 0, "sticky": "ew", "pady": (0, 8)}),
                (self.add_description_label, {"row": 14, "column": 0, "sticky": "w"}),
                (self.add_description, {"row": 15, "column": 0, "sticky": "nsew", "pady": (0, 8)}),
                (self.add_button_row, {"row": 16, "column": 0, "sticky": "e"}),
            ]
            target_row = 15
        else:
            container.grid_columnconfigure(0, weight=1)
            container.grid_columnconfigure(1, weight=1)
            placements = [
                (self.add_title_label, {"row": 0, "column": 0, "columnspan": 2, "sticky": "w"}),
                (self.add_title, {"row": 1, "column": 0, "columnspan": 2, "sticky": "ew", "pady": (0, 8)}),
                (self.add_type_label, {"row": 2, "column": 0, "sticky": "w"}),
                (self.add_priority_label, {"row": 2, "column": 1, "sticky": "w"}),
                (self.add_type, {"row": 3, "column": 0, "sticky": "ew", "pady": (0, 8)}),
                (self.add_priority, {"row": 3, "column": 1, "sticky": "ew", "pady": (0, 8)}),
                (self.add_who_label, {"row": 4, "column": 0, "sticky": "w"}),
                (self.add_assignee_label, {"row": 4, "column": 1, "sticky": "w"}),
                (self.add_who, {"row": 5, "column": 0, "sticky": "ew", "pady": (0, 8)}),
                (self.add_assignee, {"row": 5, "column": 1, "sticky": "ew", "pady": (0, 8)}),
                (self.add_start_label, {"row": 6, "column": 0, "sticky": "w"}),
                (self.add_deadline_label, {"row": 6, "column": 1, "sticky": "w"}),
                (self.add_start, {"row": 7, "column": 0, "sticky": "ew", "pady": (0, 8)}),
                (self.add_deadline, {"row": 7, "column": 1, "sticky": "ew", "pady": (0, 8)}),
                (self.add_description_label, {"row": 8, "column": 0, "columnspan": 2, "sticky": "w"}),
                (self.add_description, {"row": 9, "column": 0, "columnspan": 2, "sticky": "nsew", "pady": (0, 8)}),
                (self.add_button_row, {"row": 10, "column": 0, "columnspan": 2, "sticky": "e"}),
            ]
            target_row = 9

        for widget, opts in placements:
            widget.grid(**opts)

        container.rowconfigure(target_row, weight=1)

    def _build_bulk_tab(self):
        container = ctk.CTkFrame(self.bulk_tab)
        container.pack(fill="both", expand=True, padx=12, pady=12)
        self.bulk_container = container

        self.bulk_instruction_text = (
            "You are the TaskFocus bulk-import assistant.\n"
            "1. Read the notes I provide and identify every actionable task.\n"
            "2. Decide the best Type (Make/Ask/Arrange/Control), priority, start date, and deadline."
            " Use context or today's date when a start is missing, and leave fields blank if truly unknown.\n"
            "3. Capture who asked for the task and the assignee whenever the information exists.\n"
            "4. Create a short, informative Title and keep supporting details inside Description.\n\n"
            "Return the tasks exactly in this format, one per line:\n"
            "Type: Title — asked by <who asked> — assignee <assignee> — start <yyyy-mm-dd> — "
            "deadline <yyyy-mm-dd> — priority <High|Medium|Low> — description <details>\n"
            "Use yyyy-mm-dd dates (dd.mm.yyyy is also accepted on input). Title is required; omit an "
            "optional segment entirely if the data is unavailable."
        )

        instruct_frame = ctk.CTkFrame(container)
        instruct_frame.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(
            instruct_frame,
            text="Bulk import instructions for AI assistant",
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w", padx=4, pady=(4, 2))
        self.bulk_instruction_label = ctk.CTkLabel(
            instruct_frame,
            text=self.bulk_instruction_text,
            justify="left",
            wraplength=760,
        )
        self.bulk_instruction_label.pack(anchor="w", padx=4, pady=(0, 6))
        ctk.CTkButton(
            instruct_frame,
            text="Copy instructions",
            command=self._copy_bulk_instructions,
            width=160,
        ).pack(anchor="w", padx=4)

        self.bulk_form_help_text = (
            "After the AI responds, paste the generated lines below. Each line can omit optional parts, "
            "but the parser understands the same fields as the Add Task form: Title, Type, Priority, Who asked, "
            "Assignee, Start Date, Deadline, and Description."
        )
        self.bulk_form_help_label = ctk.CTkLabel(
            container,
            text=self.bulk_form_help_text,
            justify="left",
            wraplength=760,
        )
        self.bulk_form_help_label.pack(anchor="w", pady=(0, 8))

        self.bulk_text = ctk.CTkTextbox(container, height=320)
        self.bulk_text.pack(fill="both", expand=True)

        btns = ctk.CTkFrame(container, fg_color="transparent")
        btns.pack(fill="x", pady=(8,0))
        self.bulk_status = ctk.CTkLabel(btns, text="")
        self.bulk_status.pack(side="left")
        ctk.CTkButton(btns, text="Import", command=self._bulk_import).pack(side="right")

    def _refresh_stats(self):
        if not MATPLOTLIB_AVAILABLE or not getattr(self, "stats_container", None):
            return
        self._render_time_spent_chart()
        self._render_burn_chart()
        self._render_workload_chart()

    def _render_time_spent_chart(self):
        if not MATPLOTLIB_AVAILABLE or not getattr(self, "time_chart_holder", None):
            return
        if self.time_canvas:
            widget = self.time_canvas.get_tk_widget()
            widget.destroy()
            self.time_canvas = None
        for child in list(self.time_chart_holder.winfo_children()):
            child.destroy()

        end = date.today()
        start = end - timedelta(days=6)
        day_range = [start + timedelta(days=i) for i in range(7)]
        per_task: dict[str, defaultdict[date, int]] = {}

        for task in self.store.data.get("tasks", []):
            title = task.get("title") or "(untitled)"
            for session in task.get("sessions", []):
                when = parse_session_timestamp(session.get("timestamp"))
                if not when:
                    continue
                day = when.date()
                if day < start or day > end:
                    continue
                minutes = int(session.get("minutes", 0) or 0)
                if minutes <= 0:
                    continue
                bucket = per_task.setdefault(title, defaultdict(int))
                bucket[day] += minutes

        totals = {title: sum(day_map.values()) for title, day_map in per_task.items() if day_map}
        if not totals:
            ctk.CTkLabel(
                self.time_chart_holder,
                text="No session data recorded in the last 7 days.",
                text_color="#9CA3AF",
            ).pack(pady=24)
            return

        sorted_totals = sorted(totals.items(), key=lambda item: item[1], reverse=True)
        top_titles = [title for title, _ in sorted_totals[:5]]
        if len(sorted_totals) > 5:
            other_bucket: defaultdict[date, int] = defaultdict(int)
            for title, day_map in per_task.items():
                if title in top_titles:
                    continue
                for day, minutes in day_map.items():
                    other_bucket[day] += minutes
            if other_bucket:
                per_task["Other"] = other_bucket
                top_titles.append("Other")

        x = list(range(len(day_range)))
        bottoms = [0.0] * len(day_range)
        prop_cycle = plt.rcParams.get(
            "axes.prop_cycle",
            plt.cycler(color=["#8B5CF6", "#22C55E", "#F97316", "#0EA5E9", "#FACC15"]),
        )
        base_colors = prop_cycle.by_key().get(
            "color", ["#8B5CF6", "#22C55E", "#F97316", "#0EA5E9", "#FACC15"]
        )
        color_cycle = itertools.cycle(base_colors)

        fig, ax = plt.subplots(figsize=(11, 5), dpi=110)
        for title in top_titles:
            day_map = per_task.get(title, {})
            values = [day_map.get(day, 0) / 60 for day in day_range]
            color = next(color_cycle)
            ax.bar(x, values, bottom=bottoms, label=title, color=color, edgecolor="#0F172A", linewidth=0.3)
            bottoms = [bottoms[i] + values[i] for i in range(len(bottoms))]

        ax.set_ylabel("Hours", color="#E5E7EB")
        ax.set_xticks(x)
        ax.set_xticklabels([day.strftime("%a %d") for day in day_range], rotation=30, ha="right", color="#E5E7EB")
        ax.tick_params(axis="y", colors="#E5E7EB")
        ax.grid(axis="y", color="#374151", linestyle="--", alpha=0.4)
        ax.set_ylim(bottom=0)
        for spine in ax.spines.values():
            spine.set_color("#374151")
        ax.set_facecolor("#111827")
        fig.patch.set_facecolor("#111827")
        legend = ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), frameon=True)
        if legend:
            legend.get_frame().set_facecolor("#1F2937")
            legend.get_frame().set_edgecolor("#4B5563")
            for text in legend.get_texts():
                text.set_color("#F9FAFB")
        fig.tight_layout()

        self.time_canvas = FigureCanvasTkAgg(fig, master=self.time_chart_holder)
        self.time_canvas.draw()
        widget = self.time_canvas.get_tk_widget()
        widget.pack(fill="both", expand=True, padx=4, pady=4)
        widget.configure(background="#111827", highlightthickness=0, borderwidth=0)
        self._time_fig = fig

    def _render_burn_chart(self):
        if not MATPLOTLIB_AVAILABLE or not getattr(self, "burn_chart_holder", None):
            return
        if self.burn_canvas:
            widget = self.burn_canvas.get_tk_widget()
            widget.destroy()
            self.burn_canvas = None
        for child in list(self.burn_chart_holder.winfo_children()):
            child.destroy()

        tasks = self.store.data.get("tasks", [])
        if not tasks:
            ctk.CTkLabel(
                self.burn_chart_holder,
                text="No tasks tracked yet.",
                text_color="#9CA3AF",
            ).pack(pady=24)
            return

        end = date.today()
        start = end - timedelta(days=6)
        day_range = [start + timedelta(days=i) for i in range(7)]

        created_dates: list[date] = []
        completed_dates: list[date] = []
        today_local = date.today()
        for task in tasks:
            created = iso_to_date(task.get("created_at")) or today_local
            created_dates.append(created)
            completed = iso_to_date(task.get("completed_at")) if task.get("completed_at") else None
            if task.get("status") == "done" and not completed:
                completed = today_local
            if completed:
                completed_dates.append(completed)

        remaining_counts: list[int] = []
        completed_counts: list[int] = []
        for day in day_range:
            created_total = sum(1 for c in created_dates if c <= day)
            completed_total = sum(1 for c in completed_dates if c <= day)
            remaining_counts.append(max(created_total - completed_total, 0))
            completed_counts.append(completed_total)

        fig, ax = plt.subplots(figsize=(11, 4.5), dpi=110)
        x = list(range(len(day_range)))
        ax.plot(x, remaining_counts, marker="o", color="#38BDF8", label="Remaining tasks")
        ax.plot(x, completed_counts, marker="o", color="#22C55E", label="Completed tasks")
        ax.fill_between(x, remaining_counts, color="#38BDF8", alpha=0.2)

        ax.set_ylabel("Tasks", color="#E5E7EB")
        ax.set_xticks(x)
        ax.set_xticklabels([day.strftime("%a %d") for day in day_range], rotation=30, ha="right", color="#E5E7EB")
        ax.tick_params(axis="y", colors="#E5E7EB")
        ax.grid(axis="y", color="#374151", linestyle="--", alpha=0.4)
        ax.set_ylim(bottom=0)
        for spine in ax.spines.values():
            spine.set_color("#374151")
        ax.set_facecolor("#111827")
        fig.patch.set_facecolor("#111827")
        legend = ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), frameon=True)
        if legend:
            legend.get_frame().set_facecolor("#1F2937")
            legend.get_frame().set_edgecolor("#4B5563")
            for text in legend.get_texts():
                text.set_color("#F9FAFB")
        fig.tight_layout()

        self.burn_canvas = FigureCanvasTkAgg(fig, master=self.burn_chart_holder)
        self.burn_canvas.draw()
        widget = self.burn_canvas.get_tk_widget()
        widget.pack(fill="both", expand=True, padx=4, pady=4)
        widget.configure(background="#111827", highlightthickness=0, borderwidth=0)
        self._burn_fig = fig

    def _render_workload_chart(self):
        if not MATPLOTLIB_AVAILABLE or not getattr(self, "workload_chart_holder", None):
            return
        if self.workload_canvas:
            widget = self.workload_canvas.get_tk_widget()
            widget.destroy()
            self.workload_canvas = None
        for child in list(self.workload_chart_holder.winfo_children()):
            child.destroy()

        tasks = [t for t in self.store.data.get("tasks", []) if t.get("status") != "done"]
        if not tasks:
            ctk.CTkLabel(
                self.workload_chart_holder,
                text="No open tasks to analyse.",
                text_color="#9CA3AF",
            ).pack(pady=24)
            return

        per_person: dict[str, dict[str, int]] = {}
        for task in tasks:
            assignee = task.get("assignee") or "Unassigned"
            pr = task.get("priority") or "Medium"
            bucket = per_person.setdefault(assignee, {p: 0 for p in PRIORITIES})
            if pr not in bucket:
                bucket[pr] = 0
            bucket[pr] += 1

        totals = {name: sum(pr_counts.values()) for name, pr_counts in per_person.items()}
        sorted_people = sorted(totals.items(), key=lambda item: item[1], reverse=True)
        top_people = [name for name, _ in sorted_people[:6]]
        if len(sorted_people) > 6:
            other_bucket = {p: 0 for p in PRIORITIES}
            for name, _ in sorted_people[6:]:
                counts = per_person.get(name, {})
                for pr in PRIORITIES:
                    other_bucket[pr] += counts.get(pr, 0)
            if sum(other_bucket.values()):
                per_person["Other"] = other_bucket
                top_people.append("Other")

        x = list(range(len(top_people)))
        bottoms = [0] * len(top_people)
        color_map = {"High": "#F97316", "Medium": "#8B5CF6", "Low": "#22D3EE"}

        fig, ax = plt.subplots(figsize=(11, 4.2), dpi=110)
        for priority in PRIORITIES:
            values = [per_person.get(name, {}).get(priority, 0) for name in top_people]
            ax.bar(x, values, bottom=bottoms, label=priority, color=color_map.get(priority, "#8B5CF6"), edgecolor="#0F172A", linewidth=0.3)
            bottoms = [bottoms[i] + values[i] for i in range(len(bottoms))]

        ax.set_ylabel("Open tasks", color="#E5E7EB")
        ax.set_xticks(x)
        ax.set_xticklabels(top_people, rotation=20, ha="right", color="#E5E7EB")
        ax.tick_params(axis="y", colors="#E5E7EB")
        ax.grid(axis="y", color="#374151", linestyle="--", alpha=0.4)
        ax.set_ylim(bottom=0)
        for spine in ax.spines.values():
            spine.set_color("#374151")
        ax.set_facecolor("#111827")
        fig.patch.set_facecolor("#111827")
        legend = ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), frameon=True)
        if legend:
            legend.get_frame().set_facecolor("#1F2937")
            legend.get_frame().set_edgecolor("#4B5563")
            for text in legend.get_texts():
                text.set_color("#F9FAFB")
        fig.tight_layout()

        self.workload_canvas = FigureCanvasTkAgg(fig, master=self.workload_chart_holder)
        self.workload_canvas.draw()
        widget = self.workload_canvas.get_tk_widget()
        widget.pack(fill="both", expand=True, padx=4, pady=4)
        widget.configure(background="#111827", highlightthickness=0, borderwidth=0)
        self._workload_fig = fig

    def _initialize_responsive_layout(self):
        width = max(self.winfo_width(), 1)
        self._update_responsive_layout(width)

    def _on_window_configure(self, event):
        if event.widget is not self:
            return
        self._pending_width = event.width
        if self._responsive_after:
            try:
                self.after_cancel(self._responsive_after)
            except Exception:
                pass
        self._responsive_after = self.after(120, self._commit_responsive_update)

    def _commit_responsive_update(self):
        self._responsive_after = None
        width = self._pending_width or self.winfo_width()
        self._update_responsive_layout(max(width, 1))

    def _update_responsive_layout(self, width: int):
        mode = "narrow" if width < 900 else "wide"
        if mode != self._layout_mode:
            self._layout_mode = mode
            self._layout_add_form(mode)

        self._apply_scaling(width)

        wrap = max(width - 260, 360)
        if hasattr(self, "bulk_instruction_label"):
            self.bulk_instruction_label.configure(wraplength=wrap)
        if hasattr(self, "bulk_form_help_label"):
            self.bulk_form_help_label.configure(wraplength=wrap)

    def _apply_scaling(self, width: int):
        # User feedback indicated that dynamic scaling at different widths made the
        # interface feel unstable, so keep a consistent 1.0 scale regardless of the
        # window size.
        scale = 1.0

        if self._widget_scale == scale:
            return
        self._widget_scale = scale
        ctk.set_widget_scaling(scale)
        try:
            ctk.set_window_scaling(scale)
        except AttributeError:
            # Older CustomTkinter versions do not expose set_window_scaling
            pass

    # ----------------------- Actions -----------------------
    def refresh_all(self):
        self._refresh_people_options()
        self._refresh_today_list()
        self._refresh_all_list()
        self.status_label.configure(text=f"Tasks: {len(self.store.data['tasks'])}")
        self._refresh_stats()

    def _on_today_search_change(self, *_):
        self._schedule_search_refresh("_today_search_job", self._refresh_today_list)

    def _on_all_search_change(self, *_):
        self._schedule_search_refresh("_all_search_job", self._refresh_all_list)

    def _schedule_search_refresh(self, job_attr: str, callback):
        existing = getattr(self, job_attr, None)
        if existing is not None:
            try:
                self.after_cancel(existing)
            except tk.TclError:
                pass

        def run():
            setattr(self, job_attr, None)
            callback()

        setattr(self, job_attr, self.after(1000, run))

    def _cancel_search_refresh(self, job_attr: str):
        existing = getattr(self, job_attr, None)
        if existing is not None:
            try:
                self.after_cancel(existing)
            except tk.TclError:
                pass
            finally:
                setattr(self, job_attr, None)

    def _clear_search(self, var: tk.StringVar, job_attr: str, refresh_callback):
        if var.get():
            var.set("")
        self._cancel_search_refresh(job_attr)
        refresh_callback()

    def _task_matches_query(self, task: dict, query: str) -> bool:
        if not query:
            return True
        haystacks = [
            task.get("title", ""),
            task.get("description", ""),
            task.get("who_asked", ""),
            task.get("assignee", ""),
            task.get("type", ""),
        ]
        for session in task.get("sessions", []) or []:
            haystacks.append(session.get("note", ""))
        combined = " ".join(text for text in haystacks if text).lower()
        query = query.lower()
        if query in combined:
            return True
        tokens = [token for token in query.split() if token]
        if not tokens:
            return False
        return all(token in combined for token in tokens)

    def _refresh_today_list(self):
        for w in self.today_list.winfo_children():
            w.destroy()
        tasks = self.store.eligible_today()
        tasks.sort(key=sort_key)
        query = getattr(self, "today_search_var", None)
        if query:
            needle = query.get().strip().lower()
            if needle:
                tasks = [t for t in tasks if self._task_matches_query(t, needle)]
        # Show focused first
        focused = [t for t in tasks if t.get("focus")]
        others = [t for t in tasks if not t.get("focus")]

        if focused:
            ctk.CTkLabel(self.today_list, text="Focus ⭐", font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(4,4), padx=6)
            for t in focused:
                self._add_task_card(self.today_list, t)

        ctk.CTkLabel(self.today_list, text="Available Today", font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(12,4), padx=6)
        for t in others:
            self._add_task_card(self.today_list, t)

        if not tasks:
            ctk.CTkLabel(self.today_list, text="No tasks available to start today.").pack(pady=12)

    def _refresh_all_list(self):
        for w in self.all_list.winfo_children():
            w.destroy()
        status = self.status_filter.get()
        if status == "all":
            tasks = self.store.list_tasks()
        else:
            tasks = self.store.list_tasks(status)
        tasks.sort(key=sort_key)
        query = getattr(self, "all_search_var", None)
        if query:
            needle = query.get().strip().lower()
            if needle:
                tasks = [t for t in tasks if self._task_matches_query(t, needle)]
        for t in tasks:
            self._add_task_card(self.all_list, t)
        if not tasks:
            ctk.CTkLabel(self.all_list, text="No tasks to show.").pack(pady=12)

    def _add_task_card(self, parent, task: dict):
        card = TaskCard(parent, task,
                        on_edit=self._open_editor,
                        on_done_toggle=self._toggle_done,
                        on_focus_toggle=self._toggle_focus,
                        on_start_timer=self._start_task_timer,
                        on_log_time=self._log_manual_time,
                        on_postpone=self._postpone_task)
        card.pack(fill="x", padx=12, pady=10)

    def _toggle_done(self, task):
        new_status = "open" if task.get("status") == "done" else "done"
        updates = {"status": new_status}
        if new_status == "done":
            updates["completed_at"] = datetime.now().isoformat(timespec="seconds")
        else:
            updates["completed_at"] = None
        self.store.update_task(task["id"], updates)
        self.refresh_all()

    def _toggle_focus(self, task):
        self.store.update_task(task["id"], {"focus": not bool(task.get("focus"))})
        self.refresh_all()

    def _open_editor(self, task):
        def on_save(updated):
            self.store.update_task(task["id"], updated)
            self.refresh_all()
        TaskEditor(self, task, on_save, self.store.get_people())

    def _start_task_timer(self, task):
        if self.timer_window and self.timer_window.winfo_exists():
            messagebox.showinfo("Timer", "A timer is already running. Please finish or stop it before starting another.")
            self.timer_window.focus()
            return

        def handle_complete(minutes, ended_early):
            self._handle_timer_completion(task.get("id"), minutes, ended_early)

        self.timer_window = PomodoroWindow(self, task, handle_complete, self._on_timer_closed)
        self.timer_window.focus()

    def _on_timer_closed(self):
        self.timer_window = None

    def _handle_timer_completion(self, task_id: int, minutes: int, ended_early: bool):
        self._on_timer_closed()
        if minutes is None:
            return
        if minutes <= 0:
            return
        self.bell()
        task = next((t for t in self.store.data.get("tasks", []) if t.get("id") == task_id), None)
        if not task:
            messagebox.showinfo("Timer", "Task no longer exists.")
            return
        title = task.get("title", "Task")
        if ended_early:
            heading = "Session stopped"
            body = f"Logged {minutes} minute(s) for '{title}'."
        else:
            heading = "Time's up!"
            body = f"{minutes} minute(s) completed for '{title}'."
        messagebox.showinfo(heading, body)
        dialog = SessionLogDialog(
            self,
            title=f"Session recap — {title}",
            preset_minutes=minutes,
            allow_minutes_edit=True,
            prompt="Describe what you accomplished during this focus session:",
        )
        result = dialog.show()
        if result:
            minutes_logged, note = result
        else:
            minutes_logged, note = minutes, ""
        # Preserve the task description and only update the dedicated session log.
        self.store.append_session(task_id, minutes_logged, note)
        self.refresh_all()

    def _log_manual_time(self, task):
        task_id = task.get("id") if task else None
        if not task_id:
            return
        title = task.get("title", "Task")
        dialog = SessionLogDialog(
            self,
            title=f"Log time — {title}",
            preset_minutes=None,
            allow_minutes_edit=True,
            prompt="Enter how long you worked (e.g. 90, 1:30, 1.5h) and describe what happened:",
        )
        result = dialog.show()
        if not result:
            return
        minutes, note = result
        # Manual logging mirrors timer sessions without touching the description field.
        self.store.append_session(task_id, minutes, note)
        self.refresh_all()

    def _postpone_task(self, task):
        task_id = task.get("id") if task else None
        if not task_id:
            return
        dialog = PostponeDialog(self, task)
        days = dialog.show()
        if days is None:
            return
        current_start = parse_date(task.get("start_date", "")) or date.today()
        base = max(current_start, date.today())
        new_date = base + timedelta(days=days)
        self.store.update_task(task_id, {"start_date": new_date.strftime("%Y-%m-%d")})
        self.refresh_all()
        title = task.get("title", "Task")
        messagebox.showinfo(
            "Task postponed",
            f"'{title}' postponed until {new_date.strftime('%Y-%m-%d')}.",
        )

    def _clear_add_form(self):
        self.add_title.delete(0, tk.END)
        self.add_type.set(TASK_TYPES[0])
        self.add_priority.set(PRIORITIES[1])
        self.add_who.set("")
        self.add_assignee.set("")
        self.add_start.set_date(date.today())
        self.add_deadline.set_date(date.today())
        self.add_description.delete("1.0", tk.END)

    def _add_task_from_form(self):
        title = self.add_title.get().strip()
        if not title:
            messagebox.showwarning("Validation", "Title cannot be empty")
            return
        task = {
            "title": title,
            "type": self.add_type.get(),
            "priority": self.add_priority.get(),
            "who_asked": self.add_who.get().strip(),
            "assignee": self.add_assignee.get().strip(),
            "start_date": self.add_start.get_date().strftime('%Y-%m-%d'),
            "deadline": self.add_deadline.get_date().strftime('%Y-%m-%d'),
            "status": "open",
            "focus": False,
            "description": self.add_description.get("1.0", tk.END).strip(),
        }
        self.store.add_task(task)
        self._clear_add_form()
        self.refresh_all()
        self.tabs.set("All Tasks")

    def _bulk_import(self):
        text = self.bulk_text.get("1.0", tk.END).strip()
        if not text:
            self.bulk_status.configure(text="Nothing to import.")
            return
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        added = 0
        for ln in lines:
            task = self._parse_template_line(ln)
            if task and task.get("title"):
                self.store.add_task(task)
                added += 1
        self.bulk_status.configure(text=f"Imported {added} task(s).")
        self.refresh_all()

    def _parse_template_line(self, line: str) -> dict | None:
        """Parse template lines like:
        Make: Title — asked by Alex — start 2025-10-06 — deadline 2025-10-08 — priority High
        Ask: Confirm PT rules — asked by Lena
        """
        # Allow hyphen forms: —, -, --
        # Split head (type:title) and segments (key-value)
        m = re.match(r"^\s*(\w+)\s*:\s*(.+)$", line)
        if not m:
            return None
        ttype = m.group(1).strip().capitalize()
        rest = m.group(2).strip()

        # Split by em-dash or hyphen separators
        parts = re.split(r"\s+[—\-]{1,2}\s+", rest)
        title = parts[0].strip()
        info = parts[1:]

        who = ""
        assignee = ""
        start_s = today_str()
        deadline_s = ""
        pr = "Medium"
        description = ""

        for seg in info:
            s = seg.strip()
            # key: asked by
            m1 = re.match(r"(?i)^asked\s+by\s*:?\s*(.+)$", s)
            if m1:
                who = m1.group(1).strip()
                continue
            # key: assignee / assigned to
            m1b = re.match(r"(?i)^(assignee|assigned\s+to)\s*:?\s*(.+)$", s)
            if m1b:
                assignee = m1b.group(2).strip()
                continue
            # key: start date
            m2 = re.match(r"(?i)^start\s*:?\s*(.+)$", s)
            if m2:
                d = parse_date(m2.group(1).strip())
                if d:
                    start_s = d.strftime('%Y-%m-%d')
                continue
            # key: deadline
            m3 = re.match(r"(?i)^deadline\s*:?\s*(.+)$", s)
            if m3:
                d = parse_date(m3.group(1).strip())
                if d:
                    deadline_s = d.strftime('%Y-%m-%d')
                continue
            # key: priority
            m4 = re.match(r"(?i)^priority\s*:?\s*(high|medium|low)$", s)
            if m4:
                pr = m4.group(1).capitalize()
                continue
            # key: description / notes
            m5 = re.match(r"(?i)^(description|desc|notes?)\s*:?\s*(.+)$", s)
            if m5:
                description = m5.group(2).strip()
                continue

        if ttype not in TASK_TYPES:
            ttype = TASK_TYPES[0]
        if pr not in PRIORITIES:
            pr = PRIORITIES[1]

        return {
            "title": title,
            "type": ttype,
            "priority": pr,
            "who_asked": who,
            "assignee": assignee,
            "start_date": start_s,
            "deadline": deadline_s,
            "status": "open",
            "focus": False,
            "description": description,
        }

    def _copy_bulk_instructions(self):
        try:
            self.clipboard_clear()
            self.clipboard_append(self.bulk_instruction_text)
            self.bulk_status.configure(text="Instructions copied.")
        except Exception:
            self.bulk_status.configure(text="Unable to copy instructions.")

    def _copy_bulk_instructions(self):
        try:
            self.clipboard_clear()
            self.clipboard_append(self.bulk_instruction_text)
            self.bulk_status.configure(text="Instructions copied.")
        except Exception:
            self.bulk_status.configure(text="Unable to copy instructions.")

    def _copy_bulk_instructions(self):
        try:
            self.clipboard_clear()
            self.clipboard_append(self.bulk_instruction_text)
            self.bulk_status.configure(text="Instructions copied.")
        except Exception:
            self.bulk_status.configure(text="Unable to copy instructions.")

    def _copy_bulk_instructions(self):
        try:
            self.clipboard_clear()
            self.clipboard_append(self.bulk_instruction_text)
            self.bulk_status.configure(text="Instructions copied.")
        except Exception:
            self.bulk_status.configure(text="Unable to copy instructions.")

    def _copy_bulk_instructions(self):
        try:
            self.clipboard_clear()
            self.clipboard_append(self.bulk_instruction_text)
            self.bulk_status.configure(text="Instructions copied.")
        except Exception:
            self.bulk_status.configure(text="Unable to copy instructions.")

    def _copy_bulk_instructions(self):
        try:
            self.clipboard_clear()
            self.clipboard_append(self.bulk_instruction_text)
            self.bulk_status.configure(text="Instructions copied.")
        except Exception:
            self.bulk_status.configure(text="Unable to copy instructions.")

    def _copy_bulk_instructions(self):
        try:
            self.clipboard_clear()
            self.clipboard_append(self.bulk_instruction_text)
            self.bulk_status.configure(text="Instructions copied.")
        except Exception:
            self.bulk_status.configure(text="Unable to copy instructions.")

    def _copy_bulk_instructions(self):
        try:
            self.clipboard_clear()
            self.clipboard_append(self.bulk_instruction_text)
            self.bulk_status.configure(text="Instructions copied.")
        except Exception:
            self.bulk_status.configure(text="Unable to copy instructions.")

    def _prompt_focus_selection(self):
        tasks = self.store.eligible_today()
        if not tasks:
            # No eligible tasks; just set the meta date to avoid nagging
            self.store.data["meta"]["last_focus_date"] = today_str()
            self.store.save()
            return
        tasks.sort(key=sort_key)

        def on_confirm(selected_ids: list[int]):
            self.store.set_focus_for_today(selected_ids)
            self.refresh_all()

        FocusDialog(self, tasks, on_confirm)


# -------------------------------
# MAIN
# -------------------------------
if __name__ == "__main__":
    ensure_dirs()
    write_purple_theme_if_missing()

    # Apply dark mode and theme
    ctk.set_appearance_mode("dark")
    try:
        ctk.set_default_color_theme(THEME_FILE)
    except Exception:
        # Fallback to built-in if custom theme fails
        ctk.set_default_color_theme("dark-blue")

    store = TaskStore(DATA_FILE)
    app = TaskFocusApp(store)
    app.mainloop()
