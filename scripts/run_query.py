#!/usr/bin/env python3
"""Interactive or single-shot Q&A against the knowledge base."""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.retrieval.generator import AnswerGenerator
from src.utils.logger import logger


def print_result(result) -> None:
    print("\n" + "=" * 60)
    print(f"复杂度: {result.complexity}")
    print(f"子查询 ({len(result.queries)}): {result.queries}")
    print("-" * 60)
    print(result.answer)
    print("-" * 60)
    print("引用来源:")
    for src in result.sources:
        print(f"  [{src['index']}] {src['title_path']} — {src['file_path']} (p.{src['page']})")
    print("=" * 60 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Query FusionRAG knowledge base")
    parser.add_argument("question", nargs="?", help="Question to ask")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    args = parser.parse_args()

    generator = AnswerGenerator()

    if args.interactive:
        print("FusionRAG 交互式问答 (输入 quit 退出)")
        while True:
            try:
                q = input("\n问题> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not q or q.lower() in ("quit", "exit", "q"):
                break
            result = generator.generate(q)
            print_result(result)
    elif args.question:
        result = generator.generate(args.question)
        print_result(result)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
