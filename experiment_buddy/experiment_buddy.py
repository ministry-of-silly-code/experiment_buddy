import argparse
import datetime
import logging
import os
import subprocess
import sys
import time
import types

import cloudpickle
import fabric
import git
import matplotlib.pyplot as plt
import tensorboardX
import tqdm
import wandb
import wandb.cli
import yaml
from invoke import UnexpectedExit
from paramiko.ssh_exception import SSHException

import experiment_buddy.utils
from experiment_buddy.utils import get_backend
from experiment_buddy.utils import get_project_name

try:
    import torch
except ImportError:
    TORCH_ENABLED = False
else:
    TORCH_ENABLED = True

logging.basicConfig(level=logging.INFO)

wandb_escape = "^"
hyperparams = None
tb = tensorboard = None
if os.path.exists("buddy_scripts/"):
    SCRIPTS_PATH = "buddy_scripts/"
else:
    SCRIPTS_PATH = os.path.join(os.path.dirname(__file__), "../scripts/")
ARTIFACTS_PATH = "runs/"
DEFAULT_WANDB_KEY = os.path.join(os.environ["HOME"], ".netrc")


def register(config_params):
    global hyperparams
    # TODO: fails on nested config object
    if hyperparams is not None:
        raise RuntimeError("refusing to overwrite registered parameters")

    parser = argparse.ArgumentParser()
    parser.add_argument('_ignored', nargs='*')

    for k, v in config_params.items():
        if k.startswith(wandb_escape):
            raise NameError(f"{wandb_escape} is a reserved prefix")
        if _is_valid_hyperparam(k, v):
            parser.add_argument(f"--{k}", f"--^{k}", type=type(v), default=v)

    parsed = parser.parse_args()

    for k, v in vars(parsed).items():
        k = k.lstrip(wandb_escape)
        config_params[k] = v

    hyperparams = config_params.copy()


def _is_valid_hyperparam(key, value):
    if key.startswith("__") and key.endswith("__"):
        return False
    if key == "_":
        return False
    if isinstance(value, (types.FunctionType, types.MethodType, types.ModuleType)):
        return False
    return True


class WandbWrapper:
    def __init__(self, experiment_id, debug, wandb_kwargs, local_tensorboard=None):
        """
        project_name is the git root folder name
        """
        # Calling wandb.method is equivalent to calling self.run.method
        # I'd rather to keep explicit tracking of which run this object is following
        wandb_kwargs["mode"] = wandb_kwargs.get("mode", "offline" if debug else "online")
        if not debug:
            wandb_kwargs["settings"] = wandb_kwargs.get("settings", wandb.Settings(start_method="fork"))
        self.run = wandb.init(name=experiment_id, **wandb_kwargs)

        self.tensorboard = local_tensorboard
        self.objects_path = os.path.join(ARTIFACTS_PATH, "objects/", self.run.name)
        os.makedirs(self.objects_path, exist_ok=True)

        def register_param(name, value, prefix=""):
            if not _is_valid_hyperparam(name, value):
                return

            if name == "_extra_modules_":
                for module in value:
                    for __k in dir(module):
                        __v = getattr(module, __k)
                        register_param(__k, __v, prefix=module.__name__.replace(".", "_"))
            else:
                name = prefix + wandb_escape + name
                # if the parameter was not set by a sweep
                if not name in wandb.config._items:
                    print(f"setting {name}={str(value)}")
                    setattr(wandb.config, name, str(value))
                else:
                    print(
                        f"not setting {name} to {str(value)}, "
                        f"str because its already {getattr(wandb.config, name)}, "
                        f"{type(getattr(wandb.config, name))}"
                    )

        for k, v in hyperparams.items():
            register_param(k, v)

    def add_scalar(self, tag: str, scalar_value: float, global_step: int):
        scalar_value = float(scalar_value)  # silently remove extra data such as torch gradients
        self.run.log({tag: scalar_value}, step=global_step, commit=False)
        if self.tensorboard:
            self.tensorboard.add_scalar(tag, scalar_value, global_step=global_step)

    def add_figure(self, tag, figure, global_step, close=True):
        self.run.log({tag: figure}, global_step)
        if close:
            plt.close(figure)

        if self.tensorboard:
            self.tensorboard.add_figure(tag, figure, global_step=None, close=True)

    @staticmethod
    def add_histogram(tag, values, global_step):
        if len(values) == 2:
            wandb.log({tag: wandb.Histogram(np_histogram=values)}, step=global_step, commit=False)
        else:
            wandb.log({tag: wandb.Histogram(values)}, step=global_step, commit=False)

    def plot(self, tag, values, global_step):
        wandb.log({tag: wandb.Image(values)}, step=global_step, commit=False)

    def add_object(self, tag, obj, global_step):
        if not TORCH_ENABLED:
            raise NotImplementedError

        local_path = os.path.join(self.objects_path, f"{tag}-{global_step}.pt")
        with open(local_path, "wb") as fout:
            try:
                torch.save(obj, fout, pickle_module=cloudpickle)
            except Exception as e:
                raise e

        self.run.save(local_path, base_path=self.objects_path)
        return local_path

    def watch(self, *args, **kwargs):
        self.run.watch(*args, **kwargs)


