import click


@click.group()
def main() -> None:
    """Continuous profiler command line interface."""


if __name__ == "__main__":
    main()

