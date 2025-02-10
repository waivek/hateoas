import sys
from output_modifier import OutputModifier

def main():
    unmodified_stdout = sys.stdout
    sys.stdout = OutputModifier(sys.stdout)
    sys.stderr = OutputModifier(sys.stderr)
    1/0

if __name__ == "__main__":
    main()
# run.vim: term python %
