"""RickyCEO local Shorts pipeline."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("rickyceo")
except PackageNotFoundError:
    __version__ = "0.1.0"
