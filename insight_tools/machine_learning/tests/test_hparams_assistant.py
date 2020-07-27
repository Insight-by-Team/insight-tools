import numpy as np

from insight_tools.machine_learning import HParamsAssistant
from insight_tools.machine_learning.tests.test_module_with_imports import \
    DummyModel


def test_hparams_assistant():
    hparams = {
        'kernel_size': 3,
        'wavenumbers': {
            '__class__': 'linspace',
            '*args': [500, 3500, 1408]
        },
    }

    model = DummyModel()
    assistant = HParamsAssistant(save_all_params_to_model=True)
    setted_params = assistant.parametrize(hparams, model)

    assert 'kernel_size' in setted_params
    assert 'wavenumbers' in setted_params
    assert type(setted_params['wavenumbers']) == np.ndarray
