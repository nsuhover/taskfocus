# 🔄 ПЛАН РЕФАКТОРИНГА LEGACY-СКРИПТА TaskFocus
## Стратегия миграции с минимальным риском

---

## 1️⃣ АНАЛИЗ ЛОГИЧЕСКИХ ЗОН ОТВЕТСТВЕННОСТИ

### **Зона 1: Конфигурация & Инициализация**
```
Строки: 24-120
Ответственность: Константы, настройки пути, создание темы
Статус: STABLE - минимальные измения требуются
```

### **Зона 2: Утилиты (680 строк)**
**2.1 Date/Time utilities**
- `parse_date()`, `today_str()`, `parse_session_timestamp()`, `iso_to_date()`
- Используется: везде (тип: Date parser)
- **Выделить в**: `dateutils.py`

**2.2 Format utilities**
- `format_minutes()`, `shorten_url_display()`, `_normalize_url()`
- **Выделить в**: `formatters.py`

**2.3 Text/URL utilities**
- `gather_task_links()`, `URL_REGEX`, `_normalize_url()`
- **Выделить в**: `url_utils.py`

**2.4 Input parsing**
- `parse_minutes_input()`, `PRIORITY_ORDER`, `sort_key()`
- **Выделить в**: `parsers.py`

**2.5 Tkinter utilities**
- `make_textbox_copyable()`, `configure_fast_scroll()`, `create_dark_date_entry()`
- **Выделить в**: `tk_utils.py`

### **Зона 3: Слой данных (TaskStore)**
```
Строки: 393-903
Ответственность: JSON I/O, CRUD, индексирование, синхронизация плана
Риск: ВЫСОКИЙ - индексирование может потеряться из синхронизации
```

**Подкомпоненты**:
- `TaskStore.load/save` - сериализация JSON
- `TaskStore._task_index` - кеш по ID (точка синхронизации)
- `TaskStore.add_task/update_task/delete_task` - CRUD
- `TaskStore._merge_plan_items()` - план-фиксирование (очень сложно)
- `TaskStore.append_session()` - логирование времени
- `TaskStore.register_people/labels` - реестры

**Выделить в**: `data/store.py` (основной модуль)

### **Зона 4: GUI компоненты (1600 строк)**

**Компонент 4.1: TaskCard**
- Визуализация карточки в списке
- **Выделить в**: `ui/cards.py`

**Компонент 4.2: TaskDetailPane + TaskEditorForm**
- Просмотр и редактирование задачи
- Сложная логика UI состояния (view/edit режимы)
- **Выделить в**: `ui/task_detail.py`

**Компонент 4.3: LabelsEditor + PlanEditorFrame**
- Управление метками и планом
- Относительно независимы
- **Выделить в**: `ui/editors.py`

**Компонент 4.4: Диалоговые окна**
- SessionLogDialog, SessionEditDialog, SessionManagerDialog
- PostponeDialog, PomodoroWindow, FocusDialog
- Выделить в**: `ui/dialogs/` (отдельный модуль для каждого)

### **Зона 5: Главное приложение (TaskFocusApp)**
```
Строки: 2850-4200
Ответственость: Tab-управление, рефреш-механизм, действия, интеграция
Риск: КРИТИЧЕСКИЙ - состояние разбросано по атрибутам
```

**Подсистемы**:
- Tab builders (6 вкладок) - **выделить в** `ui/tabs/`
- Refresh механизм (`refresh_all`, `_execute_refresh`) - **выделить в** `app/refresh_controller.py`
- Action handlers (toggle, save, timer, etc) - **выделить в** `app/actions.py`
- Search & cache - **выделить в** `app/search.py`
- Statistics rendering - **выделить в** `app/stats_charts.py`
- Report generation - **выделить в** `app/report_generator.py`
- Bulk import parser - **выделить в** `app/bulk_importer.py`
- Layout & responsive - **выделить в** `ui/responsive_layout.py`

---

## 2️⃣ НАЙДЕННЫЕ ПОВТОРЯЮЩИЕСЯ ПАТТЕРНЫ

### **Паттерн A: Dialog + Callback Pattern**
**Найдено в**: `_start_task_timer()`, `_log_manual_time()`, `_manage_sessions()`, `_postpone_task()`

