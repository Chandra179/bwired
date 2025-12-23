from abc import ABC, abstractmethod
import ollama

class BaseLLMEngine(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_message: str = "") -> str:
        pass

class LocalEngine(BaseLLMEngine):
    def __init__(self, model: str = "llama3.2"):
        self.model = model

    def generate(self, prompt: str, system_message: str = "You are a helpful assistant.") -> str:
        response = ollama.chat(
            model=self.model,
            messages=[
                {'role': 'system', 'content': system_message},
                {'role': 'user', 'content': prompt},
            ],
            options={
                'temperature': 0.1,
                'num_ctx': 4096,  # Limits context to 4k tokens to stay within 6GB VRAM
                'num_gpu': 35     # Ensures all layers stay on your GPU
            }
        )
        return response['message']['content']