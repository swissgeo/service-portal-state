from datetime import UTC, datetime

from pydantic import Field

from app.schemas.state import StateId, StateItem


class DBStateItem(StateItem):
    id: StateId
    full_hash: str = Field(min_length=64, max_length=64)
    major_version: int = Field(ge=0)
    created: datetime
    last_accessed: datetime

    @classmethod
    def from_state_item(
        cls,
        state_id: StateId,
        full_hash: str,
        version: int,
        state: StateItem,
    ) -> DBStateItem:
        created = datetime.now(tz=UTC)
        data = state.model_dump(by_alias=True)
        data.update(
            {
                "id": state_id,
                "full_hash": full_hash,
                "major_version": version,
                "created": created,
                "last_accessed": created,
            }
        )
        return cls.model_validate(data)
