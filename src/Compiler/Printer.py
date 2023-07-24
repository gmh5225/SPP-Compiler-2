from typing import Any
import pprint, json, jsonpickle


def save_json(json_dict: dict[str, Any], file_path: str) -> None:
    # e = jsonpickle.encode(json_dict, indent=4)
    # open(file_path, "w").write(e)
    with open(file_path, "w") as file:
        file.write(pprint.pformat(json_dict, indent=1, compact=True, sort_dicts=False)
                   .replace("'", '"').replace('""', '"')
                   .replace("None", "null").replace("False", "false").replace("True", "true"))
