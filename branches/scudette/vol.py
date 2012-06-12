#!/usr/bin/python

# Volatility
# Copyright (C) 2008 Volatile Systems
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or (at
# your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

__author__ = "Michael Cohen <scudette@gmail.com>"

import argparse
import logging
import sys


from volatility import session

# Import and register the core plugins
from volatility import plugins

parser =  argparse.ArgumentParser(description='The Volatility Memory Forensic Framework.',
                                  epilog='When no module is provided, '
                                  'drops into interactive mode')

parser.add_argument("module", nargs='?',
                    help="plugin module to run.")

parser.add_argument("-e", "--exec", default=None,
                    help="execute a python volatility script.")

# The following are added for backwards compatibility to the most common
# volatility command line options. This is not an exhaustive list (particularly
# since in Volatility 2.X further options can be added to each plugin).

parser.add_argument("-i", "--interactive", default=False, action="store_true",
                    help="For compatibility, if a plugin name is specified on the "
                    "command line, we exit immediately after running it. If this flag "
                    "is specified we drop into the interactive shell instead.")

parser.add_argument("-f", "--filename", default=None,
                    help="The raw image to load.")

parser.add_argument("-p", "--profile", default=None,
                    help="Name of the profile to load.")

parser.add_argument("--dtb", help="DTB Address.")
parser.add_argument("--pid", help="A process PID.", type=int)
parser.add_argument("--dump-dir", help="The directory to dump files to.")


def IPython011Support(user_session):
    """Launch the ipython session for pre 0.12 versions.

    Returns:
      False if we failed to use IPython. True if the session was run and exited.
    """
    banner = "Welcome to volshell! \nTo get help, type 'help()'"

    try:
        # Try to use the ipython shell
        from IPython import genutils
        from IPython import Shell

        # Fix a bug in IPython which prevents a custom __dir__ handler by
        # polluting it with additional crap.
        genutils.dir2 = dir

        shell = Shell.IPShellEmbed(argv=[], user_ns=user_session._locals, banner=banner)

        # This must be run here because the IPython shell messes with our user
        # namespace above (by adding its own help function).
        user_session._prepare_local_namespace()

        shell(local_ns=user_session._locals)
        return True

    except ImportError:
        return False


def IPython012Support(user_session):
    """Launch the ipython session for post 0.12 versions.

    Returns:
      False if we failed to use IPython. True if the session was run and exited.
    """
    banner = "Welcome to volshell! \nTo get help, type 'help()'"

    try:
        # Try to use the ipython shell
        from IPython.frontend.terminal.embed import InteractiveShellEmbed
        from IPython.config.loader import Config

        # This should bring back the old autocall behaviour. e.g.:
        # In [1]: vol plugins.pslist
        cfg = Config()
        cfg.InteractiveShellEmbed.autocall = 2

        shell = InteractiveShellEmbed(config=cfg, user_ns=user_session._locals,
                                      banner2=banner)

        # This must be run here because the IPython shell messes with our user
        # namespace above (by adding its own help function).
        user_session._prepare_local_namespace()

        shell(local_ns=user_session._locals)
        return True

    except ImportError:
        return False


def NativePythonSupport(user_session):
    """Launch the volatility session using the native python interpreter.

    Returns:
      False if we failed to use IPython. True if the session was run and exited.
    """
    # If the ipython shell is not available, we can use the native python shell.
    import code, inspect

    banner = "Welcome to volshell! \nTo get help, type 'help()'"

    # Try to enable tab completion
    try:
        import rlcompleter, readline #pylint: disable-msg=W0612
        readline.parse_and_bind("tab: complete")
    except ImportError:
        pass

    # Prepare the session for running within the native python interpreter.
    user_session._prepare_local_namespace()
    code.interact(banner = banner, local = user_session._locals)

def UpdateSessionFromArgv(user_session, FLAGS):
    for k, v in FLAGS.__dict__.items():
        if v is not None:
            setattr(user_session, k.replace("-", "_"), v)

if __name__ == '__main__':
    FLAGS = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    # New user session.
    user_session = session.Session()

    UpdateSessionFromArgv(user_session, FLAGS)
    if FLAGS.module:
        # Run the module
        user_session.vol(FLAGS.module)

        if not FLAGS.interactive:
            sys.exit()

    # Try to launch the session using something.
    IPython011Support(user_session) or IPython012Support(user_session) or NativePythonSupport(user_session)