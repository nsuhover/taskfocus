# 🏗️ АРХИТЕКТУРНЫЕ ДИАГРАММЫ

##现ТЕКУЩАЯ СТРУКТУРА (Монолит - 4200 строк)

```
taskfocus.py
│
├─ CONFIG (50 строк)
│  └─ DATA_DIR, TASK_TYPES, PRIORITIES, STATUSES
│
├─ HELPERS (680 строк) ⚠️ ПЕРЕМЕШАНЫ
│  ├─ Date & Time: parse_date(), today_str(), iso_to_date()
│  ├─ Format: format_minutes(), shorten_url_display()
│  ├─ URL: gather_task_links(), _normalize_url()
│  ├─ Parse: parse_minutes_input(), sort_key()
│  ├─ Tkinter: make_textbox_copyable(), configure_fast_scroll()
│  └─ Theme: write_purple_theme_if_missing()
│
├─ TaskStore CLASS (550 строк) 🔴 ЯДРО ДАННЫХ
│  ├─ load() / save() — JSON I/O
│  ├─ add_task() / update_task() / delete_task()
│  ├─ get_task() / list_tasks()
│  ├─ append_session() / update_session()
│  ├─ _task_index: dict[str, dict] — КЕШ ⚠️ РИСК
│  ├─ _sync_plan_completion() — СЛОЖНАЯ ЛОГИКА
│  └─ register_people() / register_labels()
│
├─ GUI CLASSES (1600 строк) 🔴 МОНОЛИТ
│  ├─ TaskCard — карточка в списке (100 строк)
│  ├─ TaskDetailPane — детали + действия (400 строк)
│  ├─ TaskEditorForm — редактирование (200 строк)
│  ├─ LabelsEditor — управление метками (150 строк)
│  ├─ PlanEditorFrame — план-чеклист (100 строк)
│  ├─ SessionLogDialog — логирование времени (100 строк)
│  ├─ SessionEditDialog — редактирование сессии (150 строк)
│  ├─ SessionManagerDialog — менеджер сессий (150 строк)
│  ├─ PostponeDialog — отложение (100 строк)
│  ├─ PomodoroWindow — таймер (150 строк)
│  └─ FocusDialog — выбор фокуса (80 строк)
│
└─ TaskFocusApp CLASS (1500 строк) 🔴 ВИТЯЗВЛОЧКА
   ├─ __init__() — 200 строк смешанной логики
   ├─ _build_today_tab() — 80 строк
   ├─ _build_all_tab() — 80 строк
   ├─ _build_stats_tab() — 100 строк
   ├─ _build_report_tab() — 80 строк
   ├─ _build_add_tab() — 100 строк
   ├─ _build_bulk_tab() — 100 строк
   ├─ refresh_all() / _execute_refresh() — 80 строк ⚠️ СЛОЖНО
   ├─ _refresh_today_list() — 40 строк (ДУБЛИРУЕТ all_list)
   ├─ _refresh_all_list() — 40 строк (ДУБЛИРУЕТ today_list)
   ├─ _on_task_card_selected() — 20 строк
   ├─ _show_preview_for_task() — 40 строк
   ├─ Actions (toggle_done, toggle_focus, save, timer) — 200 строк
   ├─ _refresh_stats() / _render_*_chart() — 300 строк 🔴 ПАМЯТИ
   ├─ _generate_report() — 80 строк
   ├─ _bulk_import() / _parse_template_line() — 100 строк
   ├─ Dialog handlers — 200 строк (callback hell)
   └─ Responsive layout — 60 строк
```

---

## ЦЕЛЕВАЯ СТРУКТУРА (Модульная - ~3500 строк, распределено)

