class SettingModel:
    def __init__(self):
        self.camera_mode = "local"
        self.local_camera_id = 0
        self.remote_ip = ""
        self.remote_port = 10000

    def set_camera_config(self, mode, local_camera_id, remote_ip, remote_port):
        self.camera_mode = mode
        self.local_camera_id = local_camera_id
        self.remote_ip = remote_ip
        self.remote_port = remote_port
