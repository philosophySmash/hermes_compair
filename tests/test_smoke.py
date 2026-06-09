def test_package_exposes_version_string():
    import hermes_compair

    assert isinstance(hermes_compair.__version__, str)
    assert hermes_compair.__version__
