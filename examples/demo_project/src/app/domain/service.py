from app.infra.db import connect


def run():
    return connect()


def complicated(value):
    total = 0
    if value > 10:
        for item in range(value):
            if item % 2:
                total += item
            else:
                total -= item
    elif value == 3:
        total = 3
    return total

