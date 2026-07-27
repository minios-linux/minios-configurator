from system_utils import initrd_crypto_supported, is_xrdp_installed, parse_perchmode


def test_xrdp_availability_detection(tmp_path):
    assert not is_xrdp_installed(str(tmp_path))
    service = tmp_path / 'usr/lib/systemd/system/xrdp.service'
    service.parent.mkdir(parents=True)
    service.write_text('[Unit]\n', encoding='utf-8')
    assert is_xrdp_installed(str(tmp_path))


def test_initrd_crypto_capability_requires_marker(tmp_path):
    assert not initrd_crypto_supported(str(tmp_path))
    marker = tmp_path / 'run/initramfs/etc/minios-initramfs-crypt'
    marker.parent.mkdir(parents=True)
    marker.write_text('', encoding='utf-8')
    assert initrd_crypto_supported(str(tmp_path))


def test_parse_perchmode_reads_luks_without_performing_crypto_work():
    assert parse_perchmode('boot=live perchmode=luks perchsize=2000') == 'luks'
    assert parse_perchmode('boot=live') == ''
