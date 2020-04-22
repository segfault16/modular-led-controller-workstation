import argparse
from audioled import serverconfiguration


def commonRuntimeArgumentParser():
    parser = argparse.ArgumentParser(description='MOLECOLE - A Modular LED Controller Workstation')

    parser.add_argument(
        '-N',
        '--num_pixels',
        dest='num_pixels',
        type=int,
        default=300,
        help='number of pixels (default: 300)',
    )
    parser.add_argument(
        '-R',
        '--num_rows',
        dest='num_rows',
        type=int,
        default=1,
        help='number of rows (default: 1)',
    )
    parser.add_argument(
        '--device_candy_server',
        '-DCS',
        dest='device_candy_server',
        default='localhost:7890',
        help='Server for device FadeCandy (default: localhost:7890)',
    )
    parser.add_argument(
        '--device_panel_mapping',
        dest='device_panel_mapping',
        default=None,
        help='Mapping file for panels',
    )
    parser.add_argument('-A',
                        '--audio_device_index',
                        dest='audio_device_index',
                        type=int,
                        default=None,
                        help='Audio device index to use')

    return parser


def addServerRuntimeArguments(parser: argparse.ArgumentParser):
    # Add server specific arguments
    parser.add_argument(
        '-p',
        '--port',
        dest='port',
        default='5000',
        help='Port to listen on',
    )
    parser.add_argument('-C',
                        '--config_location',
                        dest='config_location',
                        default=None,
                        help='Location of the server configuration to store. Defaults to $HOME/.ledserver.')
    parser.add_argument(
        '--no_conf',
        dest='no_conf',
        action='store_true',
        default=False,
        help="Don't load config from file",
    )
    parser.add_argument(
        '--no_store',
        dest='no_store',
        action='store_true',
        default=False,
        help="Don't save anything to disk",
    )
    # deviceChoices = serverconfiguration.ServerConfiguration.getConfigurationParameters().get('device')
    deviceChoices = serverconfiguration.allowed_devices
    parser.add_argument('-D',
                        '--device',
                        dest='device',
                        default=None,
                        choices=deviceChoices,
                        help='device to send RGB to (default: FadeCandy)')
    parser.add_argument('-DC',
                        '--device_config',
                        dest='device_config',
                        default=None,
                        help='Device config to use. Default: last active')
    parser.add_argument('-P',
                        '--process_timing',
                        dest='process_timing',
                        action='store_true',
                        default=False,
                        help='Print process timing')
    parser.add_argument(
        '--strand',
        dest='strand',
        action='store_true',
        default=False,
        help="Perform strand test at start of server.",
    )