from __future__ import annotations

from pathlib import Path
from typing import Any

from .client import load_json, resolve_path
from .knowledge_base import KnowledgeBase
from .recognizer import CultureRecognizerAgent
from .responder import ResponseComposerAgent
from .retriever import KnowledgeRetrieverAgent


class CulturalResponseAgent:
    def __init__(
        self,
        *,
        knowledge_base: KnowledgeBase,
        recognizer: CultureRecognizerAgent,
        retriever: KnowledgeRetrieverAgent,
        responder: ResponseComposerAgent,
    ) -> None:
        self.knowledge_base = knowledge_base
        self.recognizer = recognizer
        self.retriever = retriever
        self.responder = responder

    def answer(self, *, background: str, user_query: str) -> dict[str, Any]:
        recognition = self.recognizer.run(background=background, user_query=user_query)
        retrieval = self.retriever.run(
            background=background,
            user_query=user_query,
            recognition=recognition,
        )
        response = self.responder.run(
            background=background,
            user_query=user_query,
            recognition=recognition,
            knowledge_items=retrieval["items"],
        )
        return {
            "text": response["text"],
            "trace": {
                "recognition": recognition,
                "retrieval": {
                    "reason": retrieval["reason"],
                    "selected_items": [
                        {
                            "id": item.item_id,
                            "dimension": item.dimension,
                            "knowledge": item.knowledge,
                            "scene": item.scene,
                            "related_taboos": item.related_taboos,
                        }
                        for item in retrieval["items"]
                    ],
                },
                "support_points": response.get("support_points", []),
            },
        }


def build_agent(config_path: str | Path) -> CulturalResponseAgent:
    resolved_config_path = Path(config_path).resolve()
    config = load_json(resolved_config_path)
    project_root = resolved_config_path.parent.parent
    knowledge_root = resolve_path(project_root, str(config["knowledge_base"]["path"]))
    knowledge_base = KnowledgeBase.from_library(knowledge_root)
    recognizer = CultureRecognizerAgent(dict(config.get("recognizer_agent", {})), knowledge_base)
    retriever = KnowledgeRetrieverAgent(dict(config.get("retriever_agent", {})), knowledge_base)
    responder = ResponseComposerAgent(dict(config.get("responder_agent", {})))
    return CulturalResponseAgent(
        knowledge_base=knowledge_base,
        recognizer=recognizer,
        retriever=retriever,
        responder=responder,
    )
