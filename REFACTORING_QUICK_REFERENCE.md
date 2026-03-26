# 🎯 QUICK REFERENCE: Рефакторинг TaskFocus

## 📊 ТЕКУЩАЯ АРХИТЕКТУРА (Legacy - Monolith)

```
┌─────────────────────────────────────────────────┐
│         taskfocus.py (4200 строк)              │
├─────────────────────────────────────────────────┤
│ • Config (50 строк)                            │
│ • Helpers/Utilities (680 строк) ⚠️ СМЕШАНО    │
│ • TaskStore class (550 строк) 🔴 РИСК         │
│ • 11 GUI Classes (1600 строк) 🔴 МОНОЛИТ     │
│ • TaskFocusApp (1500 строк) 🔴 МОНОЛИТ       │
│ • Main entry point (20 строк)                  │
└─────────────────────────────────────────────────┘
```

## 🚀 ЦЕЛЕВАЯ АРХИТЕКТУРА (Modular)

```
taskfocus/
├── taskfocus.py (100 строк) ← Главный entry point
├── config.py (50 строк)
│
├── data/
│   ├── store.py (400 строк) ← TaskStore
│   ├── models.py (50 строк) ← Dataclasses
│   └── validators.py (50 строк)
│
├── utils/
│   ├── dateutils.py (80 строк)
│   ├── formatters.py (60 строк)
│   ├── parsers.py (100 строк)
│   ├── url_utils.py (50 строк)
│   └── tk_utils.py (120 строк)
│
├── app/
│   ├── refresh.py (150 строк) ← Refresh Controller
│   ├── actions.py (300 строк) ← Action Handlers
│   ├── search.py (100 строк) ← Search Engine
│   ├── charts.py (350 строк) ← Matplotlib
│   ├── report.py (150 строк) ← Report Generator
│   └── bulk_importer.py (100 строк)
│
├── ui/
│   ├── components/
│   │   ├── cards.py (80 строк)
│   │   ├── task_detail.py (400 строк)
│   │   ├── editors.py (250 строк)
│   │   └── common.py (50 строк)
│   │
│   ├── dialogs/
│   │   ├── session.py (200 строк)
│   │   ├── session_manager.py (100 строк)
│   │   ├── postpone.py (80 строк)
│   │   ├── timer.py (150 строк)
│   │   └── focus.py (80 строк)
│   │
│   ├── tabs/
│   │   ├── today.py (100 строк)
│   │   ├── all_tasks.py (100 строк)
│   │   ├── add_task.py (150 строк)
│   │   ├── bulk.py (100 строк)
│   │   ├── stats.py (80 строк)
│   │   └── report.py (80 строк)
│   │
│   └── layout.py (100 строк)
│
└── tests/
    ├── test_store.py
    ├── test_parsers.py
    └── test_ui.py
```

---

## ⚠️ 5 КРИТИЧЕСКИХ РИСКОВ

| № | Риск | Место | Решение |
|----|------|-------|---------|
| 🔴1 | **Task Index Sync** | TaskStore._task_index | IndexManager + assertions |
| 🔴2 | **Plan-Session Links** | _sync_plan_completion() | Документировать инварианты |
| 🔴3 | **UI State Chaos** | TaskDetailPane view/edit | Implement State Pattern |
| 🟡4 | ~~**Matplotlib Memory**~~ **УДАЛЕНО** | ~~_render_*_chart()~~ Statistics tab removed | ✅ No dependency on matplotlib |
| 🟡5 | **Job Scheduling** | _refresh_job, _today_search_job | JobScheduler class |

---

## 📋 ПОВТОРЯЮЩИЕСЯ ПАТТЕРНЫ

### Pattern A: Dialog + Callback
```python
# ❌ Current
dialog = SomeDialog(self, ...)
result = dialog.show()
if result:
    self.store.update()
    self.refresh_all()

# ✅ After
controller.execute_dialog_action(SomeAction, task)
  → DialogController handles store + refresh
```

