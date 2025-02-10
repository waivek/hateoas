from loguru import logger
import sys

# Remove the default handler
logger.remove()

# Add a handler to redirect stdout
logger.add(sys.stdout, format="{time} {level} {message}")


# Now both print and logger will use the same Loguru formatting
print("This is a print statement.")

