import os
import tempfile

import numpy as np

from oure.data.cpf_parser import CPFParser


def test_cpf_parser_basic():
    # Mock a simple CPF file content
    cpf_content = """
10 0 59215 43200.000000 0 6813354.341 0.000 0.000 0.000 7500.000 0.000
10 0 59215 43260.000000 0 6813354.341 100.000 0.000 0.000 7500.000 0.000
    """

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write(cpf_content)
        temp_path = f.name

    try:
        states = CPFParser.parse(temp_path, sat_id="TEST_SAT")
        assert len(states) == 2

        state1 = states[0]
        # x is 6813.354341 km
        assert np.isclose(state1.r[0], 6813.354341)
        assert np.isclose(state1.v[1], 7.5)  # vy = 7500 m/s = 7.5 km/s
        assert state1.sat_id == "TEST_SAT"
    finally:
        os.unlink(temp_path)


def test_cpf_parser_no_velocity():
    # Mock CPF without velocity (allowed in some cases)
    cpf_content = """
10 0 59215 43200.000000 0 6813354.341 0.000 0.000
    """
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write(cpf_content)
        temp_path = f.name

    try:
        states = CPFParser.parse(temp_path)
        assert len(states) == 1
        assert np.all(states[0].v == 0.0)
    finally:
        os.unlink(temp_path)
