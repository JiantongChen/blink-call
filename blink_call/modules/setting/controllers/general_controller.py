from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

from blink_call.modules.i18n import get_i18n
from blink_call.modules.setting.bindings import ConfigBinder


class GeneralController:
    def __init__(self, setting_view):
        self.vm = setting_view.vm
        self.page = setting_view.general_page

        self.bind()

    def bind(self):
        ConfigBinder.bind_combo(self.vm, self.page.language_combo, "ui.language")
        ConfigBinder.bind_combo(self.vm, self.page.theme_combo, "ui.theme")

        self.page.manual_btn.clicked.connect(self.open_user_manual)
        self.vm.manual_link_text_changed.connect(self.on_manual_link_text_changed)

    def refresh_from_local_config(self):
        language_idx = self.page.language_combo.findData(self.vm.get_config("ui.language"))
        self.page.language_combo.blockSignals(True)
        self.page.language_combo.setCurrentIndex(0 if language_idx < 0 else language_idx)
        self.page.language_combo.blockSignals(False)

        theme_idx = self.page.theme_combo.findData(self.vm.get_config("ui.theme"))
        self.page.theme_combo.blockSignals(True)
        self.page.theme_combo.setCurrentIndex(0 if theme_idx < 0 else theme_idx)
        self.page.theme_combo.blockSignals(False)

        i18n = get_i18n(self.vm.get_config("ui.language"))

        self.page.manual_btn.setText(i18n["user_manual"])
        self.page.language_label.setText(i18n["language"])
        self.page.theme_label.setText(i18n["theme"])
        self.page.theme_combo.setItemText(0, i18n["light"])
        self.page.theme_combo.setItemText(1, i18n["dark"])
        self.on_manual_link_text_changed("user_manual")

    def on_manual_link_text_changed(self, key: str):
        i18n = get_i18n(self.vm.get_config("ui.language"))
        self.page.manual_label.setText(i18n[key])

    @staticmethod
    def open_user_manual():
        QDesktopServices.openUrl(QUrl("https://jiantongchen.github.io/blink-call/"))
