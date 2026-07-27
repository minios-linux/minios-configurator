from main_configurator import applicability_for_key


def test_field_applicability_classes():
    assert applicability_for_key('LIVE_HOSTNAME') == 'next-boot'
    assert applicability_for_key('LIVE_USERNAME') == 'new-session'
    assert applicability_for_key('LIVE_XRDP_MODE') == 'new-session'
    assert applicability_for_key('LIVE_MODULE_MODE') == 'next-boot'
    assert applicability_for_key('EXPORT_LOGS') == 'next-boot'
