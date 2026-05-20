from app.erp.client import ERPClient


class MockERPClient(ERPClient):
    async def get_module(self, serial_number: str) -> dict:
        return {"serial_number": serial_number, "status": "active", "source": "mock"}

    async def sync_module(self, data: dict) -> None:
        pass

    async def create_rma(self, module_id: str, reason: str) -> dict:
        return {"rma_id": f"MOCK-RMA-{module_id[:8]}", "status": "created"}
