import json

from oure.data.cdm_parser import CDMParser


def test_cdm_parser(tmp_path):
    cdm_data = {
        "body": {
            "TCA": "2026-03-12T14:23:11Z",
            "MISS_DISTANCE": 0.5,
            "RELATIVE_SPEED": 12.5,
            "segment1": {
                "metadata": {"OBJECT_DESIGNATOR": "SAT1"},
                "data": {
                    "state_vector": {
                        "X": 7000,
                        "Y": 0,
                        "Z": 0,
                        "X_DOT": 0,
                        "Y_DOT": 7.5,
                        "Z_DOT": 0,
                    },
                    "covariance_matrix": {"CR11": 1.0, "CR22": 1.0, "CR33": 1.0},
                },
            },
            "segment2": {
                "metadata": {"OBJECT_DESIGNATOR": "SAT2"},
                "data": {
                    "state_vector": {
                        "X": 7000.5,
                        "Y": 0,
                        "Z": 0,
                        "X_DOT": 0,
                        "Y_DOT": -7.5,
                        "Z_DOT": 0,
                    },
                    "covariance_matrix": {"CR11": 1.0, "CR22": 1.0, "CR33": 1.0},
                },
            },
        }
    }

    cdm_file = tmp_path / "test_cdm.json"
    with open(cdm_file, "w") as f:
        json.dump(cdm_data, f)

    event = CDMParser.parse_json(str(cdm_file))

    assert event.primary_id == "SAT1"
    assert event.secondary_id == "SAT2"
    assert event.miss_distance_km == 0.5
    assert event.primary_state.r[0] == 7000
    assert event.primary_covariance.matrix[0, 0] == 1.0
