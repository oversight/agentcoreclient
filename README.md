[![CI](https://github.com/oversight/agentcoreclient/workflows/CI/badge.svg)](https://github.com/oversight/agentcoreclient/actions)
[![Release Version](https://img.shields.io/github/release/oversight/agentcoreclient)](https://github.com/oversight/agentcoreclient/releases)

# Oversight AgentCore Client

This is a library to create probes for the [Oversight platform](https://oversig.ht).

## Supported environment variable

Variable              | Description
--------------------- | -----------
`OS_LOG_LEVEL`        | Log level. One of `debug`, `info`, `warning`, `error` or `critical`. If not set, the `log_level` argument of the `setup_logger(..)` method will be used.
`OS_AGENTCORE_IP`     | Set the agent core Ip address. Fallback to `agentCoreIp` from the configuration and finally `localhost`.
`OS_AGENTCORE_PORT`   | Set the agent core port. Fallback to `agentCorePort` from the configuration and finally `7211`.
`OS_CONFIG_FOLDER`    | Set the configuration folder. The assets configuration files must be stored in this folder. If not set, `/etc` will be used. *(This environment variable is usually configured in the Dockerfile of the corresponding probe)*
`OS_CONFIG_FILENAME`  | Path to the probe configuration file. If not set, the `config_fn` argument of the `AgentCoreClient` will be used instead. *(It is recommended to configure the `config_fn` argument when building a probe and not rely on this environment variable only)*

## Reload local config

The local configuration files will be read only the first time this is required for an asset. If you with to reload the configuration, for example when the configuration has been changed, this can be done by adding a file named `reload` inside the configuration folder. For example:

```bash
/data/config/sampleprobe/$ touch reload
```