@experiment_buddy.utils.telemetry
def deploy(host: str = "", sweep_yaml: str = "", proc_num: int = 1, wandb_kwargs=None, extra_slurm_headers="") -> WandbWrapper:
    if wandb_kwargs is None:
        wandb_kwargs = {}

    debug = '_pydev_bundle.pydev_log' in sys.modules.keys() and not os.environ.get('BUDDY_DEBUG_DEPLOYMENT', False)
    is_running_remotely = "SLURM_JOB_ID" in os.environ.keys() or "BUDDY_IS_DEPLOYED" in os.environ.keys()
    local_run = not host

    try:
        git_repo = git.Repo(search_parent_directories=True)
    except git.InvalidGitRepositoryError:
        raise ValueError(f"Could not find a git repo")

    project_name = get_project_name(git_repo)

    if local_run and sweep_yaml:
        raise NotImplemented("Local sweeps are not supported")

    wandb_kwargs = {'project': project_name, **wandb_kwargs}
    common_kwargs = {'debug': debug, 'wandb_kwargs': wandb_kwargs, }

    if is_running_remotely:
        print("using wandb")
        experiment_id = f"{git_repo.head.commit.message.strip()}"
        jid = datetime.datetime.now().strftime("%b%d_%H-%M-%S")
        jid += os.environ.get("SLURM_JOB_ID", "")
        # TODO: turn into a big switch based on scheduler
        return WandbWrapper(f"{experiment_id}_{jid}", **common_kwargs)

    dtm = datetime.datetime.now().strftime("%b%d_%H-%M-%S")
    if debug:
        experiment_id = "DEBUG_RUN"
        tb_dir = os.path.join(git_repo.working_dir, ARTIFACTS_PATH, "tensorboard/", experiment_id, dtm)
        return WandbWrapper(f"{experiment_id}_{dtm}", local_tensorboard=_setup_tb(logdir=tb_dir), **common_kwargs)

    experiment_id = _ask_experiment_id(host, sweep_yaml)
    print(f"experiment_id: {experiment_id}")
    if local_run:
        tb_dir = os.path.join(git_repo.working_dir, ARTIFACTS_PATH, "tensorboard/", experiment_id, dtm)
        return WandbWrapper(f"{experiment_id}_{dtm}", local_tensorboard=_setup_tb(logdir=tb_dir), **common_kwargs)
    else:
        if experiment_id.endswith("!!"):
            extra_slurm_headers += "\n#SBATCH --partition=unkillable"
        elif experiment_id.endswith("!"):
            extra_slurm_headers += "\n#SBATCH --partition=main"

        _commit_and_sendjob(host, experiment_id, sweep_yaml, git_repo, project_name, proc_num, extra_slurm_headers, wandb_kwargs)
        sys.exit()


def _ask_experiment_id(cluster, sweep):
    title = f'{"[CLUSTER" if cluster else "[LOCAL"}'
    if sweep:
        title = f"{title}-SWEEP"
    title = f"{title}]"

    try:
        import tkinter.simpledialog  # fails on the server or colab
        logging.info("Name your run in the pop-up window!")
        root = tkinter.Tk()
        root.withdraw()
        experiment_id = tkinter.simpledialog.askstring(title, "experiment_id")
        root.destroy()
    except:
        if os.environ.get('BUDDY_CURRENT_TESTING_BRANCH', ''):
            import uuid
            experiment_id = f'TESTING_BRANCH-{os.environ["BUDDY_CURRENT_TESTING_BRANCH"]}-{uuid.uuid4()}'
        else:
            experiment_id = input(f"Running on {title}\ndescribe your experiment (experiment_id):\n")

    experiment_id = (experiment_id or "no_id").replace(" ", "_")
    if cluster:
        experiment_id = f"[CLUSTER] {experiment_id}"
    return experiment_id


def _setup_tb(logdir):
    print("http://localhost:6006")
    return tensorboardX.SummaryWriter(logdir=logdir)


def _open_ssh_session(hostname: str) -> fabric.Connection:
    """ TODO: move this to utils.py or to a class (better)
        TODO add time-out for unknown host
     """

    try:
        ssh_session = fabric.Connection(host=hostname, connect_timeout=10, forward_agent=True)
        ssh_session.run("")
    except SSHException as e:
        raise SSHException(
            "SSH connection failed!,"
            f"Make sure you can successfully run `ssh {hostname}` with no parameters, "
            f"any parameters should be set in the ssh_config file"
        )
    return ssh_session