```python
# Текущая структура:
def action(self, task):
    dialog = SomeDialog(self, ...)
    result = dialog.show()
    if result:
        # обработка
        self.store.update_*()
        self.refresh_all()
```

**Улучшение**: Создать `DialogController` для инкапсуляции

### **Паттерн B: List Refresh Pattern**
**Найдено в**: `_refresh_today_list()`, `_refresh_all_list()`

```python
# Текущая структура:
def refresh_list(self, container):
    body = self._list_body(container)
    for w in body.winfo_children(): w.destroy()
    tasks = self.store.list_tasks(...)
    tasks.sort(key=sort_key)
    # apply filter
    for t in tasks:
        self._add_task_card(body, t)
```

**Улучшение**: Абстрактный `ListRefresher`, переиспользуемый для разных контейнеров

### **Паттерн C: State Invalidation Pattern**
**Найдено в**: `_stats_dirty`, `_search_cache_dirty`, `_labels_dirty`

```python
# Текущая структура:
if data_changed:
    self._stats_dirty = True
    self._search_cache_dirty = True
    self._labels_dirty = True

# Later...
if self._stats_dirty:
    self._refresh_stats()
    self._stats_dirty = False
```

**Улучшение**: Создать `InvalidationManager` для управления флагами

### **Паттерн D: Date Parsing Everywhere**
**Найдено в**: 20+ мест вызывают `parse_date()`

**Улучшение**: `DateValidator` класс с типизацией

### **Паттерн E: Form Validation Pattern**
**Найдено в**: `get_payload()`, `_add_task_from_form()`, `_parse_template_line()`

**Улучшение**: `FormValidator` + `FieldValidator` классы

### **Паттерн F: Events from UI to Store**
**Найдено в**: Множество callbacks (`on_toggle_done`, `on_save`, `on_plan_toggle`)

**Улучшение**: Event bus / Observer pattern

---

## 3️⃣ РЕКОМЕНДУЕМЫЕ МОДУЛИ И ФУНКЦИИ

### **Структура директорий после рефакторинга**
```
taskfocus/
├── taskfocus.py          # Главный entry point (100 строк)
├── config.py             # Константы и конфиг (50 строк)
├── data/
│   ├── __init__.py
│   ├── store.py          # TaskStore класс
│   ├── models.py         # Task, Session, PlanItem dataclasses
│   └── validators.py     # Data validation
├── utils/
│   ├── dateutils.py      # Работа с датами
│   ├── formatters.py     # Форматирование
│   ├── parsers.py        # Парсинг ввода
│   ├── url_utils.py      # URL обработка
│   └── tk_utils.py       # Tkinter помощники
├── app/
│   ├── __init__.py
│   ├── main.py           # TaskFocusApp класс (разбить на 400-500 строк)
│   ├── refresh.py        # Refresh механизм
│   ├── actions.py        # Action handlers (toggle, save, etc)
│   ├── search.py         # Поиск и кеширование
│   └── report.py         # Report generation
├── ui/
│   ├── __init__.py
│   ├── components/
│   │   ├── cards.py      # TaskCard
│   │   ├── task_detail.py    # TaskDetailPane, TaskEditorForm
│   │   ├── editors.py    # LabelsEditor, PlanEditorFrame
│   │   └── common.py     # Общие компоненты
│   ├── dialogs/
│   │   ├── __init__.py
│   │   ├── session.py    # SessionLogDialog, SessionEditDialog
│   │   ├── session_manager.py # SessionManagerDialog
│   │   ├── postpone.py   # PostponeDialog
│   │   ├── timer.py      # PomodoroWindow
│   │   └── focus.py      # FocusDialog
│   ├── tabs/
│   │   ├── __init__.py
│   │   ├── today.py      # Today's Tasks tab
│   │   ├── all_tasks.py  # All Tasks tab
│   │   ├── add_task.py   # Add Task tab
│   │   ├── bulk.py       # Bulk Import tab
│   │   └── report.py     # Report tab
│   └── layout.py         # Responsive layout
└── tests/               # Unit tests
    ├── test_store.py
    ├── test_parsers.py
    └── test_ui.py
```

---

