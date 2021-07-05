import os
import pathlib
import shutil
import subprocess
import venv
from distutils import dir_util

import fabric
import paramiko
from git import Repo

from .init_framework import FatalException


def is_venv():
    return bool(os.environ.get('VIRTUAL_ENV'))


def create_venv():
    """Create the experiment venv, otherwhise use the already active venv"""
    venv.EnvBuilder(with_pip=True).create('venv')
    subprocess.check_output(f'venv/bin/python3 -m pip install --upgrade pip', shell=True)
    print(f"""\n\nRemember to source your new environment with:
        source {os.getcwd()}/venv/bin/activate\n\n""")


def create_git_repo():
    """Setups the git repo with the proper git ignores"""
    Repo.init('./.git', bare=True)


def create_base_structure(use_local_venv=True):
    """initializes the base example"""
    base_skeleton_path = f'{os.path.dirname(os.path.realpath(__file__))}/base_skeleton'
    dir_util.copy_tree(base_skeleton_path, '.')
    if use_local_venv:
        subprocess.check_output(f'venv/bin/python3 -m pip install -r requirements.txt', shell=True)
    elif is_venv():
        subprocess.check_output(f'python3 -m pip install -r requirements.txt', shell=True)
    else:
        raise FatalException('Installing packages on the system python is not allowed. Aborting')


def setup_mila_user(mila_user: str):
    """One time setup to connect with the Mila servers"""
    mila_config = f"""
Host mila1
    Hostname login-1.login.server.mila.quebec
Host mila2
    Hostname login-2.login.server.mila.quebec
Host mila3
    Hostname login-3.login.server.mila.quebec
Host mila4
    Hostname login-4.login.server.mila.quebec
Host mila
    Hostname         login.server.mila.quebec
Host mila*
    Port 2222

Match host *.mila.quebec,*.umontreal.ca
    User {mila_user}
    PreferredAuthentications publickey
    Port 2222
    ServerAliveInterval 120
    ServerAliveCountMax 5
"""
    config_path = os.path.expanduser('~/.ssh/config_mila')
    pathlib.Path(config_path).touch()

    current_config = pathlib.Path(config_path).read_text()

    if 'Host mila' not in current_config:
        shutil.copy(config_path, f'{config_path}_BACKUP')
        pathlib.Path(config_path).write_text(f'{current_config}\n{mila_config}')

    try:
        fabric.Connection(host='mila', config=fabric.Config(user_ssh_path=config_path)).run("")
    except paramiko.ssh_exception.SSHException:
        shutil.copy(f'{config_path}_BACKUP', config_path)
        raise FatalException(f"""
Error while checking SSH connection, stopping
Did you:
 - double check that your username is '{mila_user}'?
 - setup the public and private key for you and for the mila cluster?
""")


def setup_wandb(project_name: str):
    """Initialize the wandb project in the current directory"""
    subprocess.check_output(f'venv/bin/python3 -m pip install wandb', shell=True)
    subprocess.check_output(f'venv/bin/python3 -m wandb init -p {project_name}', shell=True)
