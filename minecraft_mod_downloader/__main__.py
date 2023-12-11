"""Command-line execution of the `minecraft_mod_downloader` package."""

from collections.abc import Sequence

__all__: Sequence[str] = []

from minecraft_mod_downloader import console

if __name__ == "__main__":
    raise SystemExit(console.run())
