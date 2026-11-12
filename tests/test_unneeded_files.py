import pytest

from unneeded_files import is_unneeded


@pytest.mark.parametrize(
    "path",
    [
        "PySide6/opengl32sw.dll",
        "PySide6/Qt6Network.dll",
        "PySide6/QtNetwork.pyd",
        "PySide6/Qt6Svg.dll",
        "PySide6/QtSvg.pyd",
        "PySide6/translations/qt_de.qm",
        "PySide6/plugins/tls/qschannelbackend.dll",
        "PySide6/plugins/networkinformation/qnetworklistmanager.dll",
        "PySide6/plugins/iconengines/qsvgicon.dll",
        "PySide6/plugins/imageformats/qgif.dll",
        "PySide6/plugins/imageformats/qsvg.dll",
        "_internal/PySide6/plugins/imageformats/qwebp.dll",
        "PySide6\\plugins\\imageformats\\qjpeg.dll",
    ],
)
def test_a_file_mathdoer_never_uses_is_unneeded(path):
    assert is_unneeded(path)


@pytest.mark.parametrize(
    "path",
    [
        "PySide6/Qt6Core.dll",
        "PySide6/Qt6Gui.dll",
        "PySide6/Qt6Widgets.dll",
        "PySide6/QtWidgets.pyd",
        "PySide6/plugins/imageformats/qico.dll",
        "PySide6/plugins/platforms/qwindows.dll",
        "PySide6/plugins/styles/qmodernwindowsstyle.dll",
        "PySide6/MSVCP140.dll",
        "mathdoer/interface/icon.ico",
        "python/python313.dll",
        "Qt6Network.dll",  # not PySide6's
    ],
)
def test_a_file_mathdoer_needs_is_kept(path):
    assert not is_unneeded(path)


def test_the_folders_themselves_are_not_files_and_are_kept():
    assert not is_unneeded("PySide6")
    assert not is_unneeded("PySide6/plugins")
