---
name: sbis-stubs
description: |
  Use SBIS/Saby Python stubs during work on SBIS projects: treat the stubs in C:/Saby/stubs as the source of API contracts and types when reading, editing, or reviewing code 
  (especially when a .py file imports sbis or when editing .orx files with a <body> tag). 
  Trigger this skill to confirm stub availability, verify they resolve in the editor, and lean on stubs for understanding function signatures and data shapes.
---

# Sbis Stubs workflow

1) Confirm stubs are available in the filesystem.
   - Expected root: `C:/Saby/stubs`
   - The `sbis` package should exist (e.g., `C:/Saby/stubs/sbis/__init__.pyi`).

2) Use stubs during code work.
   - Consult function signatures and docstrings in `.pyi` files for expected parameters and return types.
   - Use types to validate API usage, data shapes, and optional/nullability.

3) If stubs are not resolving, fix the environment.

