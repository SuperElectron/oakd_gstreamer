# /utils/setup_logging.py

from pathlib import Path
from os import system
import logging
from datetime import datetime


def create_image_folder(folder="/logs/python"):
    system(f"mkdir -p {folder}/images")


def setup_logging(folder="/logs/python", filename="python.log", level=logging.DEBUG):
    try:
        system(f"mkdir -p {folder}")
        filepath = folder + '/' + filename
        Path(filepath).touch(mode=0o777, exist_ok=True)
        system(f"ln -sf /dev/stdout {filepath}")
        logging.basicConfig(filename=filepath, filemode="w", level=level)
        print(f"Python logger ({filepath}) started at {datetime.now()}\n", flush=True)
        return folder
    except Exception as err:
        print(f"ERROR (setup_logging): {err}")
        return False
