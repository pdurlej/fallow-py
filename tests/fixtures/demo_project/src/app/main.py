import importlib

import missingdep
import requests

from app.domain.service import run
from app import cycle_a

NAME = "app.dynamic_unknown"
importlib.import_module("app.dynamic_mod")
importlib.import_module(NAME)


def main():
    return run(), requests.__name__, missingdep, cycle_a.VALUE
