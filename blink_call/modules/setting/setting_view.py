from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from blink_call.core.model_files_manager import ModelFilesManager
from blink_call.modules.i18n import get_i18n
from blink_call.modules.setting.setting_viewmodel import SettingViewModel
from blink_call.modules.setting.subview import (
    build_blink_call_page,
    build_camera_page,
    build_general_page,
    build_other_page,
)
from blink_call.widget import InteractionBlockOverlay, NoWheelSpinBox


class SettingView(QWidget):
    close_setting_popup = Signal()

    def __init__(self, vm: SettingViewModel, parent=None):
        super().__init__(parent)
        self.vm = vm
        self.blink_call_sequence_rows = []
        self.blink_call_audio_file_values = [f"ring_{i:02d}.wav" for i in range(1, 11)]
        self.blink_call_audio_duration_values = [10, 30, 60, 300, 600, 1800, 3600, -1]
        self._preview_sound = QSoundEffect(self)
        self.model_files_manager = ModelFilesManager()

        self.setObjectName("settingOverlay")

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(120, 60, 120, 60)

        self.panel = QFrame()
        self.panel.setObjectName("settingPanel")
        root_layout.addWidget(self.panel)

        self.model_files_block_overlay = InteractionBlockOverlay(self)
        self.model_files_block_overlay.setObjectName("settingModelFilesBlockOverlay")
        self.model_files_block_overlay.hide()

        panel_layout = QVBoxLayout(self.panel)
        panel_layout.setContentsMargins(20, 20, 20, 20)
        panel_layout.setSpacing(16)

        self.title_label = QLabel("Settings")
        self.title_label.setObjectName("settingTitle")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        panel_layout.addWidget(self.title_label)

        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.addLayout(content_layout, 1)

        left_nav_scroll = QScrollArea()
        left_nav_scroll.setObjectName("settingLeftScroll")
        left_nav_scroll.setWidgetResizable(True)
        left_nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_nav_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_nav_scroll.setFixedWidth(160)
        content_layout.addWidget(left_nav_scroll)

        left_nav = QFrame()
        left_nav.setObjectName("settingLeftNav")
        left_nav_scroll.setWidget(left_nav)

        left_nav_layout = QVBoxLayout(left_nav)
        left_nav_layout.setContentsMargins(12, 12, 12, 12)
        left_nav_layout.setSpacing(12)

        self.general_nav_row, self.general_nav_btn, self.general_nav_icon = self._create_nav_item("General")
        self.camera_nav_row, self.camera_nav_btn, self.camera_nav_icon = self._create_nav_item("Camera")
        self.blink_call_nav_row, self.blink_call_nav_btn, self.blink_call_nav_icon = self._create_nav_item("Blink Call")
        self.other_nav_row, self.other_nav_btn, self.other_nav_icon = self._create_nav_item("Others")

        setting_pixmap = QPixmap("assets/icons/setting.png").scaled(25, 25, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.general_nav_icon.setPixmap(setting_pixmap)
        camera_pixmap = QPixmap("assets/icons/camera.png").scaled(25, 25, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.camera_nav_icon.setPixmap(camera_pixmap)
        blink_call_pixmap = QPixmap("assets/icons/algorithm.png").scaled(
            25, 25, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.blink_call_nav_icon.setPixmap(blink_call_pixmap)
        others_pixmap = QPixmap("assets/icons/others.png").scaled(25, 25, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.other_nav_icon.setPixmap(others_pixmap)

        self.nav_rows = [self.general_nav_row, self.camera_nav_row, self.blink_call_nav_row, self.other_nav_row]
        self.nav_icons = [self.general_nav_icon, self.camera_nav_icon, self.blink_call_nav_icon, self.other_nav_icon]

        left_nav_layout.addWidget(self.general_nav_row)
        left_nav_layout.addWidget(self.camera_nav_row)
        left_nav_layout.addWidget(self.blink_call_nav_row)
        left_nav_layout.addWidget(self.other_nav_row)
        left_nav_layout.addStretch()

        nav_group = QButtonGroup(self)
        nav_group.setExclusive(True)
        nav_group.addButton(self.general_nav_btn, 0)
        nav_group.addButton(self.camera_nav_btn, 1)
        nav_group.addButton(self.blink_call_nav_btn, 2)
        nav_group.addButton(self.other_nav_btn, 3)
        nav_group.idClicked.connect(self.on_switch_setting_page)

        vline = QFrame()
        vline.setObjectName("settingCenterDivider")
        vline.setFrameShape(QFrame.Shape.VLine)
        content_layout.addWidget(vline)

        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("settingContentStack")
        content_layout.addWidget(self.content_stack, 1)

        self._attach_widgets(build_general_page(self.content_stack))
        self._attach_widgets(build_camera_page(self.content_stack))
        self._attach_widgets(build_blink_call_page(self.content_stack))
        self._attach_widgets(build_other_page(self.content_stack))

        self.bind_combo(self.language_combo, "ui.language")
        self.bind_combo(self.theme_combo, "ui.theme")
        self.bind_spinbox(self.local_camera_id, "camera.local_camera_id")
        self.bind_line_edit(self.remote_ip, "camera.remote.ip")
        self.bind_spinbox(self.remote_port, "camera.remote.port")
        self.bind_spinbox(self.service_camera_id, "local_service.camera_id")
        self.bind_spinbox(self.service_port, "local_service.port")
        self.bind_spinbox(self.recording_duration_spin, "recording.max_duration_min")
        self.bind_combo(self.blink_call_audio_file_combo, "blink_call.audio.file")
        self.bind_combo(self.blink_call_audio_duration_combo, "blink_call.audio.play_duration_s")
        self.bind_slider(self.blink_call_audio_volume_slider, "blink_call.audio.volume")

        camera_mode_group = QButtonGroup(self)
        camera_mode_group.addButton(self.camera_local_mode_radio)
        camera_mode_group.addButton(self.camera_remote_mode_radio)
        self.camera_local_mode_radio.setProperty("tag_value", "local")
        self.camera_remote_mode_radio.setProperty("tag_value", "remote")
        self.bind_radio_group(camera_mode_group, "camera.mode", self._update_camera_mode_visibility)

        debug_mode_group = QButtonGroup(self)
        debug_mode_group.addButton(self.debug_mode_on_radio)
        debug_mode_group.addButton(self.debug_mode_off_radio)
        self.debug_mode_on_radio.setProperty("tag_value", True)
        self.debug_mode_off_radio.setProperty("tag_value", False)
        self.bind_radio_group(debug_mode_group, "debug_mode", self._update_debug_logging_visibility)

        debug_log_save_group = QButtonGroup(self)
        debug_log_save_group.addButton(self.debug_log_save_yes_radio)
        debug_log_save_group.addButton(self.debug_log_save_no_radio)
        self.debug_log_save_yes_radio.setProperty("tag_value", True)
        self.debug_log_save_no_radio.setProperty("tag_value", False)
        self.bind_radio_group(debug_log_save_group, "debug_log.save_to_local", self._update_debug_logging_visibility)

        blink_call_group = QButtonGroup(self)
        blink_call_group.addButton(self.blink_call_enabled_radio)
        blink_call_group.addButton(self.blink_call_disabled_radio)
        self.blink_call_enabled_radio.setProperty("tag_value", True)
        self.blink_call_disabled_radio.setProperty("tag_value", False)
        self.bind_radio_group(blink_call_group, "blink_call.enabled", self._update_blink_call_sequence_visibility)

        blink_call_progress_group = QButtonGroup(self)
        blink_call_progress_group.addButton(self.blink_call_progress_show_radio)
        blink_call_progress_group.addButton(self.blink_call_progress_hide_radio)
        self.blink_call_progress_show_radio.setProperty("tag_value", True)
        self.blink_call_progress_hide_radio.setProperty("tag_value", False)
        self.bind_radio_group(blink_call_progress_group, "blink_call.show_home_progress_bar")

        blink_call_audio_group = QButtonGroup(self)
        blink_call_audio_group.addButton(self.blink_call_audio_enable_on_radio)
        blink_call_audio_group.addButton(self.blink_call_audio_enable_off_radio)
        self.blink_call_audio_enable_on_radio.setProperty("tag_value", True)
        self.blink_call_audio_enable_off_radio.setProperty("tag_value", False)
        self.bind_radio_group(
            blink_call_audio_group, "blink_call.audio.enabled", self._update_blink_call_audio_visibility
        )

        self.blink_call_add_sequence_btn.clicked.connect(self.on_add_blink_call_step)
        self.blink_call_audio_preview_btn.clicked.connect(self.on_preview_blink_call_audio)
        self.blink_call_audio_volume_slider.valueChanged.connect(self._update_blink_call_audio_volume_text)
        self.model_files_btn.clicked.connect(lambda: self.model_files_manager.start_download_or_update(timeout_s=10.0))

        for idx, file_name in enumerate(self.blink_call_audio_file_values, start=1):
            self.blink_call_audio_file_combo.addItem(f"Audio {idx}", file_name)
        for duration_s in self.blink_call_audio_duration_values:
            self.blink_call_audio_duration_combo.addItem(str(duration_s), duration_s)

        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("Save settings")
        self.save_btn.setObjectName("settingSaveBtn")
        self.close_btn = QPushButton("Close")
        self.close_btn.setObjectName("settingCloseBtn")
        btn_row.addWidget(self.save_btn)
        btn_row.addWidget(self.close_btn)
        panel_layout.addLayout(btn_row)

        self.save_btn.clicked.connect(self.vm.save_config)
        self.close_btn.clicked.connect(self.vm.close)
        self.reset_config_btn.clicked.connect(self.on_restore_default_config)
        self.start_service_btn.clicked.connect(self.on_start_service)
        self.recording_start_btn.clicked.connect(self.vm.start_recording)
        self.recording_path_choose_btn.clicked.connect(self.on_choose_recording_dir)
        self.debug_log_path_choose_btn.clicked.connect(self.on_choose_debug_log_dir)
        self.vm.close_requested.connect(self.hide)
        self.model_files_manager.status_changed.connect(self.on_model_files_status_changed)
        self.model_files_manager.download_started.connect(self.on_model_files_download_started)
        self.model_files_manager.download_progress.connect(self.on_model_files_download_progress)
        self.model_files_manager.download_finished.connect(self.on_model_files_download_finished)

        self.on_switch_setting_page(0)
        self.refresh_from_local_config()

    def _create_nav_item(self, text: str):
        row = QWidget()
        row.setObjectName("settingNavRow")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(10, 10, 10, 10)
        row_layout.setSpacing(5)

        icon_slot = QLabel()
        icon_slot.setObjectName("settingNavIconSlot")
        icon_slot.setFixedSize(25, 25)
        icon_slot.setAlignment(Qt.AlignCenter)
        row_layout.addWidget(icon_slot)

        btn = QPushButton(text)
        btn.setObjectName("settingNavBtn")
        btn.setCheckable(True)
        btn.setFlat(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        row_layout.addWidget(btn)
        return row, btn, icon_slot

    def _attach_widgets(self, page_widgets):
        for key, value in vars(page_widgets).items():
            setattr(self, key, value)

    def on_switch_setting_page(self, page_index: int):
        self.content_stack.setCurrentIndex(page_index)
        for idx, row in enumerate(self.nav_rows):
            row.setProperty("active", idx == page_index)
            row.style().unpolish(row)
            row.style().polish(row)

        for idx, icon in enumerate(self.nav_icons):
            icon.setProperty("active", idx == page_index)
            icon.style().unpolish(icon)
            icon.style().polish(icon)

    def bind_radio_group(self, group, path, on_after_changed=None):
        def on_changed(btn):
            value = btn.property("tag_value")
            self.vm.set_config(path, value)
            if on_after_changed:
                on_after_changed(value)

        group.buttonClicked.connect(on_changed)

    def bind_line_edit(self, edit, path: str):
        def on_changed(text):
            self.vm.set_config(path, text)

        edit.textChanged.connect(on_changed)

    def bind_combo(self, combo, path: str):
        def on_changed():
            self.vm.set_config(path, combo.currentData())

        combo.currentIndexChanged.connect(on_changed)

    def bind_spinbox(self, spinbox, path: str):
        def on_changed(value: int):
            self.vm.set_config(path, int(value))

        spinbox.valueChanged.connect(on_changed)

    def bind_slider(self, slider, path: str):
        def on_changed(value: int):
            self.vm.set_config(path, int(value))

        slider.valueChanged.connect(on_changed)

    def refresh_from_local_config(self):
        language_idx = self.language_combo.findData(self.vm.get_config("ui.language"))
        self.language_combo.blockSignals(True)
        self.language_combo.setCurrentIndex(0 if language_idx < 0 else language_idx)
        self.language_combo.blockSignals(False)
        theme_idx = self.theme_combo.findData(self.vm.get_config("ui.theme"))
        self.theme_combo.blockSignals(True)
        self.theme_combo.setCurrentIndex(0 if theme_idx < 0 else theme_idx)
        self.theme_combo.blockSignals(False)

        if self.vm.get_config("camera.mode") == "remote":
            self.camera_remote_mode_radio.setChecked(True)
            self._update_camera_mode_visibility("remote")
        else:
            self.camera_local_mode_radio.setChecked(True)
            self._update_camera_mode_visibility("local")

        if bool(self.vm.get_config("debug_mode")):
            self.debug_mode_on_radio.setChecked(True)
        else:
            self.debug_mode_off_radio.setChecked(True)

        if bool(self.vm.get_config("debug_log.save_to_local")):
            self.debug_log_save_yes_radio.setChecked(True)
        else:
            self.debug_log_save_no_radio.setChecked(True)
        self.debug_log_path_value_label.setText(self.vm.get_config("debug_log.local_dir") or "")
        self._update_debug_logging_visibility()

        if bool(self.vm.get_config("blink_call.enabled")):
            self.blink_call_enabled_radio.setChecked(True)
        else:
            self.blink_call_disabled_radio.setChecked(True)

        if bool(self.vm.get_config("blink_call.show_home_progress_bar")):
            self.blink_call_progress_show_radio.setChecked(True)
        else:
            self.blink_call_progress_hide_radio.setChecked(True)

        if bool(self.vm.get_config("blink_call.audio.enabled")):
            self.blink_call_audio_enable_on_radio.setChecked(True)
        else:
            self.blink_call_audio_enable_off_radio.setChecked(True)

        audio_file_idx = self.blink_call_audio_file_combo.findData(self.vm.get_config("blink_call.audio.file"))
        self.blink_call_audio_file_combo.blockSignals(True)
        self.blink_call_audio_file_combo.setCurrentIndex(0 if audio_file_idx < 0 else audio_file_idx)
        self.blink_call_audio_file_combo.blockSignals(False)

        audio_duration_idx = self.blink_call_audio_duration_combo.findData(
            self.vm.get_config("blink_call.audio.play_duration_s")
        )
        self.blink_call_audio_duration_combo.blockSignals(True)
        self.blink_call_audio_duration_combo.setCurrentIndex(0 if audio_duration_idx < 0 else audio_duration_idx)
        self.blink_call_audio_duration_combo.blockSignals(False)

        audio_volume = int(self.vm.get_config("blink_call.audio.volume"))
        self.blink_call_audio_volume_slider.blockSignals(True)
        self.blink_call_audio_volume_slider.setValue(max(0, min(100, audio_volume)))
        self.blink_call_audio_volume_slider.blockSignals(False)
        self._update_blink_call_audio_volume_text(self.blink_call_audio_volume_slider.value())

        for row in self.blink_call_sequence_rows:
            row["widget"].deleteLater()
        self.blink_call_sequence_rows.clear()

        pattern = self._normalize_blink_call_pattern(self.vm.get_config("blink_call.pattern"))
        for item in pattern:
            self._add_blink_call_sequence_row(
                item["state"], float(item["duration_s"]), bool(item["sound_prompt"]), emit_change=False
            )

        self._update_blink_call_sequence_visibility()

        self.local_camera_id.setValue(int(self.vm.get_config("camera.local_camera_id") or 0))
        self.remote_ip.setText(self.vm.get_config("camera.remote.ip") or "")
        self.remote_port.setValue(int(self.vm.get_config("camera.remote.port") or 10000))

        self.service_camera_id.setValue(int(self.vm.get_config("local_service.camera_id") or 0))
        self.service_port.setValue(int(self.vm.get_config("local_service.port") or 10000))
        recording_max_duration_min = int(self.vm.get_config("recording.max_duration_min") or 1)
        self.recording_duration_spin.setValue(max(1, min(1440, recording_max_duration_min)))
        self.recording_path_value_label.setText(
            self.vm.get_config("recording.local_dir") or str(Path.home() / "Desktop")
        )

        self.model_files_manager.start_check_status(timeout_s=10.0)

        self._apply_language()

    def _apply_language(self):
        i18n = get_i18n(self.vm.get_config("ui.language"))

        self.title_label.setText(i18n["setting"])
        self.general_nav_btn.setText(i18n["general"])
        self.camera_nav_btn.setText(i18n["camera"])
        self.blink_call_nav_btn.setText(i18n["blink_call"])
        self.other_nav_btn.setText(i18n["other"])

        self.language_label.setText(i18n["language"])
        self.theme_label.setText(i18n["theme"])
        self.theme_combo.setItemText(0, i18n["light"])
        self.theme_combo.setItemText(1, i18n["dark"])

        self.choose_camera_source_label.setText(i18n["choose_camera_source"])
        self.camera_local_mode_radio.setText(i18n["local_camera"])
        self.camera_remote_mode_radio.setText(i18n["remote_camera"])
        self.local_camera_id_label.setText(i18n["camera_id"])
        self.remote_service_info_label.setText(i18n["remote_camera_service_info"])
        self.remote_ip_label.setText(i18n["ip"])
        self.remote_port_label.setText(i18n["port"])
        self.start_service_btn.setText(i18n["start_local_camera_service"])
        self.start_service_label.setText(i18n["start_local_camera_service"])
        self.service_section_label.setText(i18n["service_configuration_items"])
        self.service_camera_id_label.setText(i18n["camera_id"])
        self.service_port_label.setText(i18n["port"])

        self.blink_call_switch_label.setText(i18n["enable_blink_call"])
        self.blink_call_enabled_radio.setText(i18n["on"])
        self.blink_call_disabled_radio.setText(i18n["off"])
        self.blink_call_progress_label.setText(i18n["show_top_progress_bar_on_home_page"])
        self.blink_call_progress_show_radio.setText(i18n["show"])
        self.blink_call_progress_hide_radio.setText(i18n["hide"])
        self.blink_call_sequence_label.setText(i18n["blink_sequence"])
        self.blink_call_add_sequence_btn.setText(i18n["add_step"])
        self.blink_call_audio_enable_label.setText(i18n["play_call_audio"])
        self.blink_call_audio_enable_on_radio.setText(i18n["on"])
        self.blink_call_audio_enable_off_radio.setText(i18n["off"])
        self.blink_call_audio_file_label.setText(i18n["call_audio_file"])
        self.blink_call_audio_preview_btn.setText(i18n["preview"])
        self.blink_call_audio_volume_label.setText(i18n["audio_volume"])
        self.blink_call_audio_duration_label.setText(i18n["audio_play_duration"])
        self.model_files_label.setText(i18n["download_or_update_model_files"])
        self.model_files_desc_label.setText("")
        self.model_files_btn.setText(i18n["download_or_update"])

        for idx in range(len(self.blink_call_audio_file_values)):
            self.blink_call_audio_file_combo.setItemText(idx, f'{i18n["audio"]} {idx + 1}')

        duration_keys = [
            "ten_seconds",
            "thirty_seconds",
            "one_minute",
            "five_minutes",
            "ten_minutes",
            "thirty_minutes",
            "one_hour",
            "unlimited",
        ]
        for idx, key in enumerate(duration_keys):
            self.blink_call_audio_duration_combo.setItemText(idx, i18n[key])

        for row in self.blink_call_sequence_rows:
            row["state_combo"].setItemText(0, i18n["open_eyes"])
            row["state_combo"].setItemText(1, i18n["close_eyes"])
            row["duration_label"].setText(i18n["duration_seconds"])
            row["sound_prompt_label"].setText(i18n["sound_prompt"])
            row["sound_prompt_combo"].setItemText(0, i18n["no"])
            row["sound_prompt_combo"].setItemText(1, i18n["yes"])
            row["remove_btn"].setText(i18n["remove"])

        self.debug_mode_label.setText(i18n["debug_mode"])
        self.recording_label.setText(i18n["record_current_camera_data"])
        self.recording_start_btn.setText(i18n["start_recording"])
        self.recording_duration_label.setText(i18n["duration"])
        self.recording_duration_unit_label.setText(i18n["minute"])
        self.recording_path_label.setText(i18n["local_folder"])
        self.recording_path_choose_btn.setText(i18n["choose_folder"])
        self.debug_mode_on_radio.setText(i18n["on"])
        self.debug_mode_off_radio.setText(i18n["off"])
        self.debug_log_save_label.setText(i18n["save_to_local"])
        self.debug_log_save_yes_radio.setText(i18n["yes"])
        self.debug_log_save_no_radio.setText(i18n["no"])
        self.debug_log_path_label.setText(i18n["local_file_path"])
        self.debug_log_path_choose_btn.setText(i18n["choose_folder"])

        self.reset_config_btn.setText(i18n["restore_defaults"])
        self.reset_config_label.setText(i18n["restore_defaults"])

        self.save_btn.setText(i18n["save"])
        self.close_btn.setText(i18n["close"])

    def _normalize_blink_call_pattern(self, pattern):
        normalized = []
        for item in pattern if isinstance(pattern, list) else []:
            if not isinstance(item, dict):
                continue
            state = item.get("state")
            duration_s = item.get("duration_s")
            if state not in {"open", "closed"}:
                continue
            try:
                duration_s = float(duration_s)
            except (TypeError, ValueError):
                continue
            sound_prompt = item.get("sound_prompt")
            normalized.append({"state": state, "duration_s": duration_s, "sound_prompt": sound_prompt})

        return normalized

    def _add_blink_call_sequence_row(
        self, state: str = "open", duration_s: float = 1.0, sound_prompt: bool = True, emit_change: bool = True
    ):
        i18n = get_i18n(self.vm.get_config("ui.language"))

        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        state_combo = QComboBox()
        state_combo.addItem(i18n["open_eyes"], "open")
        state_combo.addItem(i18n["close_eyes"], "closed")
        idx = state_combo.findData(state)
        state_combo.setCurrentIndex(0 if idx < 0 else idx)
        state_combo.setFixedSize(100, 40)

        duration_label = QLabel(i18n["duration_seconds"])
        duration_label.setObjectName("settingSubSectionTitle")
        duration_spin = NoWheelSpinBox()
        duration_spin.setDecimals(1)
        duration_spin.setSingleStep(0.5)
        duration_spin.setRange(0.5, 5.0)
        duration_spin.setValue(min(5.0, max(0.5, duration_s)))
        duration_spin.setFixedSize(100, 40)

        sound_prompt_label = QLabel(i18n["sound_prompt"])
        sound_prompt_label.setObjectName("settingSubSectionTitle")
        sound_prompt_combo = QComboBox()
        sound_prompt_combo.addItem(i18n["no"], False)
        sound_prompt_combo.addItem(i18n["yes"], True)
        sound_prompt_idx = sound_prompt_combo.findData(bool(sound_prompt))
        sound_prompt_combo.setCurrentIndex(0 if sound_prompt_idx < 0 else sound_prompt_idx)
        sound_prompt_combo.setFixedSize(100, 40)

        remove_btn = QPushButton(i18n["remove"])
        remove_btn.setObjectName("settingNormalButton")
        remove_btn.setFixedSize(160, 30)

        row_layout.addWidget(state_combo)
        row_layout.addWidget(duration_label)
        row_layout.addWidget(duration_spin)
        row_layout.addWidget(sound_prompt_label)
        row_layout.addWidget(sound_prompt_combo)
        row_layout.addStretch()
        row_layout.addWidget(remove_btn)

        row = {
            "widget": row_widget,
            "state_combo": state_combo,
            "duration_label": duration_label,
            "duration_spin": duration_spin,
            "sound_prompt_label": sound_prompt_label,
            "sound_prompt_combo": sound_prompt_combo,
            "remove_btn": remove_btn,
        }
        self.blink_call_sequence_rows.append(row)
        self.blink_call_sequence_rows_layout.addWidget(row_widget)

        state_combo.currentIndexChanged.connect(self._save_blink_call_pattern)
        duration_spin.valueChanged.connect(self._save_blink_call_pattern)
        sound_prompt_combo.currentIndexChanged.connect(self._save_blink_call_pattern)
        remove_btn.clicked.connect(lambda: self._remove_blink_call_sequence_row(row_widget))

        self._refresh_blink_call_remove_buttons()
        if emit_change:
            self._save_blink_call_pattern()

    def _remove_blink_call_sequence_row(self, row_widget: QWidget):
        if len(self.blink_call_sequence_rows) <= 1:
            return

        remove_idx = -1
        for idx, row in enumerate(self.blink_call_sequence_rows):
            if row["widget"] is row_widget:
                remove_idx = idx
                break
        if remove_idx < 0:
            return

        row = self.blink_call_sequence_rows.pop(remove_idx)
        row["widget"].deleteLater()
        self._refresh_blink_call_remove_buttons()
        self._save_blink_call_pattern()

    def _refresh_blink_call_remove_buttons(self):
        enable_remove = len(self.blink_call_sequence_rows) > 1
        for row in self.blink_call_sequence_rows:
            row["remove_btn"].setVisible(enable_remove)
            row["remove_btn"].setEnabled(enable_remove)

    def _save_blink_call_pattern(self):
        sequence = []
        for row in self.blink_call_sequence_rows:
            sequence.append(
                {
                    "state": row["state_combo"].currentData(),
                    "duration_s": float(row["duration_spin"].value()),
                    "sound_prompt": bool(row["sound_prompt_combo"].currentData()),
                }
            )

        self.vm.set_config("blink_call.pattern", self._normalize_blink_call_pattern(sequence))

    def on_add_blink_call_step(self):
        self._add_blink_call_sequence_row("open", 1.0, True, emit_change=True)

    def on_start_service(self):
        self.vm.on_start_local_service()

    def on_choose_recording_dir(self):
        i18n = get_i18n(self.vm.get_config("ui.language"))
        current_dir = self.vm.get_config("recording.local_dir", source="temp") or str(Path.home() / "Desktop")
        dialog = QFileDialog(self, i18n["choose_recording_folder"], current_dir)
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
        self.recording_path_value_label.setText(selected)

    def on_restore_default_config(self):
        i18n = get_i18n(self.vm.get_config("ui.language"))
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setWindowTitle(i18n["restore_defaults"])
        msg.setText(i18n["are_you_sure_to_restore_default_settings"])
        confirm_btn = msg.addButton(i18n["confirm"], QMessageBox.ButtonRole.AcceptRole)
        msg.addButton(i18n["close"], QMessageBox.ButtonRole.RejectRole)
        msg.exec()
        if msg.clickedButton() == confirm_btn:
            self.vm.restore_default_config()

    def on_choose_debug_log_dir(self):
        i18n = get_i18n(self.vm.get_config("ui.language"))
        current_dir = self.vm.get_config("debug_log.local_dir", source="temp") or ""
        dialog = QFileDialog(self, i18n["choose_local_log_folder"], current_dir)
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
        self.debug_log_path_value_label.setText(selected)

    def on_preview_blink_call_audio(self):
        file_name = self.blink_call_audio_file_combo.currentData()
        if not isinstance(file_name, str) or not file_name.strip():
            return

        audio_path = Path("assets") / "audio" / file_name
        if not audio_path.exists():
            return

        self._preview_sound.stop()
        self._preview_sound.setSource(QUrl.fromLocalFile(str(audio_path.resolve())))
        self._preview_sound.setLoopCount(1)
        self._preview_sound.setVolume(float(self.blink_call_audio_volume_slider.value()) / 100.0)
        self._preview_sound.play()

    def on_model_files_status_changed(self, payload=None):
        i18n = get_i18n(self.vm.get_config("ui.language"))
        desc_text = f"{i18n.get(payload['desc_key'], '')} {payload['reason_detail']}"

        self.model_files_desc_label.setText(desc_text)
        self.model_files_btn.setEnabled(payload.get("button_enabled", False))

    def on_model_files_download_started(self):
        self.model_files_btn.setEnabled(False)
        i18n = get_i18n(self.vm.get_config("ui.language"))

        self.model_files_block_overlay.setGeometry(0, 0, self.width(), self.height())
        self.model_files_block_overlay.show_progress(i18n.get("downloading", ""), determinate=True)
        self.model_files_block_overlay.set_progress(0)
        self.model_files_block_overlay.show()
        self.model_files_block_overlay.raise_()

    def on_model_files_download_progress(self, progress: dict):
        value = int(max(0, min(100, progress.get("progress", 0))))
        filename = progress.get("filename", "")

        self.model_files_block_overlay.set_progress(value)
        if filename:
            i18n = get_i18n(self.vm.get_config("ui.language"))
            self.model_files_block_overlay.set_title(f'{i18n["downloading"]}\n{filename}')

    def on_model_files_download_finished(self, success: bool):
        self.model_files_block_overlay.hide()

        if success:
            self.save_btn.click()
        else:
            self.model_files_btn.setEnabled(True)

    def _update_blink_call_audio_volume_text(self, value: int):
        self.blink_call_audio_volume_value_label.setText(f"{int(value)}%")

    def _update_camera_mode_visibility(self, mode: str):
        is_local = mode != "remote"
        self.local_mode_widgets_row.setVisible(is_local)
        self.remote_mode_widgets_row.setVisible(not is_local)

    def _update_debug_logging_visibility(self, _value=None):
        is_debug_on = bool(self.debug_mode_on_radio.isChecked())
        is_save_local = bool(self.debug_log_save_yes_radio.isChecked())

        self.debug_log_save_widgets_row.setVisible(is_debug_on)
        self.debug_log_path_widgets_row.setVisible(is_debug_on and is_save_local)

    def _update_blink_call_sequence_visibility(self, _value=None):
        enabled = bool(self.blink_call_enabled_radio.isChecked())
        self.blink_call_progress_widgets_row.setVisible(enabled)
        self.blink_call_progress_divider_line.setVisible(enabled)
        self.blink_call_sequence_label.setVisible(enabled)
        self.blink_call_sequence_rows_host.setVisible(enabled)
        self.blink_call_add_sequence_btn.setVisible(enabled)
        self.blink_call_sequence_divider_line.setVisible(enabled)
        self.blink_call_audio_enable_widgets_row.setVisible(enabled)
        self.blink_call_audio_enable_divider_line.setVisible(enabled)
        self._update_blink_call_audio_visibility()

    def _update_blink_call_audio_visibility(self, _value=None):
        enabled = bool(self.blink_call_enabled_radio.isChecked())
        audio_enabled = bool(self.blink_call_audio_enable_on_radio.isChecked())
        show_audio_settings = enabled and audio_enabled
        self.blink_call_audio_file_widgets_row.setVisible(show_audio_settings)
        self.blink_call_audio_file_divider_line.setVisible(show_audio_settings)
        self.blink_call_audio_volume_widgets_row.setVisible(show_audio_settings)
        self.blink_call_audio_volume_divider_line.setVisible(show_audio_settings)
        self.blink_call_audio_duration_widgets_row.setVisible(show_audio_settings)
        self.blink_call_audio_duration_divider_line.setVisible(show_audio_settings)

    def showEvent(self, event):
        self.refresh_from_local_config()
        super().showEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.model_files_block_overlay.setGeometry(0, 0, self.width(), self.height())

    def hideEvent(self, event):
        self._preview_sound.stop()
        self.close_setting_popup.emit()
        super().hideEvent(event)
