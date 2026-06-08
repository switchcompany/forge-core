"""Forge Core — AI-powered backend test generation engine."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("switchforge")
except PackageNotFoundError:
    __version__ = "2.0.2"
