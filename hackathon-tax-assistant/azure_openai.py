"""Utility to create OpenAI client supporting Azure resource & global endpoint modes.

Environment Variable Modes:

1. Azure Resource Endpoint (traditional):
   AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/
   AZURE_OPENAI_API_KEY=... (key from Azure portal)
   AZURE_OPENAI_API_VERSION=2024-10-01-preview (or appropriate)

2. Global Endpoint with Model Names (new):
   OPENAI_API_KEY=<multi-service key or AAD token via azure-identity not yet wired>
   OPENAI_ENDPOINT=https://models.inference.azure.com (default for global)

Set USE_GLOBAL_OPENAI=1 to force global endpoint path if both are present.

The rest of the code can call create_client() and pass a 'model' string (either deployment
name for Azure resource or model name for global inference).
"""

from __future__ import annotations
import os
from openai import OpenAI, AzureOpenAI
from typing import Optional


def _verbose() -> bool:
    return os.environ.get("OPENAI_VERBOSE", "").lower() in {"1", "true", "yes"}

def get_deployment_name() -> str:
    """Return the deployment name for the given model.

    This is a simple heuristic that assumes the model name is the same as the deployment name
    with the first character capitalized. This is true for all models deployed by the OpenAI
    team, but may not be true for models deployed by other teams.
    """
    return os.environ.get(f"DEPLOYMENT_NAME")

def create_client(purpose: Optional[str] = None) -> OpenAI:
    """Return an OpenAI client configured for Azure resource or global endpoint.

    Args:
        purpose: Optional hint (e.g. "embeddings") which allows forcing global endpoint
                 if FORCE_GLOBAL_EMBED=1 is set.

    Selection precedence:
      1. If purpose == embeddings and FORCE_GLOBAL_EMBED truthy -> global (if OPENAI_API_KEY)
      2. If USE_GLOBAL_OPENAI truthy -> global (if OPENAI_API_KEY)
      3. Azure resource vars present -> azure resource
      4. OPENAI_API_KEY alone -> global
      5. Else error
    """

    force_global_embed = (
        purpose == "embeddings" and os.environ.get("FORCE_GLOBAL_EMBED", "").lower() in {"1", "true", "yes"}
    )
    use_global = os.environ.get("USE_GLOBAL_OPENAI", "").lower() in {"1", "true", "yes"}

    azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    azure_key = os.environ.get("AZURE_OPENAI_API_KEY")
    azure_api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-01-preview")

    global_endpoint = os.environ.get("OPENAI_ENDPOINT", "https://models.inference.azure.com")
    global_key = os.environ.get("OPENAI_API_KEY")

    def make_global():
        if _verbose():
            print(f"[azure_openai] Using GLOBAL endpoint: {global_endpoint}")
        return OpenAI(base_url=global_endpoint, api_key=global_key)

    # 1. Force global for embeddings
    if force_global_embed and global_key:
        return make_global()

    # 2. Explicit global flag
    if use_global and global_key:
        return make_global()

    # 3. Azure resource
    if azure_endpoint and azure_key:
        if _verbose():
            print(f"[azure_openai] Using AZURE RESOURCE endpoint: {azure_endpoint} (api_version={azure_api_version})")
        return OpenAI(
            base_url=azure_endpoint,
            api_key=azure_key,
        )

    # 4. Fallback global
    if global_key:
        return make_global()

    raise RuntimeError("No valid configuration. Set AZURE_OPENAI_* or OPENAI_API_KEY.")


__all__ = ["create_client"]
