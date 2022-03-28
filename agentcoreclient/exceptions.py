class IgnoreResultException(Exception):
    """IgnoreResultException should be raised by a check if the result needs
    to be ignored.
    Nothing for this check will be returned to the AgentCore.
    """
    pass