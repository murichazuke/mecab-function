import argparse
import csv
import json
import logging
import logging.config
from textwrap import dedent
from typing import Dict, Iterable, List

import MeCab


logger = logging.getLogger(__name__)


FEATURES = [
    'pos1',
    'pos2',
    'pos3',
    'pos4',
    'cType',
    'cForm',
    'lForm',
    'lemma',
    'orth',
    'pron',
    'orthBase',
    'pronBase',
    'goshu',
    'iType',
    'iForm',
    'fType',
    'fForm',
    'kana',
    'kanaBase',
    'form',
    'formBase',
    'iConType',
    'fConType',
    'aType',
    'aConType',
    'aModType',
]


def parse_csv(line: str, *args, **kwargs) -> Dict[str, str]:
    """parse a single line CSV into a dict"""
    return next(csv.DictReader([line], *args, **kwargs))


def parse_to_node(tagger: MeCab.Tagger, text: str) -> Iterable[MeCab.Node]:
    """Iterate over parsed nodes"""
    node = tagger.parseToNode(text)
    node = node.next  # omit BOS
    while node:
        if node.next:  # omit EOS
            yield node
        node = node.next


def _configure_logging(log_level: str) -> None:
    """Configure the logging facility"""
    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'default': {
                'format': '%(asctime)s %(levelname)-8s %(name)-15s %(message)s',
                'datefmt': '%Y-%m-%dT%H:%M:%S',
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'default',
                'level': log_level,
            },
        },
        'root': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'loggers': {},
    })


def handler(event, context):
    text = event["body"]
    logger.debug('text: %s', text)

    tagger = MeCab.Tagger()
    out = [
        dict(
            surface=node.surface,
            **parse_csv(node.feature, fieldnames=FEATURES)
        )
        for node in parse_to_node(tagger, text)
    ]
    logger.debug('out: %s', out)

    response = {
        "statusCode": 200,
        "body": json.dumps(out, ensure_ascii=False, indent=2),
    }

    return response


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=dedent(
            """\
            Invoke the function locally
            """
        ),
    )
    parser.add_argument('--log-level', default='INFO')
    parser.add_argument(
        '--data',
        type=str,
        help='Input data',
    )

    # main
    args = parser.parse_args(argv)
    _configure_logging(log_level=args.log_level)
    logger.debug('given option: %s', vars(args))
    response = handler(json.loads(args.data), None)
    logger.info('response: %s', response)
    return 0


if __name__ == "__main__":
    import sys
    main(sys.argv[1:])
