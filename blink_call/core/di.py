class DIContainer:
    def __init__(self):
        self._services = {}

    def register(self, name, instance):
        self._services[name] = instance

    def get(self, name):
        return self._services[name]


# Global DI
DI = DIContainer()
