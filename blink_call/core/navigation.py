class Navigation:
    def __init__(self, main_window):
        self.main_window = main_window

    def to(self, page_name):
        self.main_window.navigate(page_name)
