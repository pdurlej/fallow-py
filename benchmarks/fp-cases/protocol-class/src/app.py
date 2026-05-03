from typing import Protocol


class Service(Protocol):
    def run(self) -> str:
        ...


def main():
    return "ok"
