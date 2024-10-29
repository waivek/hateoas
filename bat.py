import os
import sys
import textwrap
from waivek.reltools import pathjoin

def get_width():
    try:
        return os.get_terminal_size().columns
    except:
        return 80

def bat(path):
    path = path if os.path.isabs(path) else pathjoin(sys._getframe(1), path)
    with open(path, 'r') as f:
        contents = f.readlines()
    lines = contents

    max_line_number = len(lines)
    line_number_width = len(str(max_line_number))
    gutter_padding = 2  # Padding on each side of the line number

    # Calculate the total width of the output
    terminal_width = get_width()
    gutter_width = line_number_width + 2 * gutter_padding + 1  # +1 for the vertical bar
    content_width = terminal_width - gutter_width - 1  # -1 for the space after the vertical bar

    # ANSI escape codes for dimming and resetting
    dim = "\033[2m"
    reset = "\033[0m"
    bold = "\033[1m"

    # Print the header
    print(f"{dim}{'─' * (gutter_width - 1)}┬{'─' * (content_width + 1)}{reset}")
    print(f"{dim}{'':{gutter_width - 1}}│{reset} File: {bold}{path}{reset}")
    print(f"{dim}{'─' * (gutter_width - 1)}┼{'─' * (content_width + 1)}{reset}")

    # Print the file contents with line numbers and wrapping
    for i, line in enumerate(lines, start=1):
        line = line.rstrip('\n')
        wrapped_lines = textwrap.wrap(line, width=content_width)
        for j, wrapped_line in enumerate(wrapped_lines):
            if j == 0:
                print(f"{dim}{i:>{line_number_width + gutter_padding}}{' ' * gutter_padding}│{reset} {wrapped_line}")
            else:
                print(f"{dim}{'':{line_number_width + gutter_padding}}{' ' * gutter_padding}│{reset} {wrapped_line}")

    # Print the footer
    print(f"{dim}{'─' * (gutter_width - 1)}┴{'─' * (content_width + 1)}{reset}")

if __name__ == "__main__":
    bat(sys.argv[1])


# run.vim: vert term python % tmp/lorem_ipsum.txt