def _ensure_scripts_directory(ssh_session: fabric.Connection, extra_slurm_header: str, working_dir: str) -> str:
    retr = ssh_session.run("mktemp -d -t experiment_buddy-XXXXXXXXXX")
    remote_tmp_folder = retr.stdout.strip() + "/"
    ssh_session.put(f'{SCRIPTS_PATH}/common/common.sh', remote_tmp_folder)

    scripts_dir = os.path.join(SCRIPTS_PATH, get_backend(ssh_session, working_dir).value)

    for file in os.listdir(scripts_dir):
        if extra_slurm_header and file in ("run_sweep.sh", "srun_python.sh"):
            new_tmp_file = _insert_extra_header(extra_slurm_header, os.path.join(scripts_dir, file))
            ssh_session.put(new_tmp_file, remote_tmp_folder)
        else:
            ssh_session.put(os.path.join(scripts_dir, file), remote_tmp_folder)

    return remote_tmp_folder


def _insert_extra_header(extra_slurm_header, script_path):
    tmp_script_path = f"/tmp/{os.path.basename(script_path)}"
    with open(script_path) as f_in, open(tmp_script_path, "w") as f_out:
        rows = f_in.readlines()
        first_free_idx = 1 + next(i for i in reversed(range(len(rows))) if "#SBATCH" in rows[i])
        rows.insert(first_free_idx, f"\n{extra_slurm_header}\n")
        f_out.write("\n".join(rows))
    return tmp_script_path


def _check_or_copy_wandb_key(ssh_session: fabric.Connection):
    try:
        ssh_session.run("test -f $HOME/.netrc")
    except UnexpectedExit:
        print(f"Wandb api key not found in {ssh_session.host}. Copying it from {DEFAULT_WANDB_KEY}")
        ssh_session.put(DEFAULT_WANDB_KEY, ".netrc")


def log_cmd(cmd, retr):
    print("################################################################")
    print(f"## {cmd}")
    print("################################################################")
    print(retr)
    print("################################################################")


def _commit_and_sendjob(hostname: str, experiment_id: str, sweep_yaml: str, git_repo: git.Repo, project_name: str,
                        proc_num: int, extra_slurm_header: str, wandb_kwargs: dict):
    ssh_session = _open_ssh_session(hostname)
    scripts_folder = _ensure_scripts_directory(ssh_session, extra_slurm_header, git_repo.working_dir)
    hash_commit = git_sync(experiment_id, git_repo)

    _check_or_copy_wandb_key(ssh_session)

    git_url = git_repo.remotes[0].url
    entrypoint = os.path.relpath(sys.argv[0], git_repo.working_dir)
    if sweep_yaml:
        sweep_id = _load_sweep(entrypoint, experiment_id, project_name, sweep_yaml, wandb_kwargs)
        ssh_command = f"/opt/slurm/bin/sbatch {scripts_folder}/run_sweep.sh {git_url} {sweep_id} {hash_commit}"
    else:
        ssh_command = f"bash -l {scripts_folder}/run_experiment.sh {git_url} {entrypoint} {hash_commit}"
        print("monitor your run on https://wandb.ai/")

    print(ssh_command)
    for _ in tqdm.trange(proc_num):
        time.sleep(1)
        ssh_session.run(ssh_command)


def _load_sweep(entrypoint, experiment_id, project, sweep_yaml, wandb_kwargs):
    with open(sweep_yaml, 'r') as stream:
        data_loaded = yaml.safe_load(stream)

    if data_loaded["program"] != entrypoint:
        raise ValueError(f'YAML {data_loaded["program"]} does not match the entrypoint {entrypoint}')

    try:
        wandb_stdout = subprocess.check_output([
            "wandb", "sweep",
            "--name", "experiment",
            "--project", project,
            *(["--entity", wandb_kwargs["entity"]] if "entity" in wandb_kwargs else []),
            sweep_yaml
        ], stderr=subprocess.STDOUT).decode("utf-8").split("\n")
    except Exception as e:
        print(e.output)
        raise e

    row = next(row for row in wandb_stdout if "Run sweep agent with:" in row)
    print(next(row for row in wandb_stdout if "View" in row))

    sweep_id = row.split()[-1].strip()
    return sweep_id


def git_sync(experiment_id, git_repo):
    active_branch = git_repo.active_branch.name
    try:
        subprocess.check_output(f"git checkout --detach", shell=True)  # move changest to snapshot branch
        subprocess.check_output(f"git add .", shell=True)

        try:
            subprocess.check_output(f"git commit --no-verify -m '{experiment_id}'", shell=True)
        except subprocess.CalledProcessError as e:
            git_hash = git_repo.commit().hexsha
            # Ensure the code is remote
            subprocess.check_output(f"git push {git_repo.remotes[0]} {active_branch}", shell=True)
        else:
            git_hash = git_repo.commit().hexsha
            tag_name = f"snapshot/{active_branch}/{git_hash}"
            subprocess.check_output(f"git tag {tag_name}", shell=True)
            subprocess.check_output(f"git push {git_repo.remotes[0]} {tag_name}", shell=True)  # send to online repo
            subprocess.check_output(f"git reset HEAD~1", shell=True)  # untrack the changes
    finally:
        subprocess.check_output(f"git checkout {active_branch}", shell=True)
    return git_hash
