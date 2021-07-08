from functools import partial

import argparse

from .init_actions import *
from .init_framework import WorkingDirectory, prompt, add_action_toggle


def init(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--yes', '-y', help='Forces all boolean options to true', action='store_true', default=None)
    parser.add_argument('--dest', '-d', help='The destination of your epic project! :D', required=True)

    add_action_toggle(parser, setup_mila_user)
    add_action_toggle(parser, create_venv)
    add_action_toggle(parser, create_git_repo)
    add_action_toggle(parser, create_base_structure, force_bool=True)
    add_action_toggle(parser, setup_wandb)

    parsed = vars(parser.parse_args(args=args))

    base_dir = parsed['dest']

    prompt_with_args = partial(prompt, parsed_args=parsed)

    with WorkingDirectory(path=base_dir):
        os.mkdir('src')

        prompt_with_args(setup_mila_user)

        has_local_venv = prompt_with_args(create_venv, force=parsed['yes'])
        setup_wandb(project_name=base_dir, use_local_venv=has_local_venv)
        prompt_with_args(partial(create_base_structure, use_local_venv=has_local_venv), force=parsed['yes'])
        prompt_with_args(partial(create_git_repo, base_dir=base_dir))

        if has_local_venv:
            print(f'\nRemember to source your new environment with:\n    source {os.getcwd()}/venv/bin/activate\n')


def sys_main():
    try:
        init()
        return 0
    except Exception as e:
        import traceback
        print(e)
        return 1


if __name__ == '__main__':
    init()