```
taskfocus/
│
├── config.py (50 строк)
│   └─ CONFIG, TASK_TYPES, PRIORITIES, etc.
│
├── data/ (500 строк - СЛОЙ ДАННЫХ)
│   ├─ models.py (50 строк)
│   │  └─ @dataclass Task, Session, PlanItem
│   ├─ store.py (350 строк) 
│   │  └─ class TaskStore — ТОЛЬКО CRUD + persistence
│   ├─ managers.py (100 строк)
│   │  └─ IndexManager — инкапсуляция кеша
│   └─ validators.py (50 строк)
│      └─ Validation rules
│
├── utils/ (400 строк - ПЕРЕИСПОЛЬЗУЕМЫЙ КОД)
│   ├─ dateutils.py (80 строк)
│   │  └─ parse_date(), today_str(), iso_to_date()
│   ├─ formatters.py (60 строк)
│   │  └─ format_minutes(), shorten_url_display()
│   ├─ parsers.py (100 строк)
│   │  └─ parse_minutes_input(), sort_key(), parse_template()
│   ├─ url_utils.py (50 строк)
│   │  └─ gather_task_links(), _normalize_url()
│   └─ tk_utils.py (120 строк)
│      └─ make_textbox_copyable(), configure_fast_scroll()
│
├── app/ (600 строк - БИЗНЕС-ЛОГИКА)
│   ├─ refresh.py (150 строк)
│   │  └─ RefreshController — управляет refresh_all() потоком
│   ├─ actions.py (300 строк)
│   │  └─ ActionHandler — toggle_done, save, timer, etc.
│   ├─ search.py (100 строк)
│   │  └─ SearchEngine — кеш поиска, мэтчинг
│   ├─ charts.py (350 строк)
│   │  └─ ChartRenderer — matplotlib графики (с cleanup)
│   ├─ report.py (150 строк)
│   │  └─ ReportGenerator — отчеты
│   └─ bulk_importer.py (100 строк)
│      └─ BulkImporter — парсинг и импорт
│
├── ui/ (800 строк - UI КОМПОНЕНТЫ)
│   ├─ components/ (800 строк)
│   │  ├─ cards.py (80 строк)
│   │  │  └─ class TaskCard
│   │  ├─ task_detail.py (400 строк)
│   │  │  ├─ class TaskDetailPane (view/edit + State mgmt)
│   │  │  └─ class TaskEditorForm
│   │  ├─ editors.py (250 строк)
│   │  │  ├─ class LabelsEditor
│   │  │  └─ class PlanEditorFrame
│   │  └─ common.py (70 строк)
│   │     └─ Shared UI utilities
│   │
│   ├─ dialogs/ (700 строк)
│   │  ├─ base.py (30 строк)
│   │  │  └─ BaseDialog — common dialog logic
│   │  ├─ session.py (200 строк)
│   │  │  ├─ class SessionLogDialog
│   │  │  └─ class SessionEditDialog
│   │  ├─ session_manager.py (100 строк)
│   │  │  └─ class SessionManagerDialog
│   │  ├─ postpone.py (80 строк)
│   │  │  └─ class PostponeDialog
│   │  ├─ timer.py (150 строк)
│   │  │  └─ class PomodoroWindow
│   │  └─ focus.py (140 строк)
│   │     └─ class FocusDialog
│   │
│   ├─ tabs/ (600 строк)
│   │  ├─ base.py (50 строк)
│   │  │  └─ BaseTab — common tab logic
│   │  ├─ today.py (100 строк)
│   │  │  └─ TodayTasksTab._build()
│   │  ├─ all_tasks.py (100 строк)
│   │  │  └─ AllTasksTab._build()
│   │  ├─ add_task.py (150 строк)
│   │  │  └─ AddTaskTab._build()
│   │  ├─ bulk.py (100 строк)
│   │  │  └─ BulkImportTab._build()
│   │  ├─ stats.py (80 строк)
│   │  │  └─ StatsTab._build()
│   │  └─ report.py (80 строк)
│   │     └─ ReportTab._build()
│   │
│   └─ layout.py (100 строк)
│      └─ ResponsiveLayout — window size → breakpoints
│
├── app/
│   └─ main.py (300 строк) ← Главное приложение (вместо 1500!)
│      └─ class TaskFocusApp
│         ├─ __init__() — инъекция зависимостей
│         ├─ _build_ui() — собирает табы
│         └─ lifecycle methods
│
├── taskfocus.py (100 строк) ← Entry point
│   ├─ ensure_dirs()
│   ├─ write_theme()
│   ├─ set_ctk_theme()
│   └─ if __name__: main()
│
└── tests/ (TBD)
   ├─ test_store.py
   ├─ test_parsers.py
   └─ test_ui.py
```

---

## ГРАФИК ЗАВИСИМОСТЕЙ: ДО vs ПОСЛЕ

### ❌ СЕЙЧАС (СПАГЕТТИ)

