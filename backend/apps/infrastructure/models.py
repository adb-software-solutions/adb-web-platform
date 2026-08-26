"""Infrastructure model exports.

The original flat infrastructure records remain available while the structured
resource layer is introduced alongside them. They will be migrated onto the new
resource identities incrementally rather than rewritten in place.
"""

from .data_application_models import (
    ApplicationEnvironment,
    ApplicationProfile,
    ApplicationRepositoryLink,
    DatabaseInstance,
    LogicalDatabase,
    SourceRepository,
)
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
    "ApplicationEnvironment",
    "ApplicationProfile",
    "ApplicationRepositoryLink",
    "ApplicationResourceIdentity",
    "Bot",
    "BotResourceIdentity",
    "Database",
    "DatabaseInstance",
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
    "LogicalDatabase",
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
    "SourceRepository",
    "Subnet",
    "Website",
    "WebsiteResourceIdentity",
    "WebsiteTechStack",
]
