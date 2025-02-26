from docopt import docopt

from . import main, __doc__

options = docopt(__doc__)  # , options_first=True)

# print(f'hello:  {options}')
print("options: ", options)
main(options)
