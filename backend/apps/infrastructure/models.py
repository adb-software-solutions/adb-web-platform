"""Infrastructure model exports.

The original flat infrastructure records remain available while the structured
resource layer is introduced alongside them. They will be migrated onto the new
resource identities incrementally rather than rewritten in place.
"""

from .legacy_models import (
    API,
    Application,
    Bot,
    Database,
    Domain,
    EmailSystem,
    Licence,
    MobileApp,
    Server,
    SSLCertificate,
    Website,
    WebsiteTechStack,
)
from .resource_models import (
    InfrastructureResource,
    InfrastructureTag,
    ProviderAccount,
    ResourceRelationship,
    ServiceProvider,
)

__all__ = [
    "API",
    "Application",
    "Bot",
    "Database",
    "Domain",
    "EmailSystem",
    "InfrastructureResource",
    "InfrastructureTag",
    "Licence",
    "MobileApp",
    "ProviderAccount",
    "ResourceRelationship",
    "SSLCertificate",
    "Server",
    "ServiceProvider",
    "Website",
    "WebsiteTechStack",
]
