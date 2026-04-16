def has_same_major(version: str, versions: list[str]) -> bool:
    major = version.split(".", 1)[0]
    return any(v.split(".", 1)[0] == major for v in versions)
