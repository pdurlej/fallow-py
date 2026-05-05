import importlib

import missingdep
import requests

from app import PublicThing
from app import cycle_a
from app.domain.service import run

NAME = "app.dynamic_unknown"
importlib.import_module("app.dynamic_mod")
importlib.import_module(NAME)


def main():
    thing = PublicThing()
    return run(), thing.label(), requests.__name__, missingdep, cycle_a.VALUE

