from dataclasses import dataclass, field


@dataclass
class Item:
    names: list[str] = field(default_factory=list)


def main():
    return "ok"
