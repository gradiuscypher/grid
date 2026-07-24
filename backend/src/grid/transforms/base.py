"""Internal protocol for builtin (in-process) transforms.

Builtins implement the exact same request/response shape as a remote HTTP
transform (ARCHITECTURE §6) so any of them can be lifted out into its own
container later unchanged — `run()` is the same contract either way, just
invoked in-proc instead of over HTTP.
"""

from abc import ABC, abstractmethod
from typing import ClassVar

from grid.transforms.spec import RunRequest, RunResult, TransformDescriptor


class BaseTransform(ABC):
    descriptor: ClassVar[TransformDescriptor]

    @abstractmethod
    async def run(self, request: RunRequest) -> RunResult: ...