## 4️⃣ САМЫЕ РИСКОВАННЫЕ МЕСТА

### **🔴 РИСК 1: TaskStore._task_index синхронизация**
**Проблема**: Кеш ID->task может рассинхронизироваться
**Где**: `TaskStore._normalize_task_key()`, `_index_task()`, `_rebuild_index()`
**Решение**: 
- Добавить assertions при обновлении
- Создать `IndexManager` для инкапсуляции логики

### **🔴 РИСК 2: Plan-Session Cross-references**
**Проблема**: `_sync_plan_completion()`, `_reconcile_plan_sessions()` - сложная логика
**Где**: TaskStore строки 640-680
**Решение**:
- Документировать инварианты
- Добавить tests для синхронизации
- Рассмотреть денормализацию структуры

### **🔴 РИСК 3: UI State Management в TaskDetailPane**
**Проблема**: Сложность mode switching (view/edit), сигнатуры для оптимизации
**Где**: TaskDetailPane строки 1300-1800
**Решение**:
- Использовать State Pattern
- Отделить view-state от edit-state

### **РИСК 4: ~~Matplotlib Canvas Lifecycle~~ УДАЛЕН**
~~**Проблема**: Создание/уничтожение canvas в `_render_*_chart()` может утечь память~~
~~**Решение**: Явное управление cleanup~~
**То, что урегулировано**: Statistics tab и все matplotlib графики полностью удалены

### **🟡 РИСК 5: Global RefreshJob Scheduling**
**Проблема**: `_refresh_job`, `_today_search_job` - без структуры
**Где**: TaskFocusApp атрибуты
**Решение**:
- Создать `JobScheduler` для управления after() вызовами

### **🟡 РИСК 6: Responsive Layout Heuristics**
**Проблема**: Размер 900px - магическая константа, не адекватна всем экранам
**Где**: `_update_responsive_layout()`
**Решение**:
- Конфигурируемые breakpoints
- Медиа-запросы как в web

---

## 5️⃣ ПОШАГОВЫЙ ПЛАН МИГРАЦИИ (МИНИМАЛЬНЫЙ РИСК)

### **ФАЗА 0: Подготовка (День 1)**
- [ ] Создать git branch `refactor/modularize`
- [ ] Создать `tests/` папку с базовыми тестами для TaskStore
- [ ] Убедиться, что текущий скрипт работает без ошибок
- [ ] Задокументировать текущее поведение (особенно plan-sync логику)

### **ФАЗА 1: Извлечение утилит (Дни 2-3)**
**Цель**: Проверить, что небольшие, независимые модули работают

- [ ] Шаг 1.1: Создать `utils/dateutils.py`
  - Переместить: `parse_date()`, `today_str()`, `parse_session_timestamp()`, `iso_to_date()`
  - Написать unit tests
  - Проверить в главном скрипте
  
- [ ] Шаг 1.2: Создать `utils/formatters.py`
  - Переместить: `format_minutes()`, `shorten_url_display()`
  - Тесты
  
- [ ] Шаг 1.3: Создать `utils/url_utils.py`
  - Переместить: URL-related функции
  - Тесты
  
- [ ] Шаг 1.4: Создать `utils/parsers.py`
  - Переместить: `parse_minutes_input()`, `sort_key()`, `PRIORITY_ORDER`
  - Тесты

- [ ] Шаг 1.5: Создать `utils/tk_utils.py`
  - Переместить: `make_textbox_copyable()`, `configure_fast_scroll()`, `create_dark_date_entry()`
  - **Осторожно**: Эти функции зависят от CustomTkinter, проверить импорты
  
**Контрольная точка**: Главный скрипт должен работать идентично, только импорты поменялись

### **ФАЗА 2: Извлечение TaskStore (Дни 4-5)**
**Цель**: Изолировать слой данных

- [ ] Шаг 2.1: Создать `data/models.py` с dataclasses
  ```python
  @dataclass
  class Task: ...
  @dataclass
  class Session: ...
  @dataclass
  class PlanItem: ...
  @dataclass
  class TaskStore: ...
  ```
  
- [ ] Шаг 2.2: Переместить `TaskStore` класс в `data/store.py`
  - Обновить импорты в main
  - Запустить тесты
  
