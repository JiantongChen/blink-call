class SettingModel:
    def __init__(self):
        self.language = "zh"
        self.camera_mode = "local"
        self.local_camera_id = 0
        self.remote_ip = ""
        self.remote_port = 10000
        self.service_camera_id = 0
        self.service_port = 10000

    def set_language(self, language):
        self.language = language

    def set_camera_config(self, mode, local_camera_id, remote_ip, remote_port):
        self.camera_mode = mode
        self.local_camera_id = local_camera_id
        self.remote_ip = remote_ip
        self.remote_port = remote_port

    def set_service_config(self, camera_id, port):
        self.service_camera_id = camera_id
        self.service_port = port
