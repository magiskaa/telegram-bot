def name_conjugation(name, ending):
    name = name.strip()
    if ending == "lle":
        if name.endswith("kko"):
            return name[:-2] + "olle"
        elif name.endswith("tti"):
            return name[:-2] + "ille"
        else:
            return name + "lle"
    elif ending == "lla":
        if name.endswith("kko"):
            return name[:-2] + "olla"
        elif name.endswith("tti"):
            return name[:-2] + "illa"
        elif name.endswith("ti") or name.endswith("ni"):
            return name + "llä"
        else:
            return name + "lla"
    elif ending == "lta":
        if name.endswith("kko"):
            return name[:-2] + "olta"
        elif name.endswith("tti"):
            return name[:-2] + "ilta"
        elif name.endswith("ti") or name.endswith("ni"):
            return name + "ltä"
        else:
            return name + "lta"
    elif ending == "n":
        if name.endswith("kko"):
            return name[:-2] + "on"
        elif name.endswith("tti"):
            return name[:-2] + "in"
        else:
            return name + "n"
    else:
        return name + ending

def get_group_id():
    with open("data/group_id.txt", "r") as f:
        group_id = int(f.read().strip())
    return group_id
