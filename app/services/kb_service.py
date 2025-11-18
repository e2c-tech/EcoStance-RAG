import json
import os

KB_FILE = "kbs.json"

def get_all_kbs():
    """
    Reads the list of knowledge bases from the JSON file.
    """
    if not os.path.exists(KB_FILE):
        return []
    with open(KB_FILE, "r") as f:
        return json.load(f)

def add_kb(kb_name):
    """
    Adds a new knowledge base name to the JSON file.
    """
    kbs = get_all_kbs()
    if kb_name not in kbs:
        kbs.append(kb_name)
        with open(KB_FILE, "w") as f:
            json.dump(kbs, f, indent=4)

def remove_kb(kb_name):
    """
    Removes a knowledge base name from the JSON file.
    """
    kbs = get_all_kbs()
    if kb_name in kbs:
        kbs.remove(kb_name)
        with open(KB_FILE, "w") as f:
            json.dump(kbs, f, indent=4)