```
Клиент (вызов taskfocus.py)
    ↓
┌────────────────────────────────────────┐
│       taskfocus.py (4200 строк)        │
│  ┌──────────────────────────────────┐  │
│  │ TaskFocusApp                     │  │
│  │  ├─ использует TaskStore         │  │
│  │  ├─ использует TaskCard          │  │
│  │  ├─ использует TaskDetailPane    │  │
│  │  ├─ использует все Dialogs       │  │
│  │  ├─ использует все helpers       │  │
│  │  └─ ОЧЕНЬ СПУТАННАЯ ЛОГИКА       │  │
│  └──────────────────────────────────┘  │
│  ┌──────────────────────────────────┐  │
│  │ TaskStore                        │  │
│  │  ├─ использует parse_date()      │  │
│  │  ├─ использует TODAY_LOCAL       │  │
│  │  └─ индексирует вручную          │  │
│  └──────────────────────────────────┘  │
│              JSON файл                   │
└────────────────────────────────────────┘
```

**Проблемы:**
- Все зависит от всего
- Сложно тестировать части
- Трудно найти баги
- Трудно добавлять функции

### ✅ ПОСЛЕ (СЛОИ)

```
Клиент
 ↓
├─ taskfocus.py (Entry point, 100 строк)
   └─ app/main.py (TaskFocusApp, 300 строк)
      ├─ data/store.py (TaskStore) ← **СЛОЙ ДАННЫХ**
      │  └─ JSON файл
      │
      ├─ app/refresh.py (RefreshController) ← **БИЗНЕС-ЛОГИКА**
      ├─ app/actions.py (ActionHandler)
      ├─ app/search.py (SearchEngine)
      ├─ app/charts.py (ChartRenderer)
      ├─ app/report.py (ReportGenerator)
      └─ app/bulk_importer.py
         └─ utils/* ← **ПЕРЕИСПОЛЬЗУЕМАЯ ЛОГИКА**
             ├─ dateutils.py ← parse_date()
             ├─ parsers.py
             ├─ formatters.py
             └─ url_utils.py
      
      └─ ui/ (UI КОМПОНЕНТЫ) ← **ПРЕЗЕНТАЦИОННЫЙ СЛОЙ**
         ├─ components/ (Cards, Forms, etc)
         ├─ dialogs/ (All modals)
         ├─ tabs/ (Tab builders)
         └─ layout.py (Responsive)
```

**Преимущества:**
- Разделение ответственности (Separation of Concerns)
- Легко тестировать отдельно
- Переиспользуемы утилиты
- Ясная архитектура
- Легко добавлять фичи

---

## МАТРИЦА МИГРАЦИИ ПО ФАЙЛАМ

