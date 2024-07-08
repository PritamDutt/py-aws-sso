# py-aws-sso

Simple Python library for AWS SSO credential management in local development.

## About
**py-aws-sso** simplifies obtaining short-term credentials for CLI and Boto3 operations when using AWS SSO during local Python development. 

## How To Video Guide

Video detailing the steps of configuring AWS SSO Profile using AWS CLI and using this module is available on [YouTube](https://youtu.be/UEj0RnXg-rA)

[![Simplying AWS SSO Credentials for Python Developers](https://img.youtube.com/vi/UEj0RnXg-rA/0.jpg)](https://youtu.be/UEj0RnXg-rA "Simplying AWS SSO Credentials for Python Developers")


## Motivation

In our organization developing applications that interact with AWS accounts often requires managing long-term 
credentials. This can lead to several challenges, including:

- **Security risks**: Long-term credentials pose a security risk if compromised.
- **Credential management overhead**: Developers need to securely store and manage long-term credentials, which can be 
  cumbersome.
- **Role-switching complexity**: Switching between different roles or accounts can be inconvenient with long-term 
  credentials.

**py-aws-sso** addresses these challenges by providing a simple solution to obtain temporary AWS credentials during 
local development. By leveraging temporary credentials, developers can:

- **Enhance security**: Mitigate the risks associated with long-term credential leaks.
- **Simplify credential management**: Eliminate the need to store and manage long-term credentials locally.
- **Effortlessly switch roles**: Easily switch between different roles and accounts within their development workflow.

This  simple solution to this problem but piggy backing on AWS CLI v2 tool.

## How it works

**py-aws-sso** simplifies obtaining temporary credentials by leveraging the AWS CLI v2 tool. It uses the existing 
AWS CLI configuration, and uses `boto3` library to retrieve temporary credentials for the specified profile. If you 
haven't already established an SSO login session, **py-aws-sso** will automatically trigger one for you.

## Prerequisites

This Python 3 module requires a working installation of the [AWS CLI v2](https://docs.aws.amazon.
com/cli/latest/userguide/install-cliv2.html) and the `boto3` library

## Setting Up

1. **Install and Configure AWS CLI v2**: Follow the official documentation @ https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html 
   to install and configure AWS CLI v2 with your SSO profiles.

2. **Include py-aws-sso**: Install py-aws-sso.
> pip install py-aws-sso
>
> --or--
> 
> pdm add py-aws-sso   

3. **Run Your Project**:
   - Create a `local_run.py` file to execute your project using Python. 
   - Import `set_aws_creds` from the `awssso` module. 
   - Call `set_aws_creds` with these arguments:
     - `profile_name` (string): The name of the AWS CLI profile to use. 
     - `verbose` (boolean, optional): Set to `True` to print verbose messages (defaults to False).

## Inspiration:

This project is inspired by the `aws-sso-credentials project`. However, it caters specifically to Python developers 
and focuses on local development workflows.


## Example

```python
from awssso import set_aws_creds

# Assuming your AWS profile name is "my-sso-profile"
set_aws_creds(profile_name="my-sso-profile", verbose=True)

# Now you can use boto3 with the temporary credentials
import boto3

s3_client = boto3.client("s3")
response = s3_client.list_buckets()
print(response)

```

Example [fastapi](https://fastapi.tiangolo.com/) project is included for quick reference


