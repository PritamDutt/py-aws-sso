import logging

import uvicorn

from awssso import set_aws_creds
from main import app

# Replace these with your own values
aws_profile = 'test-sso'
set_aws_creds(profile_name=aws_profile, verbose=True)

logging.basicConfig(level=logging.DEBUG)


def run_api_local():
    from uvicorn.config import LOGGING_CONFIG
    log_config = LOGGING_CONFIG
    log_config["formatters"]["access"]["fmt"] = (
            "%(asctime)s " + LOGGING_CONFIG["formatters"]["access"]["fmt"]
    )
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="debug",
        reload=False,
        log_config=log_config
    )


if __name__ == "__main__":
    run_api_local()
