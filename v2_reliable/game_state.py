"""V2 game rules and state. Python decides outcomes; the LLM only narrates."""


def new_state():
    return {
        "inventory": [],
        "examined": [],
        "drawer_open": False,
        "painting_open": False,
        "door_locked": True,
        "escaped": False,
    }


def _resolve(section, name):
    """Map free text from the player to a canonical object/item name."""
    if not name or not isinstance(name, str):
        return None
    n = name.lower().strip()
    for key, entry in section.items():
        if n == key or any(alias in n for alias in entry["aliases"]):
            return key
    return None


def _r(ok, facts):
    return {"ok": ok, "facts": facts}


def apply_action(state, cfg, intent):
    """Validate an action, update the state, return {'ok', 'facts'}."""
    t = cfg["texts"]
    sol = cfg["solutions"]
    action = intent.get("action")
    target = _resolve(cfg["objects"], intent.get("target"))
    item = _resolve(cfg["items"], intent.get("item")) or _resolve(
        cfg["items"], intent.get("target")
    )
    code = intent.get("code")

    if state["escaped"]:
        return _r(False, t["game_over"])

    if action == "inventory":
        inv = ", ".join(state["inventory"]) or "nothing"
        return _r(True, f"The player is carrying: {inv}.")

    if action == "help":
        return _r(True, t["help"])

    if action == "examine":
        if target is None:
            if item and item in state["inventory"]:
                return _r(True, t["key_item"])
            return _r(False, t["unknown_object"])
        if target in ("desk", "bookshelf"):
            if target not in state["examined"]:
                state["examined"].append(target)
            return _r(True, t[target])
        if target == "drawer":
            if not state["drawer_open"]:
                return _r(True, t["drawer_locked"])
            key = "drawer_open_empty" if "brass key" in state["inventory"] else "drawer_open_key"
            return _r(True, t[key])
        if target == "painting":
            return _r(True, t["painting_open" if state["painting_open"] else "painting_locked"])
        if target == "door":
            return _r(True, t["door"])

    if action == "take":
        if item == "brass key":
            if "brass key" in state["inventory"]:
                return _r(False, t["have_key"])
            if not state["drawer_open"]:
                return _r(False, t["cannot_take"])
            state["inventory"].append("brass key")
            return _r(True, t["took_key"])
        return _r(False, t["cannot_take"])

    if action == "enter_code":
        if target not in ("drawer", "door"):
            return _r(False, t["nothing_happens"])
        if not code:
            return _r(False, t["no_code"])
        if target == "drawer":
            if state["drawer_open"]:
                return _r(False, t["drawer_already_open"])
            # prerequisite: the player must have seen the digits on the bookshelf
            if code == sol["drawer_code"] and "bookshelf" in state["examined"]:
                state["drawer_open"] = True
                return _r(True, t["drawer_unlocked"])
            return _r(False, t["wrong_code"])
        if target == "door":
            # prerequisite: the player must have opened the painting compartment
            if code == sol["door_code"] and state["painting_open"]:
                state["door_locked"] = False
                state["escaped"] = True
                return _r(True, t["escaped"])
            return _r(False, t["door_wrong"])

    if action == "use_item":
        if item is None or item not in state["inventory"]:
            return _r(False, t["no_item"])
        if item == "brass key" and target == "painting":
            if state["painting_open"]:
                return _r(False, t["painting_already_open"])
            state["painting_open"] = True
            return _r(True, t["key_opens_painting"])
        return _r(False, t["nothing_happens"])

    return _r(False, t["invalid"])