#!/usr/bin/env python3
#
# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import logging
from typing import List, Optional

import click
from fissix.pytree import Leaf, Node, type_repr

from .types import LN, SYMBOL, Capture, Filename

log = logging.getLogger(__name__)


def print_tree(
    node: LN,
    results: Capture = None,
    filename: Filename = None,
    indent: int = 0,
    recurse: int = -1,
):
    filename = filename or Filename("")
    tab = ".  " * indent
    if filename and indent == 0:
        click.secho(filename, fg="red", bold=True)

    if isinstance(node, Leaf):
        click.echo(
            click.style(tab, fg="black", bold=True)
            + click.style(
                f'[{type_repr(node.type)}] "{node.prefix}" "{node.value}"', fg="yellow"
            )
        )
    else:
        click.echo(
            click.style(tab, fg="black", bold=True)
            + click.style(f'[{type_repr(node.type)}] "{node.prefix}"', fg="blue")
        )

    if node.children:
        if recurse:
            for child in node.children:
                print_tree(child, indent=indent + 1, recurse=recurse - 1)
        else:
            click.echo(tab + "...")

    if results is None:
        return

    for key in results:
        if key == "node":
            continue

        value = results[key]
        if isinstance(value, (Leaf, Node)):
            click.secho(f'results["{key}"] =', fg="red")
            print_tree(value, indent=1, recurse=1)
        else:
            click.secho(f'results["{key}"] = {value}', fg="red")


def dotted_parts(name: str) -> List[str]:
    pre, dot, post = name.partition(".")
    if post:
        post_parts = dotted_parts(post)
    else:
        post_parts = []
    result = []
    if pre:
        result.append(pre)
    if pre and dot:
        result.append(dot)
    if post_parts:
        result.extend(post_parts)
    return result


def quoted_parts(name: str) -> List[str]:
    return [f"'{part}'" for part in dotted_parts(name)]


def power_parts(name: str) -> List[str]:
    parts = quoted_parts(name)
    index = 0
    while index < len(parts):
        if parts[index] == "'.'":
            parts.insert(index, "trailer<")
            parts.insert(index + 3, ">")
            index += 1
        index += 1
    return parts


def is_method(node: LN) -> bool:
    return (
        node.type == SYMBOL.funcdef
        and node.parent is not None
        and node.parent.type == SYMBOL.suite
        and node.parent.parent is not None
        and node.parent.parent.type == SYMBOL.classdef
    )


def find_first(node: LN, target: int, recursive: bool = False) -> Optional[LN]:
    queue: List[LN] = [node]
    queue.extend(node.children)
    while queue:
        child = queue.pop(0)
        if child.type == target:
            return child
        if recursive:
            queue = child.children + queue
    return None


def find_previous(node: LN, target: int, recursive: bool = False) -> Optional[LN]:
    while node.prev_sibling is not None:
        node = node.prev_sibling
        result = find_last(node, target, recursive)
        if result:
            return result
    return None


def find_next(node: LN, target: int, recursive: bool = False) -> Optional[LN]:
    while node.next_sibling is not None:
        node = node.next_sibling
        result = find_first(node, target, recursive)
        if result:
            return result
    return None


def find_last(node: LN, target: int, recursive: bool = False) -> Optional[LN]:
    queue: List[LN] = []
    queue.extend(reversed(node.children))
    while queue:
        child = queue.pop(0)
        if recursive:
            result = find_last(child, target, recursive)
            if result:
                return result
        if child.type == target:
            return child
    return None


def get_class(node: LN) -> LN:
    while node.parent is not None:
        if node.type == SYMBOL.classdef:
            return node
        node = node.parent
    raise ValueError(f"classdef node not found")


class Once:
    """Simple object that evaluates to True once, and then always False."""

    def __init__(self) -> None:
        self.done = False

    def __bool__(self) -> bool:
        if self.done:
            return False
        else:
            self.done = True
            return True
