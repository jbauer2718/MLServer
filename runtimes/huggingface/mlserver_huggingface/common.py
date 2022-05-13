import os
import json
from typing import Optional, Dict
from distutils.util import strtobool

from pydantic import BaseSettings
from mlserver.errors import MLServerError

from transformers.pipelines import pipeline
from transformers.pipelines.base import Pipeline
from transformers.models.auto.tokenization_auto import AutoTokenizer

from optimum.pipelines import SUPPORTED_TASKS as SUPPORTED_OPTIMUM_TASKS


HUGGINGFACE_TASK_TAG = "task"

ENV_PREFIX_HUGGINGFACE_SETTINGS = "MLSERVER_MODEL_HUGGINGFACE_"
HUGGINGFACE_PARAMETERS_TAG = "huggingface_parameters"
PARAMETERS_ENV_NAME = "PREDICTIVE_UNIT_PARAMETERS"

# Required as workaround until solved https://github.com/huggingface/optimum/issues/186
TRANSFORMER_CACHE_DIR = os.environ.get("TRANSFORMERS_CACHE", None)


class InvalidTranformerInitialisation(MLServerError):
    def __init__(self, code: int, reason: str):
        super().__init__(
            f"Huggingface server failed with {code}, {reason}",
            status_code=code,
        )


class HuggingFaceSettings(BaseSettings):
    """
    Parameters that apply only to alibi huggingface models
    """

    class Config:
        env_prefix = ENV_PREFIX_HUGGINGFACE_SETTINGS

    task: str = ""
    pretrained_model: Optional[str] = None
    pretrained_tokenizer: Optional[str] = None
    optimum_model: bool = False


def parse_parameters_from_env() -> Dict:
    """
    TODO
    """
    parameters = json.loads(os.environ.get(PARAMETERS_ENV_NAME, "[]"))

    type_dict = {
        "INT": int,
        "FLOAT": float,
        "DOUBLE": float,
        "STRING": str,
        "BOOL": bool,
    }

    parsed_parameters = {}
    for param in parameters:
        name = param.get("name")
        value = param.get("value")
        type_ = param.get("type")
        if type_ == "BOOL":
            parsed_parameters[name] = bool(strtobool(value))
        else:
            try:
                parsed_parameters[name] = type_dict[type_](value)
            except ValueError:
                raise InvalidTranformerInitialisation(
                    "Bad model parameter: "
                    + name
                    + " with value "
                    + value
                    + " can't be parsed as a "
                    + type_,
                    reason="MICROSERVICE_BAD_PARAMETER",
                )
            except KeyError:
                raise InvalidTranformerInitialisation(
                    "Bad model parameter type: "
                    + type_
                    + " valid are INT, FLOAT, DOUBLE, STRING, BOOL",
                    reason="MICROSERVICE_BAD_PARAMETER",
                )
    return parsed_parameters


def load_pipeline_from_settings(hf_settings: HuggingFaceSettings) -> Pipeline:
    """
    TODO
    """
    # TODO: Support URI for locally downloaded artifacts
    # uri = model_parameters.uri
    model = hf_settings.pretrained_model
    tokenizer = hf_settings.pretrained_tokenizer

    if model and not tokenizer:
        tokenizer = model

    if hf_settings.optimum_model:
        optimum_class = SUPPORTED_OPTIMUM_TASKS[hf_settings.task]["class"][0]
        model = optimum_class.from_pretrained(
            hf_settings.pretrained_model,
            from_transformers=True,
            cache_dir=TRANSFORMER_CACHE_DIR,
        )
        tokenizer = AutoTokenizer.from_pretrained(tokenizer)

    pp = pipeline(
        hf_settings.task,
        model=model,
        tokenizer=tokenizer,
    )
    return pp