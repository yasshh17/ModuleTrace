from abc import ABC, abstractmethod


class ERPClient(ABC):
    @abstractmethod
    async def get_module(self, serial_number: str) -> dict:
        ...

    @abstractmethod
    async def sync_module(self, data: dict) -> None:
        ...

    @abstractmethod
    async def create_rma(self, module_id: str, reason: str) -> dict:
        ...
