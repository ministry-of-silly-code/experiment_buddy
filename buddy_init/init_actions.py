import os
import shutil
import subprocess
from distutils import dir_util

import fabric
import paramiko

import buddy_init.init_project
from buddy_init.init_project import enforce_answer_list, EXAMPLE_PROJECT_PATH


def _is_venv():
    virtual_env = os.environ.get('VIRTUAL_ENV')
    return bool(virtual_env)


def _call_python(command: str, use_local_venv=True):
    if use_local_venv:
        subprocess.check_output(f'venv/bin/python3 -m {command}', shell=True)
    elif _is_venv():
        subprocess.check_output(f'python3 -m {command}', shell=True)
    else:
        raise Exception('Installing packages on the system python is not allowed. Aborting')


def create_base_structure():
    """initializes the base example"""
    base_skeleton_path = f'{os.path.dirname(os.path.realpath(__file__))}/base_skeleton'
    dir_util.copy_tree(base_skeleton_path, '.')


def setup_ssh():
    config_file = os.path.expanduser('~/.ssh/config')
    shutil.copy(config_file, config_file + ".bak")

    with open(config_file) as fin:
        current_config = fin.read()

    if 'Host mila' not in current_config:
        print("""One time setup to connect with the Mila servers""")
        wrong_username = True
        while wrong_username:
            mila_username = input("What is your mila username?")
            wrong_username = buddy_init.init_project.enforce_answer_list(f"Your cluster username is {mila_username}", ["y", "n"]) == "n"

        with open(config_file, 'a') as fout:
            fout.write(
                "Host mila\n"
                "    Hostname         login.server.mila.quebec\n"
                "    Port 2222\n"
                f"    User {mila_username}\n"
                "    PreferredAuthentications publickey\n"
                "    Port 2222\n"
                "    ServerAliveInterval 120\n"
                "    ServerAliveCountMax 5\n\n")

    try:
        fabric.Connection(host='mila').run("")
    except paramiko.ssh_exception.SSHException:
        raise Exception(f"""
Error while checking SSH connection, stopping
Did you:
 - double check that your username is '{mila_username}'?
 - setup the public and private key for you and for the mila cluster?
""")


def setup_wandb():
    print("Follow the wandb instructions if necessary")
    retr = subprocess.run("python -m wandb login", shell=True)
    if retr.returncode != 0:
        raise RuntimeError("Something went wrong with wandb setup, please ask for help")


def setup_tutorial():
    create_example = enforce_answer_list("Do you want to create an example project?", ["y", "n"]) == "y"
    if create_example:
        raise NotImplementedError
        try:
            os.makedirs(EXAMPLE_PROJECT_PATH)
        except OSError as e:
            if os.path.exists(EXAMPLE_PROJECT_PATH) and os.listdir(EXAMPLE_PROJECT_PATH):
                raise RuntimeError(f"The directory {EXAMPLE_PROJECT_PATH} exists, remove it and rerun")
            raise e

        os.chdir(EXAMPLE_PROJECT_PATH)

        create_base_structure()
        # venv.EnvBuilder(with_pip=True).create('venv')  # Create venv
        # subprocess.run(f"git init .")
        # subprocess.run(f"pip install -r requirements.txt")

        remote_url = input("""
        buddy: Please go to https://github.com/new and create a new repository.\n
        buddy: Paste the repository remote URL and hit enter, it looks like git@github.com:your_username/repository_name.git.\n
        """.strip())
        subprocess.run(f"git remote add origin {remote_url}")

        if has_local_venv:
            print(f'\nRemember to source your new environment with:\n    source {os.getcwd()}/venv/bin/activate\n')


def setup_github():
    retr = fabric.Connection(host='mila').run("ssh -T git@github.com 2>&1", shell=True, warn=True)
    if "successfully authenticated" in retr.stdout:
        return

    retr = fabric.Connection(host='mila').run("cat .ssh/id_rsa.pub")

    if "No such file or directory" in retr.stdout:
        _ = fabric.Connection(host='mila').run("ssh-keygen -t rsa -N '' -f ~/.ssh/id_rsa")
        retr = fabric.Connection(host='mila').run("cat .ssh/id_rsa.pub")

    if retr.stdout.startswith("ssh-rsa"):
        print("Navigate to https://github.com/settings/ssh/new and add your cluster public key, to allow the cluster access to private repositories")
        print("Give it a title such as \"Mila cluster\"")
        print("and the key is:")
        print(retr.stdout)
