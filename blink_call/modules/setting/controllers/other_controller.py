from pathlib import Path

from PySide6.QtWidgets import QButtonGroup, QFileDialog, QMessageBox

from blink_call.modules.i18n import get_i18n
from blink_call.modules.setting.bindings import ConfigBinder


class OtherController:
    def __init__(self, setting_view):
        self.setting_view = setting_view
        self.vm = setting_view.vm
        self.page = setting_view.other_page

        self.bind()

    def bind(self):
        ConfigBinder.bind_spinbox(self.vm, self.page.duration_spin, "recording.max_duration_min")

        debug_mode_group = QButtonGroup()
        debug_mode_group.addButton(self.page.debug_on_radio)
        debug_mode_group.addButton(self.page.debug_off_radio)
        self.page.debug_on_radio.setProperty("tag_value", True)
        self.page.debug_off_radio.setProperty("tag_value", False)
        ConfigBinder.bind_radio_group(self.vm, debug_mode_group, "debug_mode", self.update_debug_logging_visibility)
        self.debug_mode_group = debug_mode_group

        debug_log_save_group = QButtonGroup()
        debug_log_save_group.addButton(self.page.log_save_yes_radio)
        debug_log_save_group.addButton(self.page.log_save_no_radio)
        self.page.log_save_yes_radio.setProperty("tag_value", True)
        self.page.log_save_no_radio.setProperty("tag_value", False)
        ConfigBinder.bind_radio_group(
            self.vm,
            debug_log_save_group,
            "debug_log.save_to_local",
            self.update_debug_logging_visibility,
        )
        self.debug_log_save_group = debug_log_save_group

        self.page.recording_btn.clicked.connect(self.vm.start_recording)
        self.page.path_btn.clicked.connect(self.on_choose_recording_dir)
        self.page.log_path_btn.clicked.connect(self.on_choose_debug_log_dir)
        self.page.reset_btn.clicked.connect(self.on_restore_default_config)

    def refresh_from_local_config(self):
        if bool(self.vm.get_config("debug_mode")):
            self.page.debug_on_radio.setChecked(True)
        else:
            self.page.debug_off_radio.setChecked(True)

        if bool(self.vm.get_config("debug_log.save_to_local")):
            self.page.log_save_yes_radio.setChecked(True)
        else:
            self.page.log_save_no_radio.setChecked(True)
        self.page.log_path_value_label.setText(self.vm.get_config("debug_log.local_dir") or "")
        self.update_debug_logging_visibility()

        recording_max_duration_min = int(self.vm.get_config("recording.max_duration_min") or 1)
        self.page.duration_spin.setValue(max(1, min(1440, recording_max_duration_min)))
        self.page.path_value_label.setText(self.vm.get_config("recording.local_dir") or str(Path.home() / "Desktop"))

        i18n = get_i18n(self.vm.get_config("ui.language"))

        self.page.debug_label.setText(i18n["debug_mode"])
        self.page.recording_label.setText(i18n["record_current_camera_data"])
        self.page.recording_btn.setText(i18n["start_recording"])
        self.page.duration_label.setText(i18n["duration"])
        self.page.duration_unit_label.setText(i18n["minute"])
        self.page.path_label.setText(i18n["local_folder"])
        self.page.path_btn.setText(i18n["choose_folder"])
        self.page.debug_on_radio.setText(i18n["on"])
        self.page.debug_off_radio.setText(i18n["off"])
        self.page.log_save_label.setText(i18n["save_to_local"])
        self.page.log_save_yes_radio.setText(i18n["yes"])
        self.page.log_save_no_radio.setText(i18n["no"])
        self.page.log_path_label.setText(i18n["local_file_path"])
        self.page.log_path_btn.setText(i18n["choose_folder"])
        self.page.reset_btn.setText(i18n["restore_defaults"])
        self.page.reset_label.setText(i18n["restore_defaults"])

    def on_choose_recording_dir(self):
        i18n = get_i18n(self.vm.get_config("ui.language"))
        current_dir = self.vm.get_config("recording.local_dir", source="temp") or str(Path.home() / "Desktop")
        dialog = QFileDialog(self.setting_view, i18n["choose_recording_folder"], current_dir)
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)

        if dialog.exec() != QFileDialog.DialogCode.Accepted:
            return

        selected_list = dialog.selectedFiles()
        if not selected_list:
            return
        selected = selected_list[0]

        self.vm.set_config("recording.local_dir", selected)
        self.page.path_value_label.setText(selected)

    def on_choose_debug_log_dir(self):
        i18n = get_i18n(self.vm.get_config("ui.language"))
        current_dir = self.vm.get_config("debug_log.local_dir", source="temp") or ""
        dialog = QFileDialog(self.setting_view, i18n["choose_local_log_folder"], current_dir)
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)

        if dialog.exec() != QFileDialog.DialogCode.Accepted:
            return

        selected_list = dialog.selectedFiles()
        if not selected_list:
            return
        selected = selected_list[0]

        self.vm.set_config("debug_log.local_dir", selected)
        self.page.log_path_value_label.setText(selected)

    def on_restore_default_config(self):
        i18n = get_i18n(self.vm.get_config("ui.language"))
        msg = QMessageBox(self.setting_view)
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setWindowTitle(i18n["restore_defaults"])
        msg.setText(i18n["are_you_sure_to_restore_default_settings"])
        confirm_btn = msg.addButton(i18n["confirm"], QMessageBox.ButtonRole.AcceptRole)
        msg.addButton(i18n["close"], QMessageBox.ButtonRole.RejectRole)
        msg.exec()
        if msg.clickedButton() == confirm_btn:
            self.vm.restore_default_config()

    def update_debug_logging_visibility(self, _value=None):
        is_debug_on = bool(self.page.debug_on_radio.isChecked())
        is_save_local = bool(self.page.log_save_yes_radio.isChecked())
        self.page.log_save_row.setVisible(is_debug_on)
        self.page.log_path_row.setVisible(is_debug_on and is_save_local)
