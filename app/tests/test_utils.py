from app.core.utils import has_same_major


# ---------------------------------------------------------
# 1. Match exists (positive case)
# ---------------------------------------------------------
def test_has_same_major_true():
    version = "1.2.3"
    versions = ["1.0.0", "2.0.0", "1.9.9"]

    assert has_same_major(version, versions) is True


# ---------------------------------------------------------
# 2. No match (negative case)
# ---------------------------------------------------------
def test_has_same_major_false():
    version = "3.2.1"
    versions = ["1.0.0", "2.5.0"]

    assert has_same_major(version, versions) is False


# ---------------------------------------------------------
# 3. Exact match only in input version list
# ---------------------------------------------------------
def test_has_same_major_exact_match():
    version = "2.1.0"
    versions = ["2.1.0"]

    assert has_same_major(version, versions) is True


# ---------------------------------------------------------
# 4. Empty versions list
# ---------------------------------------------------------
def test_has_same_major_empty_list():
    version = "1.2.3"
    versions = []

    assert has_same_major(version, versions) is False


# ---------------------------------------------------------
# 5. Multiple major versions mixed
# ---------------------------------------------------------
def test_has_same_major_mixed_versions():
    version = "10.0.1"
    versions = ["9.1.0", "10.2.3", "11.0.0"]

    assert has_same_major(version, versions) is True


# ---------------------------------------------------------
# 6. Edge case: malformed version strings
# ---------------------------------------------------------
def test_has_same_major_single_number():
    version = "7"
    versions = ["7", "8.0.0", "7.1"]

    assert has_same_major(version, versions) is True
