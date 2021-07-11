import shutil
import sys

import buddy_init.init_actions

EXAMPLE_PROJECT_PATH = "buddy_example_project/"


def preflight_check():
    if shutil.which('ssh') is None:
        raise Exception('missing ssh, you can install it with "sudo apt install openssl-client"')
    if shutil.which('git') is None:
        raise Exception('missing git, you can install it with "sudo apt install git"')
    if shutil.which('pip') is None:
        raise Exception('missing pip, you can install it with "sudo apt install python-pip"')


def enforce_answer_list(question, possible_answers):
    possible_answers = [pa.lower() for pa in possible_answers]
    text = f"{question} [{'|'.join(possible_answers)}]"
    answer = input(text).lower()
    if possible_answers and answer not in possible_answers:
        while answer := input(text).lower() not in possible_answers:
            pass
    return answer


def init():
    preflight_check()
    buddy_init.init_actions.setup_ssh()
    buddy_init.init_actions.setup_wandb()
    buddy_init.init_actions.setup_github()
    buddy_init.init_actions.setup_tutorial()


def sys_main():
    return_code = 1
    try:
        init()
        return_code = 0
    except Exception as e:
        import traceback
        print('Error: %s' % e, file=sys.stderr)

    sys.exit(return_code)