- [ ] Шаг 2.3: **Создать IndexManager** для управления `_task_index`
  - Инкапсулировать логику нормализации
  - Добавить assertions для синхронизации
  
- [ ] Шаг 2.4: **Документировать план-синхронизацию**
  - Прописать инварианты
  - Добавить комментарии к `_sync_plan_completion()`

**Контрольная точка**: Все CRUD операции работают, плюс новые тесты pass

### **ФАЗА 3: Извлечение GUI компонентов (Дни 6-8)**
**Цель**: Разбить монолитный GUI на компоненты

- [ ] Шаг 3.1: Создать `ui/components/cards.py` с TaskCard
  - Переместить класс
  - Убедиться, что он не зависит от TaskFocusApp напрямую
  
- [ ] Шаг 3.2: Создать `ui/components/task_detail.py` с TaskDetailPane
  - Это сложно! TaskDetailPane зависит от множества callbacks
  - Использовать Dependency Injection для callbacks
  - Добавить abstractions для store методов
  
- [ ] Шаг 3.3: Создать `ui/components/editors.py` с LabelsEditor, PlanEditorFrame
  
- [ ] Шаг 3.4: Создать `ui/dialogs/` модули
  - `session.py`: SessionLogDialog, SessionEditDialog
  - `session_manager.py`: SessionManagerDialog
  - `postpone.py`: PostponeDialog
  - `timer.py`: PomodoroWindow
  - `focus.py`: FocusDialog
  
  **Внимание**: Dialogs возвращают результаты, надо проверить contracts

**Контрольная точка**: Все компоненты импортируются, но еще вызываются из main

### **ФАЗА 4: Разбиение главного приложения (Дни 9-12)**
**Цель**: Модульное главное приложение

- [ ] Шаг 4.1: Создать `app/refresh.py` с RefreshController
  - Переместить логику `refresh_all()`, `_execute_refresh()`, флаги грязного состояния
  - Инкапсулировать job scheduling
  
- [ ] Шаг 4.2: Создать `app/actions.py` с ActionHandlers
  - Переместить: `_toggle_done()`, `_toggle_focus()`, `_save_task_changes()`, `_start_task_timer()`, etc.
  - Создать класс `ActionHandler` с методами
  - Заинжектировать store и UI callbacks
  
- [ ] Шаг 4.3: Создать `app/search.py` с SearchEngine
  - Переместить: `_rebuild_search_cache()`, `_task_search_blob()`, `_task_matches_query()`
  - Управлять `_search_cache` состоянием
  
- [ ] ~~Шаг 4.4: Создать `app/charts.py` с ChartRenderer~~ **УДАЛЕНО**
  - ~~Переместить: `_refresh_stats()`, `_render_time_chart_for_period()`, `_render_burn_chart()`, `_render_workload_chart()`~~
  - **Решение**: Statistics tab полностью удален
  
- [ ] Шаг 4.5: Создать `app/report.py` с ReportGenerator
  - Переместить: `_generate_report()`, `_copy_report()`, `_set_report_text()`
  
- [ ] Шаг 4.6: Создать `app/bulk_importer.py` с BulkImporter
  - Переместить: `_bulk_import()`, `_parse_template_line()`
  
- [ ] Шаг 4.7: Создать `ui/tabs/` модули
  - `today.py`: `_build_today_tab()`, `_refresh_today_list()`
  - `all_tasks.py`: `_build_all_tab()`, `_refresh_all_list()`
  - `add_task.py`: `_build_add_tab()`, `_layout_add_form()`, `_clear_add_form()`, `_add_task_from_form()`
  - `bulk.py`: `_build_bulk_tab()`
  - `stats.py`: `_build_stats_tab()`
  - `report.py`: `_build_report_tab()`
  
- [ ] Шаг 4.8: Создать `ui/layout.py` с ResponsiveLayout
  - Переместить: `_initialize_responsive_layout()`, `_on_window_configure()`, `_update_responsive_layout()`
  
