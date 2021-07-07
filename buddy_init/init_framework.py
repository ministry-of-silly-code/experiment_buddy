import inspect
import os
from typing import Callable, Union, Dict, Any
from shutil import which
from functools import wraps, partial
from halo import Halo


class FatalException(Exception):
    pass


def log_output(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        with open('/tmp/buddy-init.log', 'a'):
            return fn(*args, **kwargs)

    return wrapper()


def preflight_check():
    if which('ssh') is None:
        raise FatalException('missing ssh, you can install it with "sudo apt install openssl-client"')
    if which('git') is None:
        raise FatalException('missing git, you can install it with "sudo apt install git"')
    if which('pip') is None:
        raise FatalException('missing pip, you can install it with "sudo apt install python-pip"')


def coalesce(*args):
    return next((i for i in args if i is not None), None)


def get_fn_parameters(action):
    if hasattr(action, 'func'):
        return list(set(inspect.signature(action).parameters) - set(action.keywords.keys()))
    else:
        return list(inspect.signature(action).parameters)


class WorkingDirectory:

    def __init__(self, *, path, force):
        if force:
            os.system(f"rm -rf {path}")
        elif os.path.exists(path) and os.listdir(path):
            raise Exception("The directory exists and it's not empty")

        os.makedirs(path)
        self.base_path = path
        self.current_path = os.getcwd()

    def __enter__(self):
        os.chdir(self.base_path)
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        os.chdir(self.current_path)


def prompt(action: Union[Callable[[], None], Callable[[str], None]],
           parsed_args: Dict[str, Any],
           force=None):
    def unsnake(string):
        return string.replace('_', ' ')

    action_name = getattr(action, 'func', action).__name__
    param_names = get_fn_parameters(action)

    apply = coalesce(force, parsed_args[action_name])
    if apply is None:
        if param_names:
            apply = input(f"Do you want to {unsnake(action_name)}? "
                          f"Insert your {unsnake(param_names[0])} [Leave empty to skip]: ")
        else:
            apply = input(f"Do you want to {unsnake(action_name)}? [Yn] ") in ['', 'y', 'Y']

    if apply:
        with Halo(text=unsnake(action_name), spinner='bouncingBar'):
            if param_names:
                action(**{param_names[0]: apply})
            else:
                action()

    return apply


def add_action_toggle(parser: ArgumentParser,
                      fn: Union[partial, Callable[[], None], Callable[[str], None]],
                      force_bool: bool = False):
    """Add a new argument to the parser. NOTE: the parameter bound to the argument is the FIRST ONE in the signature"""
    params = get_fn_parameters(fn)
    docs = getattr(fn, 'func', fn).__doc__
    name = getattr(fn, 'func', fn).__name__
    add_with = partial(parser.add_argument, f"--{name.replace('_', '-')}", dest=name, help=docs)
    if force_bool or not params:
        add_with(action='store_true', default=None)
    else:
        add_with(default=None, metavar=params[0].upper())
