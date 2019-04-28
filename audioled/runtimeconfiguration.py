import argparse


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
    parser.add_argument(
        '-A',
        '--audio_device_index',
        dest='audio_device_index',
        type=int,
        default=None,
        help='Audio device index to use')

    return parser
