from .oids import METRIC_CATALOG, build_metric_definitions


def test_catalog_keys_are_unique():
    keys = [template.key for template in METRIC_CATALOG]
    assert len(keys) == len(set(keys))


def test_build_metric_definitions_matches_catalog_size():
    assert len(build_metric_definitions()) == len(METRIC_CATALOG)


def test_every_oid_is_a_dotted_numeric_string():
    for template in METRIC_CATALOG:
        parts = template.oid.split(".")
        assert parts and all(part.isdigit() for part in parts), template.oid
