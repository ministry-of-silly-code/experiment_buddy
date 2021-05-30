import argparse
import inspect
import types
from typing import Dict

wandb_escape = "^"


def _is_valid_hyperparam(key, value):
    if key.startswith("__") and key.endswith("__"):
        return False
    if key == "_":
        return False
    if isinstance(value, (types.FunctionType, types.MethodType, types.ModuleType)):
        return False
    return True


# noinspection DuplicatedCode
class MaMan:
    def __init__(self):
        self.hyperparams = {}

    class __ParamContext:
        def __init__(self, ma_man):
            self.ma_man = ma_man

        def __enter__(self):
            f = inspect.currentframe().f_back
            self.old_vars = set(f.f_locals.keys())
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            f = inspect.currentframe().f_back
            self.ma_man.hyperparams = {name: val
                                       for name, val in f.f_locals.items()
                                       if name not in self.old_vars}

    def parameters_block(self):
        return MaMan.__ParamContext(self)

    def register(self, config_params: Dict[str, str]):
        # TODO: fails on nested config object
        if any(k.startswith(wandb_escape) for k in config_params.keys()):
            raise NameError(f"{wandb_escape} is a reserved prefix")

        parser = argparse.ArgumentParser()
        parser.add_argument('_ignored', nargs='*')

        for k, v in config_params.items():
            if _is_valid_hyperparam(k, v):
                parser.add_argument(f"--{k}", f"--^{k}", type=type(v), default=v)

        parsed = parser.parse_args()

        cli_param_overrides = {k.lstrip(wandb_escape): v for k, v in vars(parsed).items()}

        self.hyperparams = {**config_params, **cli_param_overrides}
