from collections.abc import Iterable, Mapping

from app.syntheticz.schemas import SyntheticzExternalSystem, SyntheticzStatus


class SyntheticError(Exception):
    """Raised by a synthetic check function when one or more external systems are unhealthy.

    The raiser must report which external systems failed, so that the endpoint can return the
    per-system status in the response body and the monitoring system can tell "the service is
    broken" apart from "a dependency is broken".

    Args:
        failed: names of the external systems that are DOWN. Either an iterable of names, or a
            mapping of name to a failure reason (the reason is logged, never sent to the client).
        message: optional human readable explanation, defaults to a message listing the systems.

    Raises:
        ValueError: if no failed external system is provided, as a SyntheticError without a
            failed dependency carries no actionable information.
    """

    def __init__(
        self,
        failed: Mapping[str, str] | Iterable[str],
        message: str | None = None,
    ) -> None:
        # A mapping keeps its per-system reason, a plain iterable of names has none.
        # NOTE: narrowing a `Mapping[str, str] | Iterable[str]` against the bare `Mapping` class
        # loses the type parameters in `ty`, which then sees `object` keys and values here.
        if isinstance(failed, Mapping):
            self.failed: dict[str, str | None] = dict(failed)  # ty: ignore[no-matching-overload]
        else:
            self.failed = dict.fromkeys(failed)

        if not self.failed:
            raise ValueError(
                "SyntheticError requires at least one failed external system, "
                "so that the response can report which dependency is DOWN"
            )

        self.message = message or f"Unhealthy external systems: {', '.join(sorted(self.failed))}"
        super().__init__(self.message)

    def as_external_systems(self) -> dict[str, SyntheticzExternalSystem]:
        """Return the failed external systems as DOWN entries for the response body."""
        return {
            name: SyntheticzExternalSystem(status=SyntheticzStatus.DOWN) for name in self.failed
        }
