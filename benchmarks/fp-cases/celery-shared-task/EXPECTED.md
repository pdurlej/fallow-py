# celery-shared-task

Tests Celery shared task decorators.

Expected behavior: `work` must not be reported as an unused symbol. The task module may remain
low-confidence dead-code context if not imported by local source.

Why this is tough: Celery workers can discover tasks by application configuration and autodiscovery.

How fallow-py handles it: `@shared_task` marks the function as framework-managed and the module carries
framework uncertainty.
