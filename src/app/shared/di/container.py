from dependency_injector import containers, providers

from app.core.config import Settings, get_settings


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(packages=["app.presentation.api"])

    settings: providers.Singleton[Settings] = providers.Singleton(get_settings)
