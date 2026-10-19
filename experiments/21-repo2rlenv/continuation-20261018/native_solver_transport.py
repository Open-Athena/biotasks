"""Own-client HTTP authentication, separate from native solver model settings."""

from glm_solver_settings import agent_kwargs


def solver_transport_kwargs(api_base, application_token):
    if not isinstance(application_token, str) or len(application_token) < 32:
        raise ValueError('Protected inference-client application token required')
    kwargs = agent_kwargs(api_base)
    # Provider request options put this in HTTP headers, never model messages or
    # the JSON completion payload. Iris strips Authorization before forwarding.
    kwargs['llm_call_kwargs']['extra_headers'] = {'X-Biotasks21-Inference-Token': application_token}
    return kwargs
