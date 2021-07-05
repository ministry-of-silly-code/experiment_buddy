import asyncio
import atexit
import enum
import os
import subprocess

import aiohttp
import fabric
import git
import invoke
from funcy import log_durations


class Backend(enum.Enum):
    GENERAL: str = "general"
    SLURM: str = "slurm"
    DOCKER: str = "docker"


def get_backend(ssh_session: fabric.connection.Connection, project_dir: str) -> str:
    try:
        ssh_session.run("/opt/slurm/bin/scontrol ping")
        return Backend.SLURM
    except invoke.exceptions.UnexpectedExit:
        pass

    if not os.path.exists(os.path.join(project_dir, "Dockerfile")):
        return Backend.GENERAL
    try:
        ssh_session.run("docker -v")
        ssh_session.run("docker-compose -v")
        return Backend.DOCKER
    except invoke.exceptions.UnexpectedExit:
        pass
    return Backend.GENERAL


def get_project_name(git_repo: git.Repo) -> str:
    git_repo_remotes = git_repo.remotes
    assert isinstance(git_repo_remotes, list)
    remote_url = git_repo_remotes[0].config_reader.get("url")
    project_name, _ = os.path.splitext(os.path.basename(remote_url))
    return project_name


def fire_and_forget(f):
    def wrapped(*args, **kwargs):
        return asyncio.ensure_future(f(*args, *kwargs))

    return wrapped


def __async_cleanup():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(*asyncio.all_tasks(loop)))


atexit.register(__async_cleanup)


@fire_and_forget
async def __remote_time_logger(elapsed: str):
    import re
    elapsed, function_name = re.search(r'([\d.]+).+in (\w+)', elapsed).groups()

    async with aiohttp.ClientSession() as session:
        async with session.get(
                f'http://static.92.155.21.65.clients.your-server.de/{function_name}/{elapsed}') as response:
            await response.text()


def _get_job_info(jid):
    result = subprocess.check_output(f"/opt/slurm/bin/sacct --brief -j {jid}".split()).decode()
    jid, state, exit_code = result.split("\n")[2].split()
    return state


telemetry = log_durations(__remote_time_logger, unit='s')
