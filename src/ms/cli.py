import datetime
import time
import os
from pathlib import Path
from typing import Any, Iterable, List, Union, Set

import click

import motherlib.client
import motherlib.model


SERVER_ADDR = 'http://localhost:8080'


def basetags(tags: Set[str]) -> Set[str]:
    basetags = os.getenv('BASETAGS', '')
    if basetags == '':
        return tags
    b = set(basetags.split('/'))
    return b.union(tags)


def print_records(records: List[motherlib.model.Record]) -> None:
    for r in records:
        print(f'{r.created.date()} {r.ref[:9]} {"/".join(r.tags)}')


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx: click.Context, **kwargs: str) -> None:
    if ctx.invoked_subcommand is None:
        ctx = click.get_current_context()
        click.echo(ctx.get_help())
        ctx.exit()


@cli.command()
@click.argument('tags')
@click.argument('filepath')
def u(tags: str, filepath: str) -> None:
    t = basetags(set(tags.split('/')))
    api = motherlib.client.APIClient(addr=SERVER_ADDR)
    with Path(filepath).open() as f:
        print(api.put_latest(tags=t, content=f))


@cli.command()
@click.argument('tags')
def e(tags: str) -> None:
    t = basetags(set(tags.split('/')))
    api = motherlib.client.APIClient(addr=SERVER_ADDR)
    exists = True
    try:
        result = api.get_latest(tags=t)
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
    print(api.put_latest(tags=t, content=str.encode(message)))


@cli.command()
@click.argument('tags', default='')
def l(tags: str) -> None:
    api = motherlib.client.APIClient(addr=SERVER_ADDR)
    if len(tags) > 0 and tags[-1] == '/':
        t = basetags(set(tags[:-1].split('/')))
        result = api.get_superset_latest(tags=t)
    else:
        t = basetags(set(tags.split('/')))
        result = api.get_latest(tags=t)
    if result.content is not None:
        print(result.content.read())
        return
    print_records(result.records)


@cli.command()
@click.argument('tags', default='')
def h(tags: str) -> None:
    api = motherlib.client.APIClient(addr=SERVER_ADDR)
    if len(tags) > 0 and tags[-1] == '/':
        t = basetags(set(tags[:-1].split('/')))
        records = api.get_superset_history(tags=t)
    else:
        t = basetags(set(tags.split('/')))
        records = api.get_history(tags=t)
    print_records(records)


@cli.command()
@click.argument('tags')
def d(tags: str) -> None:
    api = motherlib.client.APIClient(addr=SERVER_ADDR)
    if len(tags) > 0 and tags[-1] == '/':
        t = basetags(set(tags[:-1].split('/')))
        api.delete_superset_history(tags=t)
    else:
        t = basetags(set(tags.split('/')))
        api.delete_history(tags=t)


@cli.command()
@click.argument('src', required=True)
@click.argument('dst', required=True)
def mv(src: str, dst: str) -> None:
    api = motherlib.client.APIClient(addr=SERVER_ADDR)

    superset_src = src[-1] == '/'
    superset_dst = dst[-1] == '/'

    src_tags = basetags(set(src.split('/')))
    if superset_src:
        src_tags = basetags(set(src[:-1].split('/')))

    dst_tags = basetags(set(dst.split('/')))
    if superset_dst:
        dst_tags = basetags(set(dst[:-1].split('/')))


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
        records = api.get_superset_history(tags=src_tags)
    else:
        records = api.get_history(tags=src_tags)

    for r in reversed(records):
        content = api.get_blob(ref=r.ref)

        new_tags = r.tags

        if superset_src or not superset_dst:
            new_tags = (r.tags - src_tags)

        new_tags = new_tags | dst_tags

        print(api.put_latest(tags=new_tags, content=content))

        if superset_src:
            api.delete_superset_history(tags=src_tags)
        else:
            api.delete_history(tags=src_tags)


if __name__ == '__main__':
    try:
        cli()
    except motherlib.client.ConnectionError:
        print(f'Unable to connect to server {SERVER_ADDR}.')
    except motherlib.client.APIError as exc:
        print(exc.err)
        print(exc.kind)
