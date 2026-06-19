from django.apps import AppConfig


class TrackerConfig(AppConfig):
    name = "tracker"

    def ready(self):
        import tracker.signals # Import the signals module to ensure signal handlers are registered

