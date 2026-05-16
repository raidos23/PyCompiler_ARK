# Backward-compatibility shim.
# This package has been merged into Core.Configs.
# All symbols are re-exported from there unchanged.
from Core.Configs import (  # noqa: F401
    CONFIG_KEYS,
    DEFAULT_USER_DIRS,
    UserConfigError,
    config_file_for,
    config_home,
    ensure_config_home,
    resolve_config_value,
    set_config_value,
    unset_config_value,
)
