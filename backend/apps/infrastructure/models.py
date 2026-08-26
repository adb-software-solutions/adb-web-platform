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
from .legacy_resource_links import (
    APIResourceIdentity,
    ApplicationResourceIdentity,
    BotResourceIdentity,
    DatabaseResourceIdentity,
    DomainResourceIdentity,
    EmailSystemResourceIdentity,
    LicenceResourceIdentity,
    MobileAppResourceIdentity,
    ServerResourceIdentity,
    SSLCertificateResourceIdentity,
    WebsiteResourceIdentity,
)
from .resource_models import (
    InfrastructureResource,
    InfrastructureTag,
    ProviderAccount,
    ResourceRelationship,
    ServiceProvider,
)
from .specialist_models import IPAddress, Network, NetworkInterface, ServerProfile, Subnet

__all__ = [
    "API",
    "APIResourceIdentity",
    "Application",
    "ApplicationResourceIdentity",
    "Bot",
    "BotResourceIdentity",
    "Database",
    "DatabaseResourceIdentity",
    "Domain",
    "DomainResourceIdentity",
    "EmailSystem",
    "EmailSystemResourceIdentity",
    "IPAddress",
    "InfrastructureResource",
    "InfrastructureTag",
    "Licence",
    "LicenceResourceIdentity",
    "MobileApp",
    "MobileAppResourceIdentity",
    "Network",
    "NetworkInterface",
    "ProviderAccount",
    "ResourceRelationship",
    "SSLCertificate",
    "SSLCertificateResourceIdentity",
    "Server",
    "ServerProfile",
    "ServerResourceIdentity",
    "ServiceProvider",
    "Subnet",
    "Website",
    "WebsiteResourceIdentity",
    "WebsiteTechStack",
]
