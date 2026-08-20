"""Interface pública do backend web."""


def create_app(*args, **kwargs):
    """Importa a fábrica sob demanda para manter ``python -m src.web.app`` limpo."""
    from .app import create_app as factory

    return factory(*args, **kwargs)

__all__ = ['create_app']
