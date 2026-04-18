#ugly af, but works for now
import os
import sys
parent_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)