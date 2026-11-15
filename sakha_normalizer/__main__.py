"""python -m sakha_normalizer "текст"   или   echo "текст" | python -m sakha_normalizer"""
import sys
from . import Normalizer

n = Normalizer()
if len(sys.argv) > 1:
    print(n.normalize(' '.join(sys.argv[1:])))
else:
    for line in sys.stdin:
        sys.stdout.write(n.normalize(line))
