from asyncz.jobs import Job
from asyncz.schedulers import AsyncIOScheduler
from asyncz.triggers import CronTrigger

# Create a scheduler
scheduler = AsyncIOScheduler()


def check_status():
    # Logic to check statuses
    ...


job = Job(
    id="my-job",
    fn=check_status,
    name="my-func",
    scheduler=scheduler,
    trigger=CronTrigger(day_of_week="mon,tue,wed,thu,fri,sat,sun", hour=8, minute=1),
    max_instances=3,
    coalesce=True,
)


scheduler.start()
