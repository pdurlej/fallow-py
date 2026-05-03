try:
    import orjson
except (ImportError, ModuleNotFoundError):
    orjson = None


def main():
    return orjson
