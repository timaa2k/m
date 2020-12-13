import datetime
import time
import os
import sys
import textwrap
import urllib3
import webbrowser
from pathlib import Path
from typing import Any, Dict, Iterable, List, Union, Set
from validator_collection import checkers

import click
import jwt
from bs4 import BeautifulSoup

import motherlib.client
import motherlib.model
from m import __version__


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


CREDENTIALS_PATH = os.environ['HOME'] + '/.config/m/credentials'


def save_token(t: str) -> None:
    Path(CREDENTIALS_PATH).parent.mkdir(parents=True, exist_ok=True)
    Path(CREDENTIALS_PATH).write_text(t)


def load_token() -> str:
    return Path(CREDENTIALS_PATH).read_text()


def is_valid_jwt(token: str) -> bool:
    try:
        jwt.decode(token, verify=False)
    except Exception:
        return False
    return True


def uid_from_jwt(token: str) -> str:
    decoded = jwt.decode(token, verify=False)
    return decoded['uid']


def remove_if_in_target(tags: List[str], target: List[str]) -> List[str]:
    n = {}
    for tag in tags:
        n[tag] = True
    return [t for t in target if not n.get(t, False)]


def filter_and_prefix_with_base(tags: List[str]) -> List[str]:
    return tags


def print_records(namespace: Set[str], src_tags: Set[str], records: List[motherlib.model.Record]) -> None:
    for r in records:
        t = remove_if_in_target(namespace, r.tags)
        t = remove_if_in_target(src_tags, t)
        print(f'{r.created.date()} {r.ref.split("/cas/")[1][:9]} {"/".join(t)}')


@click.group(invoke_without_command=True)
@click.option('-h', '--host', type=str, default='https://localhost')
@click.option('-n', '--namespace', type=str, default='')
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx: click.Context, host: str, namespace: str) -> None:
    if ctx.obj is None:
        ctx.obj = {}  # type=Dict[str, Any]

    if ctx.invoked_subcommand == 'login':
        ctx.obj['api'] = motherlib.client.APIClient(
            addr=os.getenv('M_HOST', host),
            resource_owner_uid='',
        )
    else:
        try:
            token = load_token()
        except FileNotFoundError:
            print('Please sign in via the login subcommand')
            sys.exit(1)

        ctx.obj['api'] = motherlib.client.APIClient(
            addr=os.getenv('M_HOST', host),
            resource_owner_uid=uid_from_jwt(token),
            bearer_token=token,
        )
        ns_tags = os.getenv('M_NAMESPACE', namespace)
        ctx.obj['namespace'] = [] if ns_tags == '' else ns_tags.split('/')
        if ctx.invoked_subcommand is None:
            ctx.invoke(ls)


@cli.command()
@click.argument(
    'provider',
    required=True,
    type=click.Choice(['google'], case_sensitive=False),
)
@click.pass_obj
def login(ctx: Dict[str, Any], provider: str) -> None:
    api = ctx['api']
    authinfo = api.get_login_info(provider=provider)
    print('')
    print(f'Copy the following URL into your browser to sign in via {authinfo.provider_name}')
    print('')
    print(authinfo.auth_url)
    print('')
    token = click.prompt('Paste the resulting authentication token into the terminal')
    if not is_valid_jwt(token.strip()):
        print('Invalid token submitted')
        return
    save_token(token)


@cli.command()
@click.argument('tags', required=True)
@click.argument('filepath', required=True)
@click.pass_obj
def upload(ctx: Dict[str, Any], tags: str, filepath: str) -> None:
    api = ctx['api']
    namespace = ctx['namespace']
    t = remove_if_in_target(namespace, tags.split('/'))
    if checkers.is_url(filepath):
        link = f'<head><meta http-equiv="Refresh" content="0; URL={filepath}"></head>'
        print(api.put_latest(tags=namespace+t, content=str.encode(link)))
        return
    with Path(filepath).open(mode='rb') as f:
        print(api.put_latest(tags=namespace+t, content=f))


@cli.command()
@click.argument('tags', required=True)
@click.pass_obj
def edit(ctx: Dict[str, Any], tags: str) -> None:
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
    previous = ''
    if exists:
        if len(records) > 1:
            print_records(namespace, t, records)
            return
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
def ls(ctx: Dict[str, Any], tags: str) -> None:
    api = ctx['api']
    namespace = ctx['namespace']
    t = [] if tags == '' else tags.split('/')
    t = remove_if_in_target(namespace, t)
    print_records(namespace, t, api.get_latest(tags=namespace+t))


def is_binary(content: bytes) -> bool:
    textchars = bytearray([7,8,9,10,12,13,27]) + bytearray(range(0x20, 0x7f)) + bytearray(range(0x80, 0x100))
    is_binary_string = lambda bytes: bool(bytes.translate(None, textchars))
    return is_binary_string(content)


def is_html(content: str) -> bool:
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        return bool(BeautifulSoup(content, "html.parser").find())


@cli.command()
@click.argument('tags', required=True)
@click.pass_obj
def open(ctx: Dict[str, Any], tags: str) -> None:
    api = ctx['api']
    namespace = ctx['namespace']
    t = [] if tags == '' else tags.split('/')
    t = remove_if_in_target(namespace, t)
    records = api.get_latest(tags=namespace+t)
    if len(records) != 1:
        print_records(namespace, t, records)
    else:
        digest = records[0].ref
        content = api.cas_get(digest).read()
        location = '/'.join(namespace+t)
        URL = f'{api.addr}{digest}'
        if is_binary(content):
            webbrowser.open_new_tab(URL)
            return
        decoded = content.decode()
        if is_html(decoded):
            webbrowser.open_new_tab(URL)
            return
        else:
            print(decoded)


@cli.command()
@click.argument('tags', default='')
@click.pass_obj
def history(ctx: Dict[str, Any], tags: str) -> None:
    api = ctx['api']
    namespace = ctx['namespace']
    t = [] if tags == '' else tags.split('/')
    t = remove_if_in_target(namespace, t)
    print_records(namespace, t, api.get_history(tags=namespace+t))


@cli.command()
@click.argument('tags')
@click.pass_obj
def rm(ctx: Dict[str, Any], tags: str) -> None:
    api = ctx['api']
    namespace = ctx['namespace']
    t = [] if tags == '' else tags.split('/')
    t = remove_if_in_target(namespace, t)
    api.delete_history(tags=namespace+t)


@cli.command()
@click.argument('src', required=True)
@click.argument('dst', required=True)
@click.pass_obj
def mv(ctx: Dict[str, Any], src: str, dst: str) -> None:
    api = ctx['api']
    namespace = ctx['namespace']

    s = [] if src == '' else src.split('/')
    d = [] if src == '' else dst.split('/')
    src_tags = remove_if_in_target(namespace, s)
    dst_tags = remove_if_in_target(namespace, d)

    records = api.get_history(tags=namespace+src_tags)

    for r in reversed(records):
        content = api.cas_get(ref=r.ref).read()

        t = remove_if_in_target(namespace, r.tags)
        t = remove_if_in_target(src_tags, t)
        t = namespace + dst_tags + t
        digest = api.put_latest(tags=t, content=content)

        print(digest)

        api.delete_history(tags=namespace+src_tags)


def main():
    try:
        cli()
    except motherlib.client.ConnectionError:
        print(f'ConnectionError: cannot connect to server.')
    except motherlib.client.APIError as exc:
        print(exc.message)


if __name__ == '__main__':
    main()
