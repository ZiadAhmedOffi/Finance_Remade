from django.apps import AppConfig


class FundsConfig(AppConfig):
    name = 'funds'

    def ready(self):
        import funds.signals