- [ ] Шаг 4.9: **Переписать TaskFocusApp главный класс**
  - Переместить tab-builders в отдельные функции/классы
  - Заинжектировать контроллеры и сервисы
  - Сократить с 1500 строк до 300 строк композиции
  
  ```python
  class TaskFocusApp(ctk.CTk):
      def __init__(self, store):
          super().__init__()
          
          # Инъекция зависимостей
          self.store = store
          self.refresh_ctrl = RefreshController(store)
          self.actions = ActionHandlers(store, self)
          self.search = SearchEngine(store)
          self.charts = ChartRenderer()
          self.report = ReportGenerator(store)
          self.importer = BulkImporter()
          
          # Построение UI
          self._build_header()
          self.tabs = self._build_tabs()
          
          # Начальный рефреш
          self.refresh_ctrl.refresh_all(immediate=True)
  ```

**Контрольная точка**: Главное приложение остается функциональным, тесты pass

### **ФАЗА 5: Рефакторинг и оптимизация (Дни 13-15)**
**Цель**: Улучшить архитектуру

- [ ] Шаг 5.1: Применить State Pattern к TaskDetailPane
  - Инкапсулировать view/edit переходы
  
- [ ] Шаг 5.2: Создать Event Bus для UI->Store коммуникации
  - Заменить некоторые callbacks на события
  
- [ ] Шаг 5.3: Добавить logging в критические места
  - Store индексирование
  - Refresh cycle
  - Dialog results
  
- [ ] Шаг 5.4: Оптимизировать Matplotlib canvas lifecycle
  - Добавить контекст-менеджеры для cleanup
  
- [ ] Шаг 5.5: Документировать API каждого модуля
  - README для каждой папки
  - Type hints где нужно

- [ ] Шаг 5.6: Расширить test coverage
  - Unit tests для store операций
  - Integration tests для UI actions

**Контрольная точка**: Полная фиддфункциональность + документация

### **ФАЗА 6: Финализация (День 16)**
- [ ] Проверить всю функциональность вручную
- [ ] Убедиться, что JSON сохраняется корректно
- [ ] Перенести любые оставшиеся magic strings в константы
- [ ] Merge в main branch
- [ ] Создать релиз notes

---

## 6️⃣ ПРОВЕРОЧНЫЕ ЛИСТЫ ПО ФАЗАМ

### **Контрольная точка ФАЗА 1**
```
✓ Главный скрипт запускается без ошибок
✓ Все datetime операции работают
✓ Форматирование времени корректно
✓ URL парсинг работает
✓ Ввод минут парсится правильно
```

### **Контрольная точка ФАЗА 2**
```
✓ TaskStore CRUD операции работают идентично
✓ JSON загружается/сохраняется корректно
✓ Task index не рассинхронизируется
✓ План-синхронизация логика работает
✓ Sessions append/update работают
```

### **Контрольная точка ФАЗА 3**
```
✓ Все компоненты импортируются
✓ TaskCard рендерится в списках
✓ TaskDetailPane открывается при выборе
✓ Диалоги открываются и закрываются
✓ Нет утечек памяти (проверить с psutil)
```

### **Контрольная точка ФАЗА 4**
```
✓ Refresh механизм работает после изменений
✓ Поиск находит задачи
✓ Графики рендерятся (если matplotlib установлен)
✓ Отчет генерируется корректно
✓ Bulk import парсит строки правильно
✓ Responsive layout переключается при изменении размера
```

### **Контрольная точка ФАЗА 5**
```
✓ State transitions в TaskDetailPane корректны
✓ Event bus доставляет события
✓ Logging помогает отладке
✓ Canvas cleanup происходит
✓ Документация полная
✓ Tests pass на 80%+ coverage
```

---
## ИЗМЕНЕНИЯ ИЗ-ЗА УДАЛЕНИЯ STATISTICS

**Что убирается**:
- `_build_stats_tab()` — весь tabs код (~100 строк)
- `_refresh_stats()` — refresh контроллер (~30 строк)
- `_render_time_chart_for_period()` — ~350 строк
- `_render_burn_chart()` — ~150 строк
- `_render_workload_chart()` — ~150 строк
- matplotlib импорты и MATPLOTLIB_AVAILABLE флаг (~50 строк)
- `ui/tabs/stats.py` модуль — полностью
- `app/charts.py` модуль — полностью
- Требуемые зависимости: matplotlib, numpy (если использовались)

