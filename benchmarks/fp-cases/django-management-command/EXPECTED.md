# django-management-command

Tests Django management command discovery.

Expected behavior: pyfallow may report low-confidence uncertainty elsewhere in the project, but it
must not report the command module or command entry symbols as unused.

Why this is tough: Django discovers management commands by filesystem convention, not by local Python
imports from `manage.py`.

How pyfallow handles it: the existing Django framework heuristic treats `management/commands` modules
and command entry symbols as framework-managed.
