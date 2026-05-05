from celery import shared_task


@shared_task
def work():
    return 1
