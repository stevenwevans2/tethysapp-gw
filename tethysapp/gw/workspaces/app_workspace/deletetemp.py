import sys
import shutil
import os

temp_dir=sys.argv[1]
print(temp_dir)
if temp_dir is not None:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
