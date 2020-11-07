import datetime
import time
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Union

import click

import motherlib.client
import motherlib.model
from m import __version__


def remove_if_in_target(tags: List[str], target: List[str]) -> List[str]:
    n = {}
    for tag in tags:
        n[tag] = True
    return [t for t in target if not n.get(t, False)]


def filter_and_prefix_with_base(tags: List[str]) -> List[str]:
    return tags


def print_records(records: List[motherlib.model.Record]) -> None:
    for r in records:
        print(f'{r.created.date()} {r.ref[:9]} {"/".join(r.tags)}')


@click.group(invoke_without_command=True)
@click.option('-h', '--host', type=str, default='http://localhost:8080')
@click.option('-n', '--namespace', type=str, default='')
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx: click.Context, host: str, namespace: str) -> None:
    if ctx.obj is None:
       ctx.obj = {}  # type=Dict[str, Any]
    ctx.obj['api'] = motherlib.client.APIClient(addr=os.getenv('M_HOST', host))
    ns_tags = os.getenv('M_NAMESPACE', namespace)
    ctx.obj['namespace'] = [] if ns_tags == '' else ns_tags.split('/')
    if ctx.invoked_subcommand is None:
        ctx.invoke(l)


@cli.command()
@click.argument('tags')
@click.argument('filepath')
@click.pass_obj
def u(ctx: Dict[str, Any], tags: str, filepath: str) -> None:
    api = ctx['api']
    namespace = ctx['namespace']
    t = remove_if_in_target(namespace, tags.split('/'))
    with Path(filepath).open() as f:
        print(api.put_latest(tags=namespace+t, content=f))


@cli.command()
@click.argument('tags')
@click.pass_obj
def e(ctx: Dict[str, Any], tags: str) -> None:
    api = ctx['api']
    namespace = ctx['namespace']
    t = remove_if_in_target(namespace, tags.split('/'))
    exists = True
    try:
        records = api.get_latest(tags=namespace+t)
    except motherlib.client.APIError as exc:
        if exc.kind != "Not found":
            raise
        exists = False
    if len(records) > 1:
        print_records(records)
        return
    previous = ''
    if exists:
        content = api.get_blob(records[0].ref)
        previous = content.read().decode()
    message = click.edit(previous)
    if message is None:
        print('Leaving content unchanged.')
        return
    print(api.put_latest(tags=namespace+t, content=str.encode(message)))


@cli.command()
@click.argument('tags', default='')
@click.pass_obj
def l(ctx: Dict[str, Any], tags: str) -> None:
    api = ctx['api']
    namespace = ctx['namespace']
    t = remove_if_in_target(namespace, tags.split('/'))
    print_records(api.get_latest(tags=namespace+t))


@cli.command()
@click.argument('tags', default='')
@click.pass_obj
def s(ctx: Dict[str, Any], tags: str) -> None:
    api = ctx['api']
    namespace = ctx['namespace']
    t = remove_if_in_target(namespace, tags.split('/'))
    records = api.get_latest(tags=namespace+t)
    if len(records) == 1:
        print(api.get_blob(records[0].ref).read())
    else:
        print_records(records)


@cli.command()
@click.argument('tags', default='')
@click.pass_obj
def h(ctx: Dict[str, Any], tags: str) -> None:
    api = ctx['api']
    namespace = ctx['namespace']
    t = remove_if_in_target(namespace, tags.split('/'))
    print_records(api.get_history(tags=namespace+t))


@cli.command()
@click.argument('tags')
@click.pass_obj
def d(ctx: Dict[str, Any], tags: str) -> None:
    api = ctx['api']
    namespace = ctx['namespace']
    t = remove_if_in_target(namespace, tags.split('/'))
    api.delete_history(tags=namespace+t)


@cli.command()
@click.argument('src', required=True)
@click.argument('dst', required=True)
@click.pass_obj
def mv(ctx: Dict[str, Any], src: str, dst: str) -> None:
    api = ctx['api']
    namespace = ctx['namespace']

    src_tags = remove_if_in_target(namespace, src.split('/'))
    dst_tags = remove_if_in_target(namespace, dst.split('/'))

    if set(src_tags) == set(dst_tags):
        print('Cannot mv: source is equal to destination.')
        return

    if set(src_tags) <= set(dst_tags):
        print('Cannot mv: source is a subset of destination.')
        return

    if set(dst_tags) <= set(src_tags):
        print('Cannot mv: destination is a subset of source.')
        return

    records = api.get_history(tags=namespace+src_tags)

    for r in reversed(records):
        content = api.get_blob(ref=r.ref).read()

        t = namespace + dst_tags + r.tags

        digest = api.put_latest(tags=t, content=content)

        print(digest)

        api.delete_history(tags=namespace+src_tags)


if __name__ == '__main__':
    try:
        cli()
    except motherlib.client.ConnectionError:
        print(f'ConnectionError: cannot connect to server.')
    except motherlib.client.APIError as exc:
        print(exc.err)
        print(exc.kind)
