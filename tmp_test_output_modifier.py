import subprocess
import shlex
import sys
import select
from output_modifier import OutputModifier

sys.stdout = OutputModifier(sys.stdout, __file__)
sys.stderr = OutputModifier(sys.stderr, __file__)

command = "python write_to_stdout_and_stderr.py"
process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

assert process.stdout is not None
for line in process.stdout:
    print(line, end='')
