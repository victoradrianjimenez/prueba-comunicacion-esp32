import getopt
import sys

from app.main import MainApp

if __name__ == "__main__":
    fake = False
    try:
        arguments, values = getopt.getopt(sys.argv[1:], "f", ["fake"])
        for currentArgument, currentValue in arguments:
            if currentArgument in ("-f", "--fake"):
                fake = True
    except (ValueError, getopt.error) as err:
        pass
    # run program
    res = MainApp.run(fake=fake)
    exit(res)
