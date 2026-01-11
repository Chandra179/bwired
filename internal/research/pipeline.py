import logging

logger = logging.getLogger(__name__)


class ResearchPipeline:
    def __init__(self, config: dict):
        self.config = config

    async def run(self, task_id: str):
        raise NotImplementedError