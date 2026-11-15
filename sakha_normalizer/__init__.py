"""sakha_normalizer: живое якутское письмо → стандартная орфография (для машин, не для людей)."""
from .normalizer import Normalizer, normalize

__version__ = '0.1.1'
__all__ = ['Normalizer', 'normalize', '__version__']
