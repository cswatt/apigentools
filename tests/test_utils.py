import copy
import logging
import os
import subprocess

import flexmock
import pytest

from apigentools.constants import REDACTED_OUT_SECRET
from apigentools.utils import env_or_val, log, run_command, set_log


@pytest.mark.parametrize("env_var, default, args, typ, kwargs, set_env_to, expected", [
    ("APIGENTOOLS_TEST", "default", [], str, {}, None, "default"),
    ("APIGENTOOLS_TEST", "default", [], str, {}, "nondefault", "nondefault"),
    ("APIGENTOOLS_TEST", lambda x: x, ["spam"], str, {}, None, "spam"),
    ("APIGENTOOLS_TEST", lambda x: x, ["spam"], str, {}, "nondefault", "nondefault"),
    ("APIGENTOOLS_TEST", False, [], bool, {}, "TrUe", True),
    ("APIGENTOOLS_TEST", True, [], bool, {}, "FaLsE", False),
    ("APIGENTOOLS_TEST", [], [], list, {}, "foo:bar:baz", ["foo", "bar", "baz"]),
    ("APIGENTOOLS_TEST", 0, [], int, {}, "123", 123),
    ("APIGENTOOLS_TEST", 0.0, [], float, {}, "123.123", 123.123),
])
def test_env_or_val(env_var, default, args, typ, kwargs, set_env_to, expected):
    if set_env_to is None:
        if env_var in os.environ:
            del os.environ[env_var]
    else:
        os.environ[env_var] = set_env_to

    assert env_or_val(env_var, default, *args, __type=typ, **kwargs) == expected


def test_run_command(caplog):
    cmd = ["run", "this"]
    log_level = logging.INFO
    additional_env = {"SOME_ADDITIONAL_ENV": "value"}
    env = copy.deepcopy(os.environ)
    env.update(additional_env)
    combine_out_err = False

    flexmock(subprocess).should_receive("run").\
        with_args(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True, env=env).\
        and_return(subprocess.CompletedProcess(cmd, 0, "stdout", "stderr"))
    res = run_command(cmd, log_level=log_level, additional_env=additional_env, combine_out_err=combine_out_err)
    assert res.returncode == 0
    assert res.stdout == "stdout"
    assert res.stderr == "stderr"

    flexmock(subprocess).should_receive("run").\
        with_args(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True, env=env).\
        and_raise(subprocess.CalledProcessError(1, cmd, "stdout", "stderr"))
    with pytest.raises(subprocess.CalledProcessError):
        run_command(cmd, log_level=log_level, additional_env=additional_env, combine_out_err=combine_out_err)

    # test that secrets are not logged
    set_log(log)
    caplog.clear()
    caplog.set_level(logging.DEBUG, logger=log.name)
    secret = "abcdefg"
    cmd = ["run", {"secret": True, "item": secret}]
    flexmock(subprocess).should_receive("run").\
        with_args(["run", "abcdefg"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True, env=env).\
        and_return(subprocess.CompletedProcess(cmd, 0, "stdout", "stderr"))
    res = run_command(cmd, log_level=log_level, additional_env=additional_env, combine_out_err=combine_out_err)
    assert secret not in caplog.text
    assert REDACTED_OUT_SECRET in caplog.text