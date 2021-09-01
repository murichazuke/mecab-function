import argparse
import csv
import json
import sys
import logging
import logging.config
from textwrap import dedent
from typing import Dict, Iterable, List

import MeCab


logger = logging.getLogger(__name__)


# see: https://unidic.ninjal.ac.jp/faq
FEATURES_UDIC = [
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

# see: https://taku910.github.io/mecab/learn.html
FEATURES_IPADIC = [
    'pos',  # 品詞 (e.g. 動詞)
    'pos1',  # 品詞細分類1 (e.g. 自立)
    'pos2',  # 品詞細分類2
    'pos3',  # 品詞細分類3
    'cType',  # 活用型 (e.g. 命令ｅ)
    'cForm',  # 活用形 (e.g. 段・カ行イ音便)
    'orthBase',  # 基本形 (書字形基本形, e.g. こおりつく)
    'kana',  # 読み (仮名形出現形, e.g. コオリツケ)
    'pron',  # 発音 (発音出現系, e.g. コーリツケ)
]
FEATURES = FEATURES_IPADIC


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

    tagger = MeCab.Tagger('-d /opt/mecab-ipadic-neologd')
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
        required=True,
    )
    parser.add_argument(
        '--output',
        type=str,
        choices=['raw', 'json'],
        help='The formatting style for the command output',
        default='raw',
    )

    # parse arguments and then set log level
    args = parser.parse_args(argv)
    _configure_logging(log_level=args.log_level)
    logger.debug('given option: %s', vars(args))

    # cal handler
    response = handler(json.loads(args.data), None)

    # ouput
    if args.output == 'raw':
        sys.stdout.write(str(response) + '\n')

    elif args.output == 'json':
        sys.stdout.write(
            json.dumps({
                **response,
                'body': json.loads(response['body']),
            }, sort_keys=True, ensure_ascii=False, indent=2) + '\n'
        )

    return 0


if __name__ == "__main__":
    main(sys.argv[1:])