**Сэкономлено**: ~800 строк | **Зависимостей на 1 меньше** | **Скорость стартапа выше**

**У пользователей остается**: Логирование времени в сессиях (SessionLogDialog) и отчеты (ReportTab) — без визуалних графиков

---
## 7️⃣ ПОТЕНЦИАЛЬНЫЕ ПРОБЛЕМЫ И РЕШЕНИЯ

### **Проблема A: CustomTkinter импорты в modules**
**Симптом**: ImportError при импорте tk_utils в другие модули
**Решение**: Отложить импорты, использовать TYPE_CHECKING
```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import customtkinter as ctk
```

### **Проблема B: Циклические зависимости**
**Симптом**: store импортирует actions, actions импортирует store
**Решение**: Использовать Dependency Injection через конструкторы

### **Проблема C: GUI state не синхронизируется со store**
**Симптом**: Карточка показывает старые данные после обновления
**Решение**: Убедиться, что refresh_all() вызывается всегда после store.update()

### **Проблема D: Matplotlib процесс зависает**
**Симптом**: App медленнее при отрисовке графиков
**Решение**: Использовать threading для рендера диаграмм

---

## 8️⃣ МЕТРИКИ УСПЕХА

После завершения рефакторинга:

✅ **Модульность**
- Каждый файл < 500 строк (кроме main.py)
- Каждый класс < 300 строк
- Максимум 2 уровня вложенности импортов

✅ **Тестируемость**
- Store CRUD операции имеют unit tests
- Парсеры имеют parametrized tests
- UI компоненты имеют smoke tests (открывание/закрывание)

✅ **Производительность**
- Нет утечек памяти при долгой работе
- Refresh < 100ms даже с 1000 задачами
- Поиск < 50ms

✅ **Отсутствие регрессий**
- Все функции работают как раньше
- JSON структура не изменяется
- Нет потери данных при обновлении версии

✅ **Документация**
- Каждый модуль имеет docstring
- API readme в каждой папке
- Type hints на публичных функциях

---

## ВРЕМЕННАЯ ОЦЕНКА

| Фаза | Дни | Что делается |
|------|-----|---|
| 0 | 1 | Подготовка, git, tests <br> baseline |
| 1 | 2-3 | Утилиты извлечение |
| 2 | 4-5 | TaskStore модульность |
| 3 | 6-8 | GUI компоненты |
| 4 | 9-11 | Главное приложение разбиение (**-1 день**, нет stats) |
| 5 | 12-14 | Оптимизация и документация (**-1 день**) |
| 6 | 15 | Финал тестирование |
| **ИТОГО** | **~15 дней** | При 4 часах в день (было 16) |

**Параллельная работа возможна**: Фазы 1-2 могут идти параллельно с подготовкой маршрутов для Phase 3-4

---

## РИСК-МАТРИЦА МИГРАЦИИ

| № | Риск | Вероятность | Влияние | Стратегия |
|---|------|---|---|---|
| 1 | Рассинхронизация индекса | Высокая | Критическое | Assertions, IndexManager |
| 2 | Потеря данных план-сессия | Средняя | Критическое | Инварианты, тесты |
| 3 | Утечка памяти matplotlib | Средняя | Среднее | Canvas cleanup, мониторинг |
| 4 | Циклические импорты | Средняя | Среднее | DI pattern, TYPE_CHECKING |
| 5 | UI состояние рассинхронизируется | Низкая | Среднее | refresh_all() disicpline |
| 6 | Регрессия производительности | Низкая | Среднее | Бенчмарки, профилирование |

---

## РАЗВЕРТЫВАНИЕ СТРАТЕГИЯ

1. **Разработка на feature branch**: `refactor/modularize`
2. **Частые commits** (каждое шаг): `git commit -m "refactor: extract dateutils"`
3. **Pull request после каждой фазы** для код-ревью
4. **Smoke тесты** перед каждым merge
5. **Backup текущего скрипта**: `taskfocus_original_v1.py`

---

## ЗАКЛЮЧЕНИЕ

Этот план позволляет поэтапно модульранизировать legacy код без риска больших сбоев. Ключ успеха — **маленькие шаги с регулярными контролями**.

Начните с **Фазы 0** и осторожно продвигайтесь!
