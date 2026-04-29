import yaml
import os

def load_config():
    """
    Loads config.yaml from the same directory as this file.
    Expands environment variables inside the YAML.
    """
    base_dir = os.path.dirname(__file__)
    path = os.path.join(base_dir, "config.yaml")

    with open(path, "r") as f:
        raw = f.read()

    # Expand ${VAR} inside YAML
    raw = os.path.expandvars(raw)

    return yaml.safe_load(raw)
