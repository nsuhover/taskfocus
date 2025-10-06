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

import json
import os
import sys
import re
from datetime import datetime, date

import tkinter as tk
from tkinter import messagebox, simpledialog

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
    def __init__(self, master, task: dict, on_edit, on_done_toggle, on_focus_toggle, on_start_timer):
        super().__init__(master)
        self.task = task
        self.on_edit = on_edit
        self.on_done_toggle = on_done_toggle
        self.on_focus_toggle = on_focus_toggle
        self.on_start_timer = on_start_timer

        self.configure(padx=12, pady=12)

        # Left labels container
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w")

        title_row = ctk.CTkFrame(left, fg_color="transparent")
        title_row.pack(anchor="w")

        focus_prefix = "⭐ " if task.get("focus") else ""
        self.title_label = ctk.CTkLabel(title_row, text=f"{focus_prefix}{task.get('title','(no title)')}", font=("Segoe UI", 16, "bold"))
        self.title_label.pack(side="left", padx=(0, 6))

        # Priority badge
        pr = task.get("priority", "Medium")
        pr_color = {
            "High": "#F97316",  # orange
            "Medium": "#A78BFA",  # purple-light
            "Low": "#64748B"     # slate
        }.get(pr, "#A78BFA")
        pr_badge = ctk.CTkLabel(title_row, text=pr, fg_color=pr_color, text_color="#000000", corner_radius=8, padx=8, pady=2)
        pr_badge.pack(side="left")

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
        # Overdue visual hint
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
        meta_line = ctk.CTkLabel(left, text=meta_text, justify="left")
        meta_line.pack(anchor="w", pady=(6, 0))

        # Right buttons
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=0, column=1, sticky="e")

        focus_text = "Unfocus" if task.get("focus") else "Focus ⭐"
        self.focus_btn = ctk.CTkButton(btns, text=focus_text, command=lambda: self.on_focus_toggle(task))
        self.focus_btn.pack(side="left", padx=6)

        self.timer_btn = ctk.CTkButton(btns, text="Start Timer", command=lambda: self.on_start_timer(task))
        self.timer_btn.pack(side="left", padx=6)

        self.edit_btn = ctk.CTkButton(btns, text="Edit", command=lambda: self.on_edit(task))
        self.edit_btn.pack(side="left", padx=6)

        done_text = "Mark Open" if task.get("status") == "done" else "Mark Done"
        self.done_btn = ctk.CTkButton(btns, text=done_text, command=lambda: self.on_done_toggle(task))
        self.done_btn.pack(side="left", padx=6)

        self.grid_columnconfigure(0, weight=1)


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
        self.start_date = DateEntry(container, date_pattern='yyyy-mm-dd', width=18)
        self.start_date.grid(row=7, column=0, sticky="ew", pady=(0,8))
        sd = parse_date(task.get("start_date", "")) or date.today()
        self.start_date.set_date(sd)

        ctk.CTkLabel(container, text="Deadline").grid(row=6, column=1, sticky="w")
        self.deadline = DateEntry(container, date_pattern='yyyy-mm-dd', width=18)
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
        self.history_box.configure(state="disabled")

        # Status + Focus
        ctk.CTkLabel(container, text="Status").grid(row=12, column=0, sticky="w")
        self.status_menu = ctk.CTkOptionMenu(container, values=STATUSES)
        self.status_menu.grid(row=13, column=0, sticky="ew", pady=(0,8))
        self.status_menu.set(task.get("status", "open"))

        self.focus_var = tk.BooleanVar(value=task.get("focus", False))
        self.focus_chk = ctk.CTkCheckBox(container, text="Focus for Today", variable=self.focus_var)
        self.focus_chk.grid(row=13, column=1, sticky="w")

        # Buttons
        btns = ctk.CTkFrame(container, fg_color="transparent")
        btns.grid(row=14, column=0, columnspan=2, sticky="e", pady=(8,0))
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
        self.minsize(950, 600)
        self.people_options = self.store.get_people()
        self.timer_window = None

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
        self.add_tab = self.tabs.add("Add Task")
        self.bulk_tab = self.tabs.add("Bulk Import")

        # Build each tab
        self._build_today_tab()
        self._build_all_tab()
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

        # List
        self.all_list = ctk.CTkScrollableFrame(self.all_tab)
        self.all_list.pack(fill="both", expand=True)

    def _build_add_tab(self):
        container = ctk.CTkFrame(self.add_tab)
        container.pack(fill="both", expand=True, padx=12, pady=12)

        # Title
        ctk.CTkLabel(container, text="Title").grid(row=0, column=0, sticky="w")
        self.add_title = ctk.CTkEntry(container)
        self.add_title.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0,8))

        # Type & Priority
        ctk.CTkLabel(container, text="Type").grid(row=2, column=0, sticky="w")
        self.add_type = ctk.CTkOptionMenu(container, values=TASK_TYPES)
        self.add_type.grid(row=3, column=0, sticky="ew", pady=(0,8))
        self.add_type.set(TASK_TYPES[0])

        ctk.CTkLabel(container, text="Priority").grid(row=2, column=1, sticky="w")
        self.add_priority = ctk.CTkOptionMenu(container, values=PRIORITIES)
        self.add_priority.grid(row=3, column=1, sticky="ew", pady=(0,8))
        self.add_priority.set(PRIORITIES[1])

        # Who asked & Assignee
        ctk.CTkLabel(container, text="Who asked").grid(row=4, column=0, sticky="w")
        self.add_who = ctk.CTkComboBox(container, values=self._people_option_values(), justify="left")
        self.add_who.grid(row=5, column=0, sticky="ew", pady=(0,8))
        self.add_who.set("")

        ctk.CTkLabel(container, text="Assignee").grid(row=4, column=1, sticky="w")
        self.add_assignee = ctk.CTkComboBox(container, values=self._people_option_values(), justify="left")
        self.add_assignee.grid(row=5, column=1, sticky="ew", pady=(0,8))
        self.add_assignee.set("")

        # Dates
        ctk.CTkLabel(container, text="Start Date").grid(row=6, column=0, sticky="w")
        self.add_start = DateEntry(container, date_pattern='yyyy-mm-dd', width=18)
        self.add_start.grid(row=7, column=0, sticky="ew", pady=(0,8))
        self.add_start.set_date(date.today())

        ctk.CTkLabel(container, text="Deadline").grid(row=6, column=1, sticky="w")
        self.add_deadline = DateEntry(container, date_pattern='yyyy-mm-dd', width=18)
        self.add_deadline.grid(row=7, column=1, sticky="ew", pady=(0,8))
        self.add_deadline.set_date(date.today())

        # Description
        ctk.CTkLabel(container, text="Description").grid(row=8, column=0, columnspan=2, sticky="w")
        self.add_description = ctk.CTkTextbox(container, height=160)
        self.add_description.grid(row=9, column=0, columnspan=2, sticky="nsew", pady=(0,8))

        # Buttons
        btns = ctk.CTkFrame(container, fg_color="transparent")
        btns.grid(row=10, column=0, columnspan=2, sticky="e")
        ctk.CTkButton(btns, text="Clear", command=self._clear_add_form).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Add Task", command=self._add_task_from_form).pack(side="left", padx=6)

        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(9, weight=1)

    def _build_bulk_tab(self):
        container = ctk.CTkFrame(self.bulk_tab)
        container.pack(fill="both", expand=True, padx=12, pady=12)

        help_text = (
            "Paste tasks using this simple template (one per line):\n"
            "Make: Write PT summary — asked by Alex — start 2025-10-06 — deadline 2025-10-08 — priority High\n"
            "Ask: Confirm PT rules with Devs — asked by Lena\n\n"
            "Supported keys: asked by, start, deadline, priority.\n"
            "Dates: yyyy-mm-dd or dd.mm.yyyy; Priority: High/Medium/Low."
        )
        ctk.CTkLabel(container, text=help_text, justify="left").pack(anchor="w", pady=(0,8))

        self.bulk_text = ctk.CTkTextbox(container, height=320)
        self.bulk_text.pack(fill="both", expand=True)

        btns = ctk.CTkFrame(container, fg_color="transparent")
        btns.pack(fill="x", pady=(8,0))
        self.bulk_status = ctk.CTkLabel(btns, text="")
        self.bulk_status.pack(side="left")
        ctk.CTkButton(btns, text="Import", command=self._bulk_import).pack(side="right")

    # ----------------------- Actions -----------------------
    def refresh_all(self):
        self._refresh_people_options()
        self._refresh_today_list()
        self._refresh_all_list()
        self.status_label.configure(text=f"Tasks: {len(self.store.data['tasks'])}")

    def _refresh_today_list(self):
        for w in self.today_list.winfo_children():
            w.destroy()
        tasks = self.store.eligible_today()
        tasks.sort(key=sort_key)
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
        for t in tasks:
            self._add_task_card(self.all_list, t)
        if not tasks:
            ctk.CTkLabel(self.all_list, text="No tasks to show.").pack(pady=12)

    def _add_task_card(self, parent, task: dict):
        card = TaskCard(parent, task,
                        on_edit=self._open_editor,
                        on_done_toggle=self._toggle_done,
                        on_focus_toggle=self._toggle_focus,
                        on_start_timer=self._start_task_timer)
        card.pack(fill="x", padx=8, pady=8)

    def _toggle_done(self, task):
        new_status = "open" if task.get("status") == "done" else "done"
        self.store.update_task(task["id"], {"status": new_status})
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

        def handle_complete(minutes):
            self._handle_timer_completion(task.get("id"), minutes)

        self.timer_window = PomodoroWindow(self, task, handle_complete, self._on_timer_closed)
        self.timer_window.focus()

    def _on_timer_closed(self):
        self.timer_window = None

    def _handle_timer_completion(self, task_id: int, minutes: int):
        self._on_timer_closed()
        self.bell()
        task = next((t for t in self.store.data.get("tasks", []) if t.get("id") == task_id), None)
        if not task:
            messagebox.showinfo("Timer", "Task no longer exists.")
            return
        title = task.get("title", "Task")
        messagebox.showinfo("Time's up!", f"{minutes} minute(s) completed for '{title}'.")
        note = simpledialog.askstring("What did you do?", "Describe what you accomplished during this focus session:")
        if note is None:
            note = ""
        else:
            note = note.strip()
        self.store.append_session(task_id, minutes, note)
        self.refresh_all()

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

        if ttype not in TASK_TYPES:
            ttype = TASK_TYPES[0]
        if pr not in PRIORITIES:
            pr = PRIORITIES[1]

        return {
            "title": title,
            "type": ttype,
            "priority": pr,
            "who_asked": who,
            "assignee": "",
            "start_date": start_s,
            "deadline": deadline_s,
            "status": "open",
            "focus": False,
            "description": "",
        }

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
