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
def r(tags: str, filepath: str) -> None:
    t = basetags(set(tags.split('/')))
    api = motherlib.client.APIClient(addr=SERVER_ADDR)
    try:
        result = api.get_latest(tags=t)
    except motherlib.client.ConnectionError:
        print(f'Unable to connect to server {SERVER_ADDR}.')
        return
    except motherlib.client.APIError as exc:
        if exc.kind != "Not found":
            print(exc.err)
            print(exc.kind)
            return
        with Path(filepath).open() as f:
            try:
                digest = api.put_latest(tags=t, content=f)
            except motherlib.client.ConnectionError:
                print(f'Unable to connect to server {SERVER_ADDR}.')
                return
            except motherlib.client.APIError as exc:
                print(exc.err)
                print(exc.kind)
                return

        print(digest)
        return

    if result.records is not None:
        print(f'Aborting: {tags} is not a unique identifier.')
        return

    with Path(filepath).open() as f:
        try:
            digest = api.put_latest(tags=t, content=f)
        except motherlib.client.ConnectionError:
            print(f'Unable to connect to server {SERVER_ADDR}.')
            return
        except motherlib.client.APIError as exc:
            print(exc.err)
            print(exc.kind)
            return

    print(digest)
    return


@cli.command()
@click.argument('tags')
def e(tags: str) -> None:
    t = basetags(set(tags.split('/')))
    api = motherlib.client.APIClient(addr=SERVER_ADDR)
    try:
        result = api.get_latest(tags=t)
    except motherlib.client.ConnectionError:
        print(f'Unable to connect to server {SERVER_ADDR}.')
        return
    except motherlib.client.APIError as exc:
        if exc.kind != "Not found":
            print(exc.err)
            print(exc.kind)
            return
        message = click.edit('')
        if message is None:
            print('Aborting: empty content.')
            return
        try:
            digest = api.put_latest(tags=t, content=str.encode(message))
        except motherlib.client.ConnectionError:
            print(f'Unable to connect to server {SERVER_ADDR}.')
            return
        except motherlib.client.APIError as exc:
            print(exc.err)
            print(exc.kind)
            return
        print(digest)
        return

    if result.records is not None:
        print(f'Aborting: {tags} is not a unique identifier.')
        return
    try:
        records = api.get_history(tags=t)
    except motherlib.client.ConnectionError:
        print(f'Unable to connect to server {SERVER_ADDR}.')
        return
    except motherlib.client.APIError as exc:
        print(exc.err)
        print(exc.kind)
        return

    message = click.edit(result.content.read().decode())
    if message is None:
        print('Aborting: empty content.')
        return
    try:
        digest = api.put_latest(
            tags=set(records[0].tags),
            content=str.encode(message),
        )
    except motherlib.client.ConnectionError:
        print(f'Unable to connect to server {SERVER_ADDR}.')
        return
    except motherlib.client.APIError as exc:
        print(exc.err)
        print(exc.kind)
        return

    print(digest)


@cli.command()
@click.argument('tags')
def l(tags: str) -> None:
    t = basetags(set(tags.split('/')))
    api = motherlib.client.APIClient(addr=SERVER_ADDR)
    try:
        result = api.get_latest(tags=t)
    except motherlib.client.ConnectionError:
        print(f'Unable to connect to server {SERVER_ADDR}.')
        return
    except motherlib.client.APIError as exc:
        print(exc.err)
        print(exc.kind)
        return
    if result.content is not None:
        print(result.content.read())
        return
    print_records(result.records)


@cli.command()
@click.argument('tags')
def h(tags: str) -> None:
    t = basetags(set(tags.split('/')))
    api = motherlib.client.APIClient(addr=SERVER_ADDR)
    try:
        records = api.get_history(tags=t)
    except motherlib.client.ConnectionError:
        print(f'Unable to connect to server {SERVER_ADDR}.')
        return
    except motherlib.client.APIError as exc:
        print(exc.err)
        print(exc.kind)
        return
    print_records(records)


@cli.command()
@click.argument('src')
@click.argument('dst')
def cp(src: str, dst: str) -> None:
    s = basetags(set(src.split('/')))
    d = basetags(set(dst.split('/')))
    api = motherlib.client.APIClient(addr=SERVER_ADDR)
    try:
        records = api.get_history(tags=s)
    except motherlib.client.ConnectionError:
        print(f'Unable to connect to server {SERVER_ADDR}.')
        return
    except motherlib.client.APIError as exc:
        print(exc.err)
        print(exc.kind)
        return

    for r in reversed(records):
        try:
            content = api.get_blob(ref=r.ref)
        except motherlib.client.ConnectionError:
            print(f'Unable to connect to server {SERVER_ADDR}.')
            return
        except motherlib.client.APIError as exc:
            print(exc.err)
            print(exc.kind)
            return

        try:
            digest = api.put_latest(
                tags=d,
                content=content,
            )
        except motherlib.client.ConnectionError:
            print(f'Unable to connect to server {SERVER_ADDR}.')
            return
        except motherlib.client.APIError as exc:
            print(exc.err)
            print(exc.kind)
            return

        print(digest)
        time.sleep(1)


@cli.command()
@click.argument('src')
@click.argument('dst')
def mv(src: str, dst: str) -> None:
    s = basetags(set(src.split('/')))
    d = basetags(set(dst.split('/')))
    api = motherlib.client.APIClient(addr=SERVER_ADDR)
    try:
        records = api.get_history(tags=s)
    except motherlib.client.ConnectionError:
        print(f'Unable to connect to server {SERVER_ADDR}.')
        return
    except motherlib.client.APIError as exc:
        print(exc.err)
        print(exc.kind)
        return

    for r in reversed(records):
        try:
            content = api.get_blob(ref=r.ref)
        except motherlib.client.ConnectionError:
            print(f'Unable to connect to server {SERVER_ADDR}.')
            return
        except motherlib.client.APIError as exc:
            print(exc.err)
            print(exc.kind)
            return

        try:
            digest = api.put_latest(tags=d, content=content)
        except motherlib.client.ConnectionError:
            print(f'Unable to connect to server {SERVER_ADDR}.')
            return
        except motherlib.client.APIError as exc:
            print(exc.err)
            print(exc.kind)
            return

        print(digest)
        time.sleep(1)

    for r in reversed(records):
        try:
            api.delete_history(tags=s)
        except motherlib.client.ConnectionError:
            print(f'Unable to connect to server {SERVER_ADDR}.')
            return
        except motherlib.client.APIError as exc:
            print(exc.err)
            print(exc.kind)
            return


@cli.command()
@click.argument('tags')
def d(tags: str) -> None:
    t = basetags(set(tags.split('/')))
    api = motherlib.client.APIClient(addr=SERVER_ADDR)
    try:
        api.delete_history(tags=t)
    except motherlib.client.ConnectionError:
        print(f'Unable to connect to server {SERVER_ADDR}.')
        return
    except motherlib.client.APIError as exc:
        print(exc.err)
        print(exc.kind)
        return


if __name__ == '__main__':
    cli()
