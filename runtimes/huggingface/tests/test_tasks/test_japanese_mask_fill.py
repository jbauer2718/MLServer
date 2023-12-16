import pytest
from mlserver.settings import ModelSettings, ModelParameters
from mlserver_huggingface import HuggingFaceRuntime
from mlserver_huggingface.codecs import HuggingfaceRequestCodec


@pytest.fixture
def bert_japanese_settings(request) -> ModelSettings:
    if (not request.config.option.test_hg_tasks) or (
        not request.config.option.test_ja_support
    ):
        pytest.skip()

    return ModelSettings(
        name="model",
        implementation=HuggingFaceRuntime,
        parameters=ModelParameters(
            extra={
                "task": "fill-mask",
                "pretrained_model": "cl-tohoku/bert-base-japanese",
                "pretrained_tokenizer": "cl-tohoku/bert-base-japanese",
            }
        ),
    )


@pytest.fixture
async def current_runtime(bert_japanese_settings: ModelSettings) -> HuggingFaceRuntime:
    runtime = HuggingFaceRuntime(bert_japanese_settings)
    await runtime.load()
    return runtime


@pytest.fixture
def japanese_text_request():
    # Test sentence: Is the sky really [MASK]?
    test_sentence = "実際に空が[MASK]のか？"
    # [MASK] = visible
    expected_output = "見える"

    outputs = [expected_output]
    reqs = HuggingfaceRequestCodec.encode_request(
        {"inputs": [test_sentence]},
        use_bytes=False,
    )
    return reqs, outputs


async def test_infer(current_runtime, japanese_text_request):
    reqs, expected_outputs = japanese_text_request
    resp = await current_runtime.predict(reqs)
    decoded = HuggingfaceRequestCodec.decode_response(resp)

    for req, expected_output in zip(list(decoded.items()), expected_outputs):
        top_result = req[1][0]
        assert top_result["token_str"] == expected_output, "Inference is correct!"