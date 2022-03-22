# Showing how NOT to do it: "import *" is not the way to write a secure backing module.
# For anything public-facing, each symbol should be carefully reviewed before adding it to __all__.
import math
from math import *
__all__ = [d for d in dir(math) if not d.startswith('_')]
