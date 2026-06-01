from PySide6.QtWidgets import QButtonGroup

from blink_call.modules.i18n import get_i18n
from blink_call.modules.setting.bindings import ConfigBinder


class CameraController:
    def __init__(self, setting_view):
        self.vm = setting_view.vm
        self.page = setting_view.camera_page

        self.bind()

    def bind(self):
        ConfigBinder.bind_spinbox(self.vm, self.page.local_id_spin, "camera.local_camera_id")
        ConfigBinder.bind_line_edit(self.vm, self.page.remote_ip_edit, "camera.remote.ip")
        ConfigBinder.bind_spinbox(self.vm, self.page.remote_port_spin, "camera.remote.port")
        ConfigBinder.bind_spinbox(self.vm, self.page.service_id_spin, "local_service.camera_id")
        ConfigBinder.bind_spinbox(self.vm, self.page.service_port_spin, "local_service.port")

        camera_mode_group = QButtonGroup()
        camera_mode_group.addButton(self.page.local_mode_radio)
        camera_mode_group.addButton(self.page.remote_mode_radio)
        self.page.local_mode_radio.setProperty("tag_value", "local")
        self.page.remote_mode_radio.setProperty("tag_value", "remote")
        ConfigBinder.bind_radio_group(self.vm, camera_mode_group, "camera.mode", self.update_mode_visibility)
        self.camera_mode_group = camera_mode_group

        self.page.start_btn.clicked.connect(self.vm.on_start_local_service)

    def refresh_from_local_config(self):
        if self.vm.get_config("camera.mode") == "remote":
            self.page.remote_mode_radio.setChecked(True)
            self.update_mode_visibility("remote")
        else:
            self.page.local_mode_radio.setChecked(True)
            self.update_mode_visibility("local")

        self.page.local_id_spin.setValue(int(self.vm.get_config("camera.local_camera_id") or 0))
        self.page.remote_ip_edit.setText(self.vm.get_config("camera.remote.ip") or "")
        self.page.remote_port_spin.setValue(int(self.vm.get_config("camera.remote.port") or 10000))
        self.page.service_id_spin.setValue(int(self.vm.get_config("local_service.camera_id") or 0))
        self.page.service_port_spin.setValue(int(self.vm.get_config("local_service.port") or 10000))

        i18n = get_i18n(self.vm.get_config("ui.language"))

        self.page.source_label.setText(i18n["choose_camera_source"])
        self.page.local_mode_radio.setText(i18n["local_camera"])
        self.page.remote_mode_radio.setText(i18n["remote_camera"])
        self.page.local_id_label.setText(i18n["camera_id"])
        self.page.remote_info_label.setText(i18n["remote_camera_service_info"])
        self.page.remote_ip_label.setText(i18n["ip"])
        self.page.remote_port_label.setText(i18n["port"])
        self.page.start_btn.setText(i18n["start_local_camera_service"])
        self.page.start_label.setText(i18n["start_local_camera_service"])
        self.page.service_label.setText(i18n["service_configuration_items"])
        self.page.service_id_label.setText(i18n["camera_id"])
        self.page.service_port_label.setText(i18n["port"])

    def update_mode_visibility(self, mode: str):
        is_local = mode != "remote"
        self.page.local_row.setVisible(is_local)
        self.page.remote_row.setVisible(not is_local)
