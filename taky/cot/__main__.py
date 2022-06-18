# pylint: disable=missing-module-docstring
import os
import sys
import signal
import logging
import argparse
import configparser
import pdb, bdb
from datetime import datetime as dt
import traceback

from taky import __version__
from taky.cot import COTServer
from taky.config import load_config, app_config


class SigHdlr:
    def __init__(self, debug=False):
        self.got_sigterm = False
        self.debug = debug

        signal.signal(signal.SIGTERM, self.handle_term)
        signal.signal(signal.SIGUSR1, self.handle_pdb)

    def handle_term(self, sig, frame):  # pylint: disable=unused-argument
        """ Signal handler """
        logging.info("Got %s", signal.Signals(sig).name)
        self.got_sigterm = True

    def handle_pdb(self, sig, frame):  # pylint: disable=unused-argument
        """ Signal handler """
        if self.debug:
            logging.info("Dropping into PDB shell...")
            pdb.Pdb().set_trace(frame)


def log_crash(trace):
    # Log Crash
    if not os.path.exists(app_config.get("taky", "root_dir")):
        return

    crash_file = os.path.join(app_config.get("taky", "root_dir"), "crash.log")

    try:
        with open(crash_file, "a", encoding="utf8") as fp:
            fp.write("-" * 60 + "\n")
            fp.write(f"Version: {__version__}\n")
            fp.write(f"Date: {dt.utcnow().isoformat()}\n")
            fp.write(trace)
            fp.write("-" * 60 + "\n")
    except OSError as exc:
        logging.error("Unable to log crash dump: %s", exc)


def arg_parse():
    """ Handle arguments """
    argp = argparse.ArgumentParser(description="Start the taky server")
    argp.add_argument(
        "-l",
        action="store",
        dest="log_level",
        default="info",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Log verbosity",
    )
    argp.add_argument(
        "-c",
        action="store",
        dest="cfg_file",
        default=None,
        help="Path to configuration file",
    )
    argp.add_argument(
        "-d",
        action="store_true",
        dest="debug",
        default=False,
        help="Allow attaching to PDB",
    )
    argp.add_argument(
        "--version", action="version", version="%%(prog)s version %s" % __version__
    )

    args = argp.parse_args()

    return (argp, args)


def main():
    """ taky COT server """
    ret = 0

    (argp, args) = arg_parse()
    logging.basicConfig(level=args.log_level.upper(), stream=sys.stderr)
    logging.info("taky v%s", __version__)

    try:
        load_config(args.cfg_file)
    except (FileNotFoundError, OSError):
        if args.cfg_file:
            argp.error(f"Unable to load config file: '{args.cfg_file}'")
        else:
            argp.error("Unable to load './taky.conf' or '/etc/taky.conf'")
    except configparser.ParsingError as exc:
        argp.error(f"Configuration file error: {str(exc)}")

    # TODO: Check for ipv6 support
    gst = SigHdlr(args.debug)

    cot_srv = COTServer()
    try:
        cot_srv.sock_setup()
    except Exception as exc:  # pylint: disable=broad-except
        logging.error("Unable to start COTServer: %s", exc)
        logging.debug("", exc_info=exc)
        cot_srv.shutdown()
        sys.exit(1)

    try:
        while not gst.got_sigterm:
            try:
                cot_srv.loop()
            except bdb.BdbQuit:
                logging.info("Continuing from PDB shell")
    except KeyboardInterrupt:
        pass
    except Exception as exc:  # pylint: disable=broad-except
        logging.critical("Unhandled exception", exc_info=exc)
        ret = 1

        log_crash(traceback.format_exc())

    try:
        cot_srv.shutdown()
    except Exception as exc:  # pylint: disable=broad-except
        logging.critical("Exception during shutdown", exc_info=exc)
        ret = 1

    sys.exit(ret)


if __name__ == "__main__":
    main()
