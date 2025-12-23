import os
from jinja2 import Template

class PromptManager:
    def __init__(self, template_dir: str):
        self.template_dir = template_dir

    def build_rag_prompt(self, query: str, context_chunks: list[str]) -> str:
        """
        Combines the user query and retrieved chunks into a final string.
        """
        # Load your system prompt file
        path = os.path.join(self.template_dir, "system_prompt.j2")
        with open(path, "r") as f:
            template = Template(f.read())
        
        # Join chunks into a single string with separators
        context_text = "\n\n---\n\n".join(context_chunks)
        
        return template.render(
            context=context_text,
            query=query
        )