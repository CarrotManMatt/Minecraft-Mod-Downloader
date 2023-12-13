"""
Context manager to suppress anything sent to `std_out` & `std_err, depends upon verbosity.

Messages are allowed to be sent to `std_out` & `std_err` once this context manager exits,
as the previous values of `sys.std_out` & `sys.std_err` are restored.
"""

from collections.abc import Sequence

__all__: Sequence[str] = ("SuppressStdOutAndStdErr",)

import contextlib
from contextlib import AbstractContextManager
from io import StringIO
from types import TracebackType


class SuppressStdOutAndStdErr:
    """
    Context manager to suppress anything sent to `std_out` & `std_err, depends upon verbosity.

    The previous values of `sys.std_out` & `sys.std_err` are restored
    when exiting the context manager.
    """

    def __init__(self, verbosity: int = 1) -> None:
        # noinspection SpellCheckingInspection
        """
        Initialise a new SuppressStdOutAndStdErr context manager instance.

        The current values of `sys.stdout` & `sys.std_err` are stored for future reference
        to revert back to upon exiting the context manager.
        """
        self.verbosity: int = verbosity
        self._stdout_redirector: AbstractContextManager = contextlib.redirect_stdout(
            StringIO()
        )
        self._stderr_redirector: AbstractContextManager = contextlib.redirect_stderr(
            StringIO()
        )
        self._redirectors_were_entered: bool = False

    def __enter__(self) -> None:
        """Enter the context manager, suppressing anything sent to `std_out` & `std_err`."""
        if self.verbosity < 1:
            self._redirectors_were_entered = True
            self._stdout_redirector.__enter__()
            self._stderr_redirector.__enter__()

    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None) -> None:  # noqa: E501
        """Exit the context manager, restoring `std_out` & `std_err`."""
        exception_was_raised: bool = bool(
            exc_type is not None
            or exc_val is not None
            or exc_tb is not None
        )
        if self.verbosity < 0 and exception_was_raised:
            return

        if self._redirectors_were_entered:
            self._stdout_redirector.__exit__(exc_type, exc_val, exc_tb)
            self._stderr_redirector.__exit__(exc_type, exc_val, exc_tb)
