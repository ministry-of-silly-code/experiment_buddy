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


def _is_venv():
    virtual_env = os.environ.get('VIRTUAL_ENV')
    return bool(virtual_env)


def _call_python(command: str, use_local_venv=True):
    if use_local_venv:
        subprocess.check_output(f'venv/bin/python3 -m {command}', shell=True)
    elif _is_venv():
        subprocess.check_output(f'python3 -m {command}', shell=True)
    else:
        raise FatalException('Installing packages on the system python is not allowed. Aborting')


def create_venv():
    """Create the experiment venv, otherwhise use the already active venv"""
    venv.EnvBuilder(with_pip=True).create('venv')
    subprocess.check_output(f'venv/bin/python3 -m pip install --upgrade pip', shell=True)


def create_git_repo(base_dir, remote_url):
    """Setups the git repo with the proper git ignores, it requires a *NEW* the remote ssh address,
    it looks like: git@github.com:username/example.git"""
    subprocess.run(f'''(
        cd {base_dir}
        touch readme.md
        git init
        git add .
        git commit -m "First commit"
        git remote add origin {remote_url}
        git branch -M master
        git push -f -u origin master
   )''', capture_output=True, shell=True).stdout.decode()


def create_base_structure(use_local_venv=True):
    """initializes the base example"""
    base_skeleton_path = f'{os.path.dirname(os.path.realpath(__file__))}/base_skeleton'
    dir_util.copy_tree(base_skeleton_path, '.')
    _call_python(command='pip install -r requirements.txt', use_local_venv=use_local_venv)


def __create_mila_config(mila_user: str):
    return f"""Host mila1
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
    ServerAliveCountMax 5"""


def setup_mila_user(mila_user: str):
    """One time setup to connect with the Mila servers"""
    mila_config = __create_mila_config(mila_user)
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


def setup_wandb(project_name: str, use_local_venv=True):
    """Initialize the wandb project in the current directory"""
    _call_python(use_local_venv=use_local_venv, command=f'pip install wandb')
    _call_python(use_local_venv=use_local_venv, command=f'wandb init -p {project_name}')
