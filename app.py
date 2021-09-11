import argparse
import csv
import json
import logging
import logging.config
import os
import sys
from contextlib import contextmanager
from dataclasses import asdict, dataclass, fields
from tempfile import TemporaryDirectory
from textwrap import dedent
from typing import Dict, Generator, Iterable, List

import fsspec
import MeCab
import neologdn
from fsspec.implementations.local import LocalFileSystem

logger = logging.getLogger(__name__)


# see: https://unidic.ninjal.ac.jp/faq
FEATURES_UDIC = [
    "pos1",
    "pos2",
    "pos3",
    "pos4",
    "cType",
    "cForm",
    "lForm",
    "lemma",
    "orth",
    "pron",
    "orthBase",
    "pronBase",
    "goshu",
    "iType",
    "iForm",
    "fType",
    "fForm",
    "kana",
    "kanaBase",
    "form",
    "formBase",
    "iConType",
    "fConType",
    "aType",
    "aConType",
    "aModType",
]

# see: https://taku910.github.io/mecab/learn.html
FEATURES_IPADIC = [
    "pos",  # 品詞 (e.g. 動詞)
    "pos1",  # 品詞細分類1 (e.g. 自立)
    "pos2",  # 品詞細分類2
    "pos3",  # 品詞細分類3
    "cType",  # 活用型 (e.g. 命令ｅ)
    "cForm",  # 活用形 (e.g. 段・カ行イ音便)
    "orthBase",  # 基本形 (書字形基本形, e.g. こおりつく)
    "kana",  # 読み (仮名形出現形, e.g. コオリツケ)
    "pron",  # 発音 (発音出現系, e.g. コーリツケ)
]
FEATURES_USERDIC = [
    "f1",  # カスタム素性1
]
FEATURES = FEATURES_IPADIC + FEATURES_USERDIC


@dataclass
class Config:
    # the path to a mecabrc
    APP_RCFILE: str = "/dev/null"
    # the path to a system dictionary directory
    APP_DICDIR: str = "/opt/mecab-ipadic-neologd"
    # the path to an user dictionary
    APP_USERDIC: str = ""

    def make_arguments(self):
        """make args and kwargs for `ArgmentParser.add_argument()`"""
        return [
            (
                (f"--{name[4:].lower()}",),
                {
                    "type": str,
                    "default": value,
                    "required": value == "",
                },
            )
            for name, value in asdict(self).items()
        ]

    @classmethod
    def from_environ(cls, environ=os.environ):
        """load config from environment variables"""
        return cls(**{f.name: environ[f.name] for f in fields(cls) if f.name in environ})

    @classmethod
    def from_namespace(cls, namespace: argparse.Namespace):
        """load config from a Namespace object"""

        def _to_key(name: str):
            return name[4:].lower()

        dct = vars(namespace)
        return cls(**{f.name: dct[_to_key(f.name)] for f in fields(cls) if _to_key(f.name) in dct})


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


@contextmanager
def ensure_local(urlpath: str) -> Generator[str, None, None]:
    """ensure a file is on local within a with block"""
    with fsspec.open(urlpath, mode="rb") as of:
        # If the file is already on local, just yield its path
        if isinstance(of.fs, LocalFileSystem):
            yield urlpath

        # Otherwise, download the file into a tempdir, then yield its local path
        else:
            with TemporaryDirectory() as d:
                localpath = os.path.join(d, os.path.basename(urlpath))
                of.fs.download(of.path, localpath)
                yield localpath


def _configure_logging(log_level: str) -> None:
    """Configure the logging facility"""
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s %(levelname)-8s %(name)-15s %(message)s",
                    "datefmt": "%Y-%m-%dT%H:%M:%S",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "level": log_level,
                },
            },
            "root": {
                "handlers": ["console"],
                "level": "DEBUG",
            },
            "loggers": {},
        }
    )


def handler(event, context, config: Config = Config.from_environ()):
    logger.debug("event: %s", event)
    logger.debug("config: %s", config)

    with ensure_local(config.APP_USERDIC) as path:
        # configure a MeCab Tagger
        args = f"-r{config.APP_RCFILE} -d{config.APP_DICDIR} -u{path}"
        logger.debug("Tagger arguments: %s", args)
        tagger = MeCab.Tagger(args)

        # normalize and parse
        text = neologdn.normalize(event["body"])
        out = [
            dict(surface=node.surface, **parse_csv(node.feature, fieldnames=FEATURES))
            for node in parse_to_node(tagger, text)
        ]

    logger.debug("out: %s", out)
    response = {
        "statusCode": 200,
        "body": json.dumps(out, ensure_ascii=False, indent=2),
    }

    return response


def main(argv: List[str]) -> int:
    """The CLI entrypoint"""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=dedent(
            """\
            Invoke the function locally
            """
        ),
    )
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument(
        "--data",
        type=str,
        help="Input data",
        required=True,
    )
    parser.add_argument(
        "--output",
        type=str,
        choices=["raw", "json"],
        help="The formatting style for the command output",
        default="raw",
    )

    # add arguments from Config
    for args, kwargs in Config.from_environ().make_arguments():
        parser.add_argument(*args, **kwargs)

    # parse arguments and then set log level
    args = parser.parse_args(argv)
    _configure_logging(log_level=args.log_level)
    logger.debug("given option: %s", vars(args))

    # cal handler
    config = Config.from_namespace(args)
    response = handler(json.loads(args.data), None, config)

    # ouput
    if args.output == "raw":
        sys.stdout.write(str(response) + "\n")

    elif args.output == "json":
        sys.stdout.write(
            json.dumps(
                {
                    **response,
                    "body": json.loads(response["body"]),
                },
                sort_keys=True,
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        )

    return 0


if __name__ == "__main__":
    main(sys.argv[1:])
