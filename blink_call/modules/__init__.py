from blink_call.modules.home import HomeModel, HomeView, HomeViewModel

MODULES_REGISTRY = {
    "home": {
        "model": HomeModel,
        "vm": HomeViewModel,
        "view": HomeView,
    }
}
