"""
@Filename : awssso.py
@created :  May 28 12:10 2024
@project: dynamic sso
@author : pritam
"""

import os
import re
import subprocess
import sys
from configparser import ConfigParser
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import boto3
import botocore
from botocore.tokens import DeferredRefreshableToken, FrozenAuthToken
from dateutil.tz import UTC, tzlocal

VERBOSE_MODE = False

AWS_CONFIG_PATH = f'{Path.home()}/.aws/config'
AWS_CREDENTIAL_PATH = f'{Path.home()}/.aws/credentials'
AWS_DEFAULT_REGION = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')


class Colour:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def set_aws_creds(profile_name: str, *, verbose: bool = False) -> Optional[dict]:
    """
    Retrieves AWS credentials from SSO for use with CLI/Boto3 apps.
    Clones selected profile and credentials into the default profile.


    :param profile_name: AWS config profile to retrieve credentials for
    :type profile_name: str
    :param verbose: Show verbose output, messages, etc.
    :type verbose: bool
    """

    # validate aws v2
    try:
        aws_version = subprocess.run(['aws', '--version'], capture_output=True).stdout.decode('utf-8')

        if 'aws-cli/2' not in aws_version:
            _print_error('\n AWS CLI Version 2 not found. Please install. Exiting.')
            exit(1)

    except Exception as e:
        _print_error(
            f'\nAn error occured trying to find AWS CLI version. Do you have AWS CLI Version 2 installed?\n{e}')
        exit(1)

    global VERBOSE_MODE
    VERBOSE_MODE = verbose

    return _set_profile_credentials(profile_name, profile_name != 'default')


def _set_profile_credentials(profile_name: str, use_default=False) -> Optional[dict]:
    """
        Sets AWS profile credentials for the given profile.

        If the profile is an SSO profile, it retrieves the cached SSO login,
        fetches the short-term CLI/Boto3 session token, and stores the credentials
        in the AWS credentials file. If the 'use_default' flag is set, it also copies
        the profile credentials to the 'default' profile.

        :param profile_name: The name of the AWS profile to set credentials for.
        :type profile_name: str
        :param use_default: A flag indicating whether to copy the profile credentials to the 'default' profile.
        :type use_default: bool
        :return: None
        """
    profile_opts = _get_aws_profile(profile_name)

    if profile_opts != "NotSSO":
        auth_token = _get_sso_cached_login(profile_name)
        credentials = _get_sso_role_credentials(profile_opts, auth_token)

        if not use_default:
            profile = _add_prefix(profile_name)
            _store_aws_credentials(profile, profile_opts, credentials)
        elif use_default:
            _store_aws_credentials('default', profile_opts, credentials)
            _copy_to_default_profile(profile_name)

        return credentials


def _get_aws_profile(profile_name):
    _print_msg(f'\nReading profile: [{profile_name}]')
    config = _read_config(AWS_CONFIG_PATH)
    prefixed_profile = _add_prefix(profile_name)
    if prefixed_profile not in config.sections():
        _print_error(
            f'\nProfile [{profile_name}] not found in AWS CLI configuration.You can create a new profile using the following command'
            f'\naws configure sso')
        return
    profile_opts = config.items(prefixed_profile)
    if "sso_session" in dict(profile_opts):
        profile = dict(profile_opts)
        sso_session = profile.get("sso_session")
        sso_opts = config.items(f"sso-session {sso_session}")
        profile.update(sso_opts)
    else:
        _print_msg(f'\n [{profile_name}] is not an SSO profile')
        profile = "NotSSO"
    return profile


def _get_sso_cached_login(profile_name) -> FrozenAuthToken:
    _print_msg('\nChecking for SSO credentials...')
    sso_token: Optional[DeferredRefreshableToken] = None
    try:
        sso_token = botocore.tokens.SSOTokenProvider(botocore.session.Session(),
                                                     profile_name=profile_name).load_token()
        auth_token = sso_token.get_frozen_token()
    except botocore.exceptions.TokenRetrievalError as e:
        _print_msg(
            f'{e}. Invoking Session Login')
        _spawn_cli_for_auth(profile_name)

    auth_token = sso_token.get_frozen_token()
    expires_at = auth_token.expiration
    now = datetime.now().astimezone(UTC)

    if (now + timedelta(minutes=15)) >= expires_at:
        _print_warn(f'Your current SSO credentials will expire in less than 15 minutes! for [{profile_name}]')

    _print_success(f'Found credentials. Valid until {expires_at.astimezone(tzlocal())}')
    return auth_token


def _get_sso_role_credentials(profile, auth_token: FrozenAuthToken):
    _print_msg('\nFetching short-term CLI/Boto3 session token...')

    client = boto3.client('sso', region_name=profile['sso_region'])
    response = client.get_role_credentials(
        roleName=profile['sso_role_name'],
        accountId=profile['sso_account_id'],
        accessToken=auth_token.token,
    )

    expires = datetime.fromtimestamp(response['roleCredentials']['expiration'] / 1000.0, UTC)
    _print_success(f'Got session token. Valid until {expires.astimezone(tzlocal())}')

    return response["roleCredentials"]


def _store_aws_credentials(profile_name, profile_opts, credentials):
    _print_msg(f'\nAdding to credential files under [{profile_name}]')

    region = profile_opts.get("region", AWS_DEFAULT_REGION)
    config = _read_config(AWS_CREDENTIAL_PATH)

    if config.has_section(profile_name):
        config.remove_section(profile_name)

    config.add_section(profile_name)
    config.set(profile_name, "region", region)
    config.set(profile_name, "aws_access_key_id", credentials["accessKeyId"])
    config.set(profile_name, "aws_secret_access_key ", credentials["secretAccessKey"])
    config.set(profile_name, "aws_session_token", credentials["sessionToken"])

    _write_config(AWS_CREDENTIAL_PATH, config)


def _copy_to_default_profile(profile_name):
    _print_msg(f'Copying profile [{profile_name}] to [default]')

    config = _read_config(AWS_CONFIG_PATH)

    if config.has_section('default'):
        config.remove_section('default')

    config.add_section('default')
    profile = _add_prefix(profile_name)
    for key, value in config.items(profile):
        config.set('default', key, value)

    _write_config(AWS_CONFIG_PATH, config)


def _spawn_cli_for_auth(profile):
    subprocess.run(['aws', 'sso', 'login', '--profile', re.sub(r"^profile ", "", str(profile))],
                   stderr=sys.stderr,
                   stdout=sys.stdout,
                   check=True)


def _print_colour(colour, message, always=False):
    if always or VERBOSE_MODE:
        if os.environ.get('CLI_NO_COLOR', False):
            print(message)
        else:
            print(''.join([colour, message, Colour.ENDC]))


def _print_error(message):
    _print_colour(Colour.FAIL, message, always=True)
    sys.exit(1)


def _print_warn(message):
    _print_colour(Colour.WARNING, message, always=True)


def _print_msg(message):
    _print_colour(Colour.OKBLUE, message)


def _print_success(message):
    _print_colour(Colour.OKGREEN, message)


def _add_prefix(name):
    return f'profile {name}' if name != 'default' else 'default'


def _read_config(path) -> ConfigParser:
    config = ConfigParser()
    config.read(path)
    return config


def _write_config(path: str, config: ConfigParser) -> None:
    with open(path, "w") as destination:
        config.write(destination)


if __name__ == "__main__":
    profile_name = "profile_name"  # Set this to the name of the profile you want to use
    set_aws_creds(profile_name=profile_name, verbose=True)
