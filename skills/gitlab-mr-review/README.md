# gitlab-mr-review

Навык для подготовки данных к ревью GitLab Merge Request.

## Использование

powershell -ExecutionPolicy Bypass -File "<skill_root>\run_mr_prep.ps1" "<MR_URL>"

Примечания:
- `<skill_root>` — каталог этого навыка.
- Обёртка сама находит `scripts\mr_prep.py` относительно своего расположения.
- Значение `GIT_REPO_ROOTS` из переменной окружения имеет приоритет над `local_config.json`.

## Пример JSON-результата

{
  "repo_dir": "C:\\Saby\\src\\advert-service",
  "project_path": "crm/advert-service",
  "mr_url": "https://git.sbis.ru/crm/advert-service/-/merge_requests/72546",
  "target_branch": "rc-26.2100",
  "source_branch": "26.2100/feature/potemkin/expenses_item_read",
  "diff_unified_path": "C:\\Saby\\distr\\.codex\\tmp\\gitlab-mr-review\\mr_2255_72546.diff",
  "changes_json_path": "C:\\Saby\\distr\\.codex\\tmp\\gitlab-mr-review\\mr_2255_72546_changes.json",
  "notes": []
}

## Требования

- Python 3.11+ доступен в PATH
- Доступ к GitLab и репозиторию MR (SSH/HTTPS credentials)
- Git установлен и доступен в PATH

## Установка

Установите навык из `https://git.sbis.ru/crm/sbis-crm-framework/-/tree/master/skills/gitlab-mr-review`.

### Windows (PowerShell)

```powershell
git clone git@git.sbis.ru:crm/sbis-crm-framework.git
Copy-Item -Path ".\sbis-crm-framework\skills\gitlab-mr-review" `
  -Destination "$env:USERPROFILE\.codex\skills\gitlab-mr-review" `
  -Recurse -Force
```

После копирования навыка перезапустите Codex/Cursor.

## Настройка переменных окружения

Навык использует:
- `GIT_REPO_ROOTS` — один или несколько каталогов, где ищутся локальные git-репозитории.
- `GITLAB_TOKEN` — токен для запросов к GitLab API.

### Windows (PowerShell, сохранить для текущего пользователя)

```powershell
setx GIT_REPO_ROOTS "C:\Saby\src;D:\work\repos"
setx GITLAB_TOKEN "glpat-xxxxxxxxxxxxxxxx"
```

После `setx` перезапустите терминал/Cursor.

### Windows (PowerShell, только для текущей сессии)

```powershell
$env:GIT_REPO_ROOTS = "C:\Saby\src;D:\work\repos"
$env:GITLAB_TOKEN = "glpat-xxxxxxxxxxxxxxxx"
```

### Проверка

```powershell
echo $env:GIT_REPO_ROOTS
echo $env:GITLAB_TOKEN
```

### Альтернатива через local config

Если переменные окружения не заданы, навык читает значения из `local_config.json`:

```json
{
  "GIT_REPO_ROOTS": "C:/Saby/src;D:/work/repos",
  "GITLAB_TOKEN": "glpat-xxxxxxxxxxxxxxxx"
}
```

## Шаблон

- Шаблон команды: templates\mr_prep_command.txt

## Диагностика проблем

- `"can't open file ... mr_prep.py"`: используйте команду-обёртку выше, она сама корректно разрешает путь к скрипту относительно каталога навыка.
- Если `CODEX_HOME` не задан, указывайте `<skill_root>` явно (см. раздел "Использование").
- Git credentials/permissions: убедитесь, что у вас есть доступ к MR и право на `fetch` репозитория.
- Если JSON пустой или некорректный, проверьте stderr на ошибки git: обёртка печатает git-команды именно туда.

