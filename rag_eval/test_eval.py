
import os
from dotenv import load_dotenv

from deepeval import assert_test
from deepeval.test_case import (
    Turn,
    ConversationalTestCase,
    MultiTurnParams,
)
from deepeval.metrics import ConversationalGEval
from deepeval.models import GeminiModel

load_dotenv()


def test_professionalism():
    api_key = os.getenv("GOOGLE_API_KEY")
    assert api_key, "GOOGLE_API_KEY is missing from .env"

    gemini_model = GeminiModel(
        model="gemini-3.1-flash-lite",
        api_key=api_key,
    )

    professionalism_metric = ConversationalGEval(
        name="Professionalism",
        criteria=(
            "Evaluate whether the assistant communicates "
            "professionally, respectfully, and clearly."
        ),
        evaluation_params=[MultiTurnParams.CONTENT],
        threshold=0.5,
        model=gemini_model,
    )

    test_case = ConversationalTestCase(
        turns=[
            Turn(role="user", content="What is DeepEval?"),
            Turn(
                role="assistant",
                content=(
                    "DeepEval is an open-source LLM "
                    "evaluation framework."
                ),
            ),
        ]
    )

    assert_test(test_case, [professionalism_metric])
