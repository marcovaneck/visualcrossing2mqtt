import os


def retrieve_cfg(key: str, default: str = None, optional: bool = False) -> str:
    val = os.environ.get(key, os.environ.get(key.replace('.', '_'), default))
    if not optional and val is None:
        raise RuntimeError(f'Required env value is missing {key}')
    return val


def retrieve_cfg_int(key: str, default: int) -> int:
    return int(retrieve_cfg(key=key, default=str(default)))