### Pattern B: List Refresh
```python
# ❌ Current - в _refresh_today_list() и _refresh_all_list()
body = self._list_body(self.today_list)
for w in body.winfo_children(): w.destroy()
tasks = self.store.list_tasks(...)
for t in tasks: self._add_task_card(body, t)

# ✅ After
refresher = ListRefresher(container, task_provider)
refresher.refresh()
```

### Pattern C: State Invalidation
```python
# ❌ Current - разные флаги везде
if data_changed:
    self._stats_dirty = True
    self._search_cache_dirty = True
    self._labels_dirty = True

# ✅ After
self.invalidation_mgr.invalidate("stats", "search", "labels")
```

---

## 🗓️ ФАЗА ПО ФАЗЕ (TL;DR)

| Фаза | Дней | Делай | Итого |
|------|------|--------|-------|
| 0 | 1 | git + tests baseline | ✅ Can roll back |
| 1 | 2-3 | Extract utils (dateutils, formatters, parsers) | ✅ Utils importable |
| 2 | 4-5 | Extract TaskStore, IndexManager | ✅ Store tests pass |
| 3 | 6-8 | Extract GUI components, dialogs | ✅ Components work |
| 4 | 9-11 | Extract controllers (refresh, actions, search) **NO charts** | ✅ Main shortened to 300 lines |
| 5 | 12-14 | Refactor (State Pattern, Event Bus, logging) **NO matplotlib** | ✅ Good architecture |
| 6 | 15 | Final testing, merge | ✅ Live deployment |

**Total: ~15 days at 4h/day = 60 hours** (был 16, сэкономили 4 часа)

---

## 🔧 МИНИМАЛЬНЫЙ VIABLE REFACTORING (День 1-5)

Если времени меньше, сделайте только:

✅ **MUST HAVE:**
1. Extract utils (utils/ folder) → 2 дня
2. Extract TaskStore → 2 дня
3. Add basic tests → 1 день

✅ **Result:** Store отделен, легче тестировать | Statistics удалена (-800 строк) | Dependencies чист

---

## 🎓 LESSONS LEARNED

### Почему сейчас сложно?
- ~~4200~~ **3400 строк** в одном файле (после удаления Statistics)
- Множество callbacks = трудно отследить flow
- UI state разбросано = потеря синхронизации
- Нет тестов = регрессии незаметны
- Нет docs = новые разработчики теряются
- **Зависимость от matplotlib** убрана (один импорт меньше)

### Почему этот план работает?
- Маленькие этапы = легче контролировать
- Регулярные контрольные точки = можно откатиться
- Модульность = переиспользуемость коэффициент
- Dependency Injection = слабая связанность
- Tests at each phase = confidence растет

---

## ✅ CHECKLIST: ПЕРЕД СТАРТОМ

- [ ] Текущий скрипт работает без ошибок
- [ ] Создан git branch `refactor/modularize`
- [ ] Создана папка `tests/`
- [ ] Backup текущего файла сделан
- [ ] Документированы все known issues
- [ ] Проверени requirements (CustomTkinter, tkcalendar, matplotlib)
- [ ] VS Code лучше с Python extension

---

## 📞 HELP: Когда что-то пойдет не так

**Проблема**: ImportError с customtkinter
→ Решение: Используй TYPE_CHECKING, отложи импорты

**Проблема**: Циклические зависимости  
→ Решение: Pass dependencies через конструкторы

**Проблема**: UI не обновляется после сохранения  
→ Решение: Убедись refresh_all() вызывается

**Проблема**: Тесты не работают
→ Решение: Mock конструктор Tkinter через pytest fixtures

**Проблема**: Git merge conflicts
→ Решение: Разбей фазы на разные branches

---

## 📚 REFERENCE

- **LEGACY_REFACTORING_PLAN.md** ← Full detailed plan (читай это!)
- **taskfocus.py** ← Current monolith
- **tests/** ← Emerging test suite

**Начни с Фазы 0 и продвигайся методично!** 🚀
