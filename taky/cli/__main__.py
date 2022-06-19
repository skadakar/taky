import sys
import argparse
import traceback
import configparser

from taky import __version__
from taky import cli
from taky.config import load_config


def arg_parse():
    argp = argparse.ArgumentParser(description="Taky command line utility")
    argp.add_argument(
        "-c",
        action="store",
        dest="cfg_file",
        default=None,
        help="Path to configuration file",
    )
    argp.add_argument(
        "--version", action="version", version="%%(prog)s version %s" % __version__
    )

    subp = argp.add_subparsers(dest="command")

    cli.setup_taky_reg(subp)
    cli.build_client_reg(subp)
    cli.systemd_reg(subp)
    cli.mgmt_reg(subp, "status", "Check the status of the taky server")
    cli.mgmt_reg(subp, "purge_persist", "Clear the persistence database")

    args = argp.parse_args()

    return (argp, args)


def main():
    (argp, args) = arg_parse()

    commands = {
        "setup": cli.setup_taky,
        "build_client": cli.build_client,
        "systemd": cli.systemd,
        "status": cli.mgmt_status,
        "purge_persist": cli.mgmt_purge_persist,
    }

    if not args.command:
        argp.print_usage()
        sys.exit(1)

    if args.command != "setup":
        try:
            load_config(args.cfg_file, explicit=True)
        except (OSError, configparser.ParsingError) as exc:
            print(exc, file=sys.stderr)
            sys.exit(1)

    try:
        ret = commands[args.command](args)
    except KeyboardInterrupt:
        # TODO: Teardown function?
        ret = 1
    except Exception as exc:  # pylint: disable=broad-except
        print(f"{args.command} failed: {str(exc)}", file=sys.stderr)
        print("Unhandled exception:", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        ret = 1

    sys.exit(ret)


if __name__ == "__main__":
    main()
