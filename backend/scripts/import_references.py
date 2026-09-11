"""Display the built-in official references used by the agent tool."""

import json

from src.tools.search_official_reference import REFERENCES


if __name__ == "__main__":
    print(json.dumps(REFERENCES, ensure_ascii=False, indent=2))
