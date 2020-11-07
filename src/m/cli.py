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
@click.argument('tags', default='')
@click.option('-h', '--host', type=str, default='http://localhost:8080')
@click.option('-n', '--namespace', type=str, default='')
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx: click.Context, tags: str, host: str, namespace: str) -> None:
    if ctx.obj is None:
       ctx.obj = {}  # type=Dict[str, Any]
    ctx.obj['api'] = motherlib.client.APIClient(addr=os.getenv('M_HOST', host))
    ns_tags = os.getenv('M_NAMESPACE', namespace)
    ctx.obj['namespace'] = [] if ns_tags == '' else ns_tags.split('/')
    if ctx.invoked_subcommand is None:
        api = ctx.obj['api']
        ns = ctx.obj['namespace']
        if len(tags) > 0 and tags[-1] == '/':
            t = remove_if_in_target(ns, tags[:-1].split('/'))
            result = api.get_superset_latest(tags=ns+t)
        else:
            t = remove_if_in_target(ns, tags.split('/'))
            result = api.get_latest(tags=ns+t)
        if result.content is not None:
            print(result.content.read())
            return
        print_records(result.records)


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
        result = api.get_latest(tags=namespace+t)
    except motherlib.client.APIError as exc:
        if exc.kind != "Not found":
            raise
        exists = False
    previous = ''
    if exists:
        previous = result.content.read().decode()
    message = click.edit(previous)
    if message is None:
        print('Aborting: empty content.')
        return
    print(api.put_latest(tags=namespace+t, content=str.encode(message)))


@cli.command()
@click.argument('tags', default='')
@click.pass_obj
def h(ctx: Dict[str, Any], tags: str) -> None:
    api = ctx['api']
    namespace = ctx['namespace']
    if len(tags) > 0 and tags[-1] == '/':
        t = remove_if_in_target(namespace, tags[:-1].split('/'))
        records = api.get_superset_history(tags=namespace+t)
    else:
        t = remove_if_in_target(namespace, tags.split('/'))
        records = api.get_history(tags=namespace+t)
    print_records(records)


@cli.command()
@click.argument('tags')
@click.pass_obj
def d(ctx: Dict[str, Any], tags: str) -> None:
    api = ctx['api']
    namespace = ctx['namespace']
    if len(tags) > 0 and tags[-1] == '/':
        t = remove_if_in_target(namespace, tags[:-1].split('/'))
        api.delete_superset_history(tags=namespace+t)
    else:
        t = remove_if_in_target(namespace, tags.split('/'))
        api.delete_history(tags=namespace+t)


@cli.command()
@click.argument('src', required=True)
@click.argument('dst', required=True)
@click.pass_obj
def mv(ctx: Dict[str, Any], src: str, dst: str) -> None:
    api = ctx['api']
    namespace = ctx['namespace']

    superset_src = src[-1] == '/'
    superset_dst = dst[-1] == '/'

    src_tags = remove_if_in_target(namespace, src.split('/'))
    if superset_src:
        src_tags = remove_if_in_target(namespace, src[:-1].split('/'))

    dst_tags = remove_if_in_target(namespace, dst.split('/'))
    if superset_dst:
        dst_tags = remove_if_in_target(namespace, dst[:-1].split('/'))

    if superset_src or not superset_dst:
        if src_tags == dst_tags:
            print('Cannot mv: source is equal to destination.')
            return

    if not superset_src and superset_dst:
        if src_tags <= dst_tags:
            print('Cannot mv: source is a subset of destination.')
            return
        if dst_tags <= src_tags:
            print('Cannot mv: destination is a subset of source.')
            return

    if superset_src:
        records = api.get_superset_history(tags=namespace+src_tags)
    else:
        records = api.get_history(tags=namespace+src_tags)

    for r in reversed(records):
        content = api.get_blob(ref=r.ref)

        moved_tags = r.tags[len(namespace):]

        if superset_src or not superset_dst:
            moved_tags = moved_tags[len(src_tags):]

        dst_tags = dst_tags + moved_tags

        print(api.put_latest(tags=namespace+dst_tags, content=content))

        if superset_src:
            api.delete_superset_history(tags=namespace+src_tags)
        else:
            api.delete_history(tags=namespace+src_tags)


if __name__ == '__main__':
    try:
        cli()
    except motherlib.client.ConnectionError:
        print(f'ConnectionError: cannot connect to server.')
    except motherlib.client.APIError as exc:
        print(exc.err)
        print(exc.kind)
