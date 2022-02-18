[![CI](https://github.com/oversight-monitoring/agentcoreclient/workflows/CI/badge.svg)](https://github.com/oversight-monitoring/agentcoreclient/actions)
[![Release Version](https://img.shields.io/github/release/oversight-monitoring/agentcoreclient)](https://github.com/oversight-monitoring/agentcoreclient/releases)

# Oversight AgentCore Client

This is a library to create probes for the [Oversight platform](https://oversig.ht).

## Supported environment variable

Variable              | Description
--------------------- | -----------
`OS_LOG_LEVEL`        | Log level. One of `debug`, `info`, `warning`, `error` or `critical`.
`OS_AGENTCORE_IP`     | Set the agent core Ip address. Fallback to `agentCoreIp` from the configuration and finally `localhost`.
`OS_AGENTCORE_PORT`   | Set the agent core port. Fallback to `agentCorePort` from the configuration and finally `7211`.
`OS_CONFIG_FOLDER`    | Set the configuration folder. The assets configuration files must be stored in this folder.
`OS_CONFIG_FILENAME`  | Path to the probe configuration file. If not set, the `config_fn` argument of the `AgentCoreClient` will be used instead.