| Текущий | Строк | → | Целевой | Строк | Коммент |
|---------|-------|---|---------|-------|---------|
| taskfocus.py Lines 24-120 | 96 | → | config.py | 50 | Константы |
| taskfocus.py Lines 133-350 | 217 | → | utils/dateutils.py | 80 | Даты |
| taskfocus.py Lines 350-400 | 50 | → | utils/url_utils.py | 50 | URL |
| taskfocus.py Lines 400-450 | 50 | → | utils/formatters.py | 60 | Формат |
| taskfocus.py Lines 450-550 | 100 | → | utils/parsers.py | 100 | Парс |
| taskfocus.py Lines 550-680 | 130 | → | utils/tk_utils.py | 120 | Tkinter |
| taskfocus.py Lines 681-950 | 269 | → | data/store.py | 350 | CRUD |
| taskfocus.py Lines 1000-1200 | 200 | → | ui/components/cards.py | 80 | TaskCard |
| taskfocus.py Lines 1200-1600 | 400 | → | ui/components/task_detail.py | 400 | Detail pane |
| taskfocus.py Lines 1600-1800 | 200 | → | ui/components/editors.py | 250 | Editors |
| taskfocus.py Lines 1800-2000 | 200 | → | ui/dialogs/session.py | 200 | Session dialogs |
| taskfocus.py Lines 2000-2200 | 200 | → | ui/dialogs/* | 300 | Other dialogs |
| taskfocus.py Lines 2800-3000 | 200 | → | ui/tabs/today.py | 100 | Today tab |
| taskfocus.py Lines 3000-3100 | 100 | → | ui/tabs/all_tasks.py | 100 | All tasks tab |
| taskfocus.py Lines 3100-3300 | 200 | → | ui/tabs/add_task.py | 150 | Add task tab |
| taskfocus.py Lines 3500-3600 | 100 | → | ui/tabs/stats.py | 80 | Stats tab |
| taskfocus.py Lines 3700-3800 | 100 | → | ui/tabs/bulk.py | 100 | Bulk tab |
| taskfocus.py Lines 3900-4000 | 100 | → | ui/tabs/report.py | 80 | Report tab |
| taskfocus.py Lines 3200-3500 | 300 | → | app/charts.py | 350 | Matplotlib |
| taskfocus.py Lines 3600-3700 | 100 | → | app/report.py | 150 | Reports |
| taskfocus.py Lines 3800-3900 | 100 | → | app/bulk_importer.py | 100 | Bulk logic |
| taskfocus.py Lines 3540-3650 | 110 | → | app/actions.py | 300 | Actions handlers |
| taskfocus.py Lines 3650-3750 | 100 | → | app/refresh.py | 150 | Refresh logic |
| taskfocus.py Lines 3750-3900 | 150 | → | app/search.py | 100 | Search |
| **МОНОЛИТ** | **4200** | → | **Модулирован** | ~3500 | ✅ Распределено |

---

## ДИАГРАММА СОСТОЯНИЙ: TaskDetailPane (The Most Complex Component)

```
                        ┌──────────────┐
                        │    LOADING   │
                        └──────┬───────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   show_task(task)    │
                    │ (task is not None)   │
                    └──────┬───────────────┘
                           │
        ┌──────────────────┴──────────────────┐
        ▼                                      ▼
   ┌─────────────┐                    ┌──────────────┐
   │   EMPTY     │                    │    VIEWING   │
   │ mode=empty  │                    │ mode=view    │
   │             │                    │              │
   │[placeholder]│                    │[details pane]│
   │             │                    │ [actions]    │
   └─────────────┘                    │ [description]│
        │                             │ [plan]       │
        │                             │ [sessions]   │
        │                             │ [links]      │
        │                             └──┬─────┬──┬──┘
        │                                │     │  │
        │     Edit clicked────────────────┘     │  │
        │                                       │  │
        │     ┌─────────────────────────────────┘  │
        │     ▼                                     │
        │  ┌──────────────┐                        │
        │  │    EDITING   │                        │
        │  │ mode=edit    │                        │
        │  │              │                        │
        │  │[edit form]   │                        │
        │  │[title]       │                        │
        │  │[fields...]   │                        │
        │  └──┬────────┬──┘                        │
        │     │        │                           │
        │     │ Cancel │ Save                      │
        │     │ (done) │ (validate + store.update) │
        │     └────┬───┴────────────────┐          │
        │          │                    ▼          │
        │          │              [refresh_all()   │
        │          │               data_changed]   │
        │          └───────────┬──────────────┘    │
        │                      ▼                   │
        └─────────────────► (update cache,        │
                            re-render VIEWING)    │
                                      │           │
                          show_task(None)◄────────┘
                                      │
                                      ▼
                          ┌──────────────────┐
                          │ show_task cleared│
                          │ back to EMPTY    │
                          └──────────────────┘
```

**Текущая проблема**: Mode transitions смешаны с UI рендерингом
**Решение**: Implement State Pattern с явными переходами

---

## ПЛАН ОТКАТА (Emergency!)

Если что-то сломалось на какой-то фазе:

```
Phase 0 breaks? → git checkout taskfocus.py
Phase 1 breaks? → git revert <last_commit_in_phase_1>
Phase 2 breaks? → Keep backup data/store_original.py
Phase 3 breaks? → Remove all ui/ imports
Phase 4 breaks? → Keep TaskFocusApp(store) interface working
Phase 5 breaks? → Disable new features, keep core running
```

**Golden Rule**: `json.load(DATA_FILE)` всегда must work!

---

## МЕТРИКИ: БЫЛО vs БУДЕТ

| Метрика | Текущее | После рефакторинга | Улучшение |
|---------|---------|-------------------|-----------|
| Размер main file | 4200 строк | 100 строк | **-97%** |
| Макс строк в классе | 1500 | 400 | **-73%** |
| Циклическ. зависимост | Много | 0 | ✅ |
| Тестируемость | 10% | 70% | **+600%** |
| Время на добавление фичи | ~200 строк везде | <50 в одном модуле | **-75%** |
| Время поиска бага | 30 мин | 5 мин | **-83%** |

Успех! 🎉
