from typing import Any
import pprint


def save_json(json_dict: dict[str, Any], file_path: str) -> None:
    with open(file_path, "w") as file:
        file.write(pprint.pformat(json_dict, width=160, indent=1, compact=False, sort_dicts=False)
                   .replace("'", '"')#.replace('""', '"')
                   .replace("None", "null").replace("False", "false").replace("True", "true"))
