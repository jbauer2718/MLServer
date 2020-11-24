from ..settings import ModelSettings
from ..registry import MultiModelRegistry
from ..repository import ModelRepository
from ..errors import ModelNotFound
from ..types import (
    RepositoryIndexRequest,
    RepositoryIndexResponse,
    RepositoryIndexResponseItem,
    State,
)


class ModelRepositoryHandlers:
    def __init__(self, repository: ModelRepository, model_registry: MultiModelRegistry):
        self._repository = repository
        self._model_registry = model_registry

    async def index(self, payload: RepositoryIndexRequest) -> RepositoryIndexResponse:
        all_model_settings = await self._repository.list()

        repository_items = []
        for model_settings in all_model_settings:
            index_item = await self._to_item(model_settings)
            if payload.ready:
                # TODO: If filtering by ready, we could ready directly from the
                # active model registry
                if index_item.state == State.READY:
                    repository_items.append(index_item)
            else:
                repository_items.append(index_item)

        return RepositoryIndexResponse(__root__=repository_items)

    async def _to_item(
        self, model_settings: ModelSettings
    ) -> RepositoryIndexResponseItem:
        item = RepositoryIndexResponseItem(
            name=model_settings.name,
            state=State.UNKNOWN,
            reason="",
        )

        item.state = await self._get_state(model_settings)

        if model_settings.parameters:
            item.version = model_settings.parameters.version

        return item

    async def _get_state(self, model_settings: ModelSettings) -> State:
        try:
            model = await self._model_registry.get_model(model_settings.name)
            if model.ready:
                return State.READY
        except ModelNotFound:
            return State.UNAVAILABLE

        return State.UNKNOWN

    async def load(self, name: str) -> bool:
        model_settings = await self._repository.find(name)

        # TODO: Move to separate method
        model_class = model_settings.implementation
        model = model_class(model_settings)  # type: ignore

        await self._model_registry.load(model)

        return True

    async def unload(self, name: str) -> bool:
        await self._model_registry.unload(name)

        return True
