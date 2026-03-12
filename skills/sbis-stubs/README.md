# sbis-stubs

Навык для использования Python‑стабов SBIS/Saby при работе с проектами SBIS.

## Первоначальная настройка

1) Проверьте, что стабы лежат в:
   - `C:/Saby/stubs`
или замените путь в SKILL.md

2) Убедитесь, что редактор видит стабы (Cursor Pyright):
   - Файл: `C:/Users/<user_folder>/AppData/Roaming/Cursor/User/settings.json`
   - Должны быть ключи:

```json
{
  "cursorpyright.analysis.stubPath": "C:/Saby/stubs",
  "cursorpyright.analysis.extraPaths": ["C:/Saby/stubs"]
}
```

> Важно: расширение Cursor Pyright использует ключи `cursorpyright.*`, а не `basedpyright.*`.

3) Перезапустите языковой сервер:
   - `Python: Restart Language Server`

## Как использовать навык

Навык срабатывает когда:
- в .py файле есть `import sbis`;
- вы работаете с тегом `<body>` в `.orx` файле;


### Быстрое применение настроек (если стабы не видятся)

Выполните скрипт:

```powershell
python "C:/Users/<user_folder>/.codex/skills/sbis-stubs/scripts/apply_cursorpyright_stubs.py"
```

Он проставит/обновит нужные ключи в `settings.json`.

### Проверка

Откройте файл с `import sbis` и перейдите к определению — должен открыться путь:
`<your_path>/stubs/sbis`.

### Использование стабов в работе

При чтении/ревью кода сверяйте сигнатуры и типы в `.pyi`:
это помогает проверять корректность API‑вызовов, набор полей и типы данных.
