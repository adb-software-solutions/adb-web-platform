"use client";

import {
    Button,
    Card,
    DataError,
    DataLoading,
    Input,
    PageHeader,
    Select,
    Textarea,
} from "@/components/ui";
import { fetchAPI } from "@/lib/api/fetch";
import { API_URL } from "@/lib/config";
import { FormEvent, useEffect, useMemo, useState } from "react";

export type WebDomainType =
    "website" | "website_endpoint" | "domain" | "dns_zone" | "tls_certificate";

interface ScopedOption {
    resource_id: number;
    name: string;
    ownership_type: string;
    client_id: number | null;
    client_name: string | null;
}

interface ClientOption {
    id: number;
    name: string;
}

interface ProviderAccountOption extends ScopedOption {
    provider_name: string;
}

interface ApplicationEnvironmentOption extends ScopedOption {
    application_name: string;
    environment: string;
}

interface WebsiteOption extends ScopedOption {
    website_type: string;
}

interface DomainOption extends ScopedOption {
    domain_name: string;
}

interface TLSCertificateOption extends ScopedOption {
    subject_common_name: string;
}

interface WebDomainOptions {
    clients: ClientOption[];
    provider_accounts: ProviderAccountOption[];
    application_environments: ApplicationEnvironmentOption[];
    websites: WebsiteOption[];
    domains: DomainOption[];
    tls_certificates: TLSCertificateOption[];
}

interface SpecialistEditDetail {
    resource_id: number;
    resource_type: string;
    ownership_type: string;
    client_id: number | null;
    client_name: string | null;
    name: string;
    lifecycle_status: string;
    environment: string;
    criticality: string;
    description: string;
    values: Record<string, string | number | boolean | string[] | null>;
}

interface WebDomainInfrastructureFormProps {
    allowedTypes: WebDomainType[];
    editResourceId?: number;
    onCancel: () => void;
    onCreated?: (resourceId: number) => void;
    onSaved?: () => void;
}

const ENDPOINTS: Record<WebDomainType, string> = {
    website: "websites",
    website_endpoint: "website-endpoints",
    domain: "domains",
    dns_zone: "dns-zones",
    tls_certificate: "tls-certificates",
};

function label(value: WebDomainType): string {
    const labels: Record<WebDomainType, string> = {
        website: "Website",
        website_endpoint: "Website endpoint",
        domain: "Domain",
        dns_zone: "DNS zone",
        tls_certificate: "TLS certificate",
    };
    return labels[value];
}

function textValue(value: unknown): string {
    return value === null || value === undefined ? "" : String(value);
}

function numberOrNull(value: string): number | null {
    const trimmed = value.trim();
    return trimmed ? Number(trimmed) : null;
}

function triStateValue(value: unknown): string {
    return value === true ? "true" : value === false ? "false" : "";
}

function triStatePayload(value: string): boolean | null {
    return value === "true" ? true : value === "false" ? false : null;
}

function optionAllowed(
    option: ScopedOption,
    ownership: string,
    clientId: string,
): boolean {
    if (ownership === "internal") return option.ownership_type === "internal";
    return (
        option.ownership_type === "internal" ||
        option.client_id === Number(clientId)
    );
}

function FieldLabel({ children }: { children: React.ReactNode }) {
    return (
        <span className="mb-1.5 block text-xs font-medium text-slate-400">
            {children}
        </span>
    );
}

export function WebDomainInfrastructureForm({
    allowedTypes,
    editResourceId,
    onCancel,
    onCreated,
    onSaved,
}: WebDomainInfrastructureFormProps) {
    const isEditing = editResourceId !== undefined;
    const [options, setOptions] = useState<WebDomainOptions | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [type, setType] = useState<WebDomainType>(
        allowedTypes[0] ?? "website",
    );
    const [ownership, setOwnership] = useState("internal");
    const [clientId, setClientId] = useState("");
    const [name, setName] = useState("");
    const [lifecycle, setLifecycle] = useState("active");
    const [environment, setEnvironment] = useState("not_applicable");
    const [criticality, setCriticality] = useState("normal");
    const [description, setDescription] = useState("");

    const [websiteType, setWebsiteType] = useState("web_app");
    const [adminUrl, setAdminUrl] = useState("");
    const [cms, setCms] = useState("");
    const [cmsVersion, setCmsVersion] = useState("");
    const [hostingProviderId, setHostingProviderId] = useState("");
    const [cdnProviderId, setCdnProviderId] = useState("");
    const [wafProviderId, setWafProviderId] = useState("");

    const [websiteResourceId, setWebsiteResourceId] = useState("");
    const [applicationEnvironmentId, setApplicationEnvironmentId] =
        useState("");
    const [domainResourceId, setDomainResourceId] = useState("");
    const [tlsCertificateId, setTlsCertificateId] = useState("");
    const [url, setUrl] = useState("");
    const [role, setRole] = useState("primary");
    const [isPrimary, setIsPrimary] = useState(false);
    const [redirectsTo, setRedirectsTo] = useState("");

    const [domainName, setDomainName] = useState("");
    const [registrarAccountId, setRegistrarAccountId] = useState("");
    const [providerDomainId, setProviderDomainId] = useState("");
    const [domainStatus, setDomainStatus] = useState("unknown");
    const [registeredOn, setRegisteredOn] = useState("");
    const [expiresOn, setExpiresOn] = useState("");
    const [autoRenew, setAutoRenew] = useState("");
    const [transferLock, setTransferLock] = useState("");
    const [privacyEnabled, setPrivacyEnabled] = useState("");

    const [dnsProviderId, setDnsProviderId] = useState("");
    const [zoneName, setZoneName] = useState("");
    const [providerZoneId, setProviderZoneId] = useState("");
    const [dnssecEnabled, setDnssecEnabled] = useState("");
    const [zonePrimary, setZonePrimary] = useState(true);

    const [tlsProviderId, setTlsProviderId] = useState("");
    const [certificateType, setCertificateType] = useState("managed");
    const [issuer, setIssuer] = useState("");
    const [subjectCommonName, setSubjectCommonName] = useState("");
    const [providerCertificateId, setProviderCertificateId] = useState("");
    const [serialNumber, setSerialNumber] = useState("");
    const [fingerprintSha256, setFingerprintSha256] = useState("");
    const [issuedAt, setIssuedAt] = useState("");
    const [tlsExpiresAt, setTlsExpiresAt] = useState("");
    const [tlsAutoRenew, setTlsAutoRenew] = useState("");

    useEffect(() => {
        let active = true;

        async function load() {
            try {
                setIsLoading(true);
                setError(null);
                const optionResult = (await fetchAPI(
                    `${API_URL}/api/admin/infrastructure/web-domain-options`,
                )) as WebDomainOptions;
                if (!active) return;
                setOptions(optionResult);

                if (editResourceId === undefined) return;
                const detail = (await fetchAPI(
                    `${API_URL}/api/admin/infrastructure/resources/${editResourceId}/specialist-edit`,
                )) as SpecialistEditDetail;
                if (!active) return;
                const resourceType = detail.resource_type as WebDomainType;
                if (!allowedTypes.includes(resourceType)) {
                    throw new Error(
                        "This resource type cannot be edited with this form.",
                    );
                }

                setType(resourceType);
                setOwnership(detail.ownership_type);
                setClientId(
                    detail.client_id === null ? "" : String(detail.client_id),
                );
                setName(detail.name);
                setLifecycle(detail.lifecycle_status);
                setEnvironment(detail.environment);
                setCriticality(detail.criticality);
                setDescription(detail.description);

                const values = detail.values;
                setWebsiteType(textValue(values.website_type) || "web_app");
                setAdminUrl(textValue(values.admin_url));
                setCms(textValue(values.cms));
                setCmsVersion(textValue(values.cms_version));
                setHostingProviderId(
                    textValue(values.hosting_provider_account_resource_id),
                );
                setCdnProviderId(
                    textValue(values.cdn_provider_account_resource_id),
                );
                setWafProviderId(
                    textValue(values.waf_provider_account_resource_id),
                );

                setWebsiteResourceId(textValue(values.website_resource_id));
                setApplicationEnvironmentId(
                    textValue(values.application_environment_resource_id),
                );
                setDomainResourceId(textValue(values.domain_resource_id));
                setTlsCertificateId(
                    textValue(values.tls_certificate_resource_id),
                );
                setUrl(textValue(values.url));
                setRole(textValue(values.role) || "primary");
                setIsPrimary(values.is_primary === true);
                setRedirectsTo(textValue(values.redirects_to));

                setDomainName(textValue(values.domain_name));
                setRegistrarAccountId(
                    textValue(values.registrar_account_resource_id),
                );
                setProviderDomainId(textValue(values.provider_domain_id));
                setDomainStatus(textValue(values.status) || "unknown");
                setRegisteredOn(textValue(values.registered_on));
                setExpiresOn(textValue(values.expires_on));
                setAutoRenew(triStateValue(values.auto_renew));
                setTransferLock(triStateValue(values.transfer_lock_enabled));
                setPrivacyEnabled(triStateValue(values.privacy_enabled));

                setDnsProviderId(
                    textValue(values.provider_account_resource_id),
                );
                setZoneName(textValue(values.zone_name));
                setProviderZoneId(textValue(values.provider_zone_id));
                setDnssecEnabled(triStateValue(values.dnssec_enabled));
                setZonePrimary(values.is_primary !== false);

                setTlsProviderId(
                    textValue(values.provider_account_resource_id),
                );
                setCertificateType(
                    textValue(values.certificate_type) || "managed",
                );
                setIssuer(textValue(values.issuer));
                setSubjectCommonName(textValue(values.subject_common_name));
                setProviderCertificateId(
                    textValue(values.provider_certificate_id),
                );
                setSerialNumber(textValue(values.serial_number));
                setFingerprintSha256(textValue(values.fingerprint_sha256));
                setIssuedAt(textValue(values.issued_at));
                setTlsExpiresAt(textValue(values.expires_at));
                setTlsAutoRenew(triStateValue(values.auto_renew));
            } catch (loadError) {
                if (active) {
                    setError(
                        loadError instanceof Error
                            ? loadError.message
                            : "Unable to load web and domain infrastructure options.",
                    );
                }
            } finally {
                if (active) setIsLoading(false);
            }
        }

        void load();
        return () => {
            active = false;
        };
    }, [allowedTypes, editResourceId]);

    useEffect(() => {
        if (ownership === "internal") setClientId("");
    }, [ownership]);

    const providerAccounts = useMemo(
        () =>
            options?.provider_accounts.filter((option) =>
                optionAllowed(option, ownership, clientId),
            ) ?? [],
        [clientId, options, ownership],
    );
    const applicationEnvironments = useMemo(
        () =>
            options?.application_environments.filter((option) =>
                optionAllowed(option, ownership, clientId),
            ) ?? [],
        [clientId, options, ownership],
    );
    const websites = useMemo(
        () =>
            options?.websites.filter((option) =>
                optionAllowed(option, ownership, clientId),
            ) ?? [],
        [clientId, options, ownership],
    );
    const domains = useMemo(
        () =>
            options?.domains.filter((option) =>
                optionAllowed(option, ownership, clientId),
            ) ?? [],
        [clientId, options, ownership],
    );
    const certificates = useMemo(
        () =>
            options?.tls_certificates.filter((option) =>
                optionAllowed(option, ownership, clientId),
            ) ?? [],
        [clientId, options, ownership],
    );

    async function submit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        if (!name.trim()) {
            setError("Enter a resource name.");
            return;
        }
        if (!isEditing && ownership === "client" && !clientId) {
            setError("Choose the Client that owns this resource.");
            return;
        }
        if (
            type === "website_endpoint" &&
            (!websiteResourceId || !url.trim())
        ) {
            setError("Choose a Website and enter the endpoint URL.");
            return;
        }
        if (type === "domain" && !domainName.trim()) {
            setError("Enter the registered domain name.");
            return;
        }
        if (type === "dns_zone" && (!domainResourceId || !zoneName.trim())) {
            setError("Choose a Domain and enter the DNS zone name.");
            return;
        }

        const common: Record<string, unknown> = {
            name: name.trim(),
            lifecycle_status: lifecycle,
            environment,
            criticality,
            description: description.trim(),
        };
        if (!isEditing) {
            common.ownership_type = ownership;
            common.client_id = ownership === "client" ? Number(clientId) : null;
        }

        let payload: Record<string, unknown>;
        if (type === "website") {
            payload = {
                ...common,
                website_type: websiteType,
                admin_url: adminUrl.trim(),
                cms: cms.trim(),
                cms_version: cmsVersion.trim(),
                hosting_provider_account_resource_id:
                    numberOrNull(hostingProviderId),
                cdn_provider_account_resource_id: numberOrNull(cdnProviderId),
                waf_provider_account_resource_id: numberOrNull(wafProviderId),
            };
        } else if (type === "website_endpoint") {
            payload = {
                ...common,
                website_resource_id: Number(websiteResourceId),
                application_environment_resource_id: numberOrNull(
                    applicationEnvironmentId,
                ),
                domain_resource_id: numberOrNull(domainResourceId),
                tls_certificate_resource_id: numberOrNull(tlsCertificateId),
                url: url.trim(),
                role,
                is_primary: isPrimary,
                redirects_to: redirectsTo.trim(),
            };
        } else if (type === "domain") {
            payload = {
                ...common,
                domain_name: domainName.trim(),
                registrar_account_resource_id: numberOrNull(registrarAccountId),
                provider_domain_id: providerDomainId.trim(),
                status: domainStatus,
                registered_on: registeredOn || null,
                expires_on: expiresOn || null,
                auto_renew: triStatePayload(autoRenew),
                transfer_lock_enabled: triStatePayload(transferLock),
                privacy_enabled: triStatePayload(privacyEnabled),
            };
        } else if (type === "dns_zone") {
            payload = {
                ...common,
                domain_resource_id: Number(domainResourceId),
                provider_account_resource_id: numberOrNull(dnsProviderId),
                zone_name: zoneName.trim(),
                provider_zone_id: providerZoneId.trim(),
                dnssec_enabled: triStatePayload(dnssecEnabled),
                is_primary: zonePrimary,
            };
        } else {
            payload = {
                ...common,
                provider_account_resource_id: numberOrNull(tlsProviderId),
                certificate_type: certificateType,
                issuer: issuer.trim(),
                subject_common_name: subjectCommonName.trim(),
                provider_certificate_id: providerCertificateId.trim(),
                serial_number: serialNumber.trim(),
                fingerprint_sha256: fingerprintSha256.trim(),
                issued_at: issuedAt || null,
                expires_at: tlsExpiresAt || null,
                auto_renew: triStatePayload(tlsAutoRenew),
            };
        }

        try {
            setIsSaving(true);
            setError(null);
            const baseEndpoint = `${API_URL}/api/admin/infrastructure/${ENDPOINTS[type]}`;
            const saved = (await fetchAPI(
                isEditing ? `${baseEndpoint}/${editResourceId}` : baseEndpoint,
                {
                    method: isEditing ? "PUT" : "POST",
                    body: JSON.stringify(payload),
                },
            )) as { resource_id: number };
            if (isEditing) onSaved?.();
            else onCreated?.(saved.resource_id);
        } catch (saveError) {
            setError(
                saveError instanceof Error
                    ? saveError.message
                    : "Unable to save this web or domain resource.",
            );
        } finally {
            setIsSaving(false);
        }
    }

    if (isLoading || !options) {
        return (
            <DataLoading label="Loading web and domain infrastructure options..." />
        );
    }

    return (
        <form className="space-y-6" onSubmit={submit}>
            <PageHeader
                eyebrow="Structured infrastructure"
                title={`${isEditing ? "Edit" : "Add"} ${label(type)}`}
                description="Store web, DNS and TLS operational metadata against the shared resource identity. Secrets and private-key material belong in the Credential Vault, not here."
            />

            {error ? <DataError message={error} /> : null}

            <Card className="space-y-5 p-5">
                <div className="grid gap-4 sm:grid-cols-2">
                    {!isEditing ? (
                        <label>
                            <FieldLabel>Resource type</FieldLabel>
                            <Select
                                value={type}
                                onChange={(event) =>
                                    setType(event.target.value as WebDomainType)
                                }
                            >
                                {allowedTypes.map((value) => (
                                    <option key={value} value={value}>
                                        {label(value)}
                                    </option>
                                ))}
                            </Select>
                        </label>
                    ) : null}
                    {!isEditing ? (
                        <label>
                            <FieldLabel>Ownership</FieldLabel>
                            <Select
                                value={ownership}
                                onChange={(event) =>
                                    setOwnership(event.target.value)
                                }
                            >
                                <option value="internal">ADB Internal</option>
                                <option value="client">Client-owned</option>
                            </Select>
                        </label>
                    ) : null}
                    {!isEditing && ownership === "client" ? (
                        <label>
                            <FieldLabel>Client</FieldLabel>
                            <Select
                                value={clientId}
                                onChange={(event) =>
                                    setClientId(event.target.value)
                                }
                            >
                                <option value="">Choose Client</option>
                                {options.clients.map((client) => (
                                    <option key={client.id} value={client.id}>
                                        {client.name}
                                    </option>
                                ))}
                            </Select>
                        </label>
                    ) : null}
                    <label>
                        <FieldLabel>Resource name</FieldLabel>
                        <Input
                            value={name}
                            onChange={(event) => setName(event.target.value)}
                            required
                        />
                    </label>
                    <label>
                        <FieldLabel>Lifecycle</FieldLabel>
                        <Select
                            value={lifecycle}
                            onChange={(event) =>
                                setLifecycle(event.target.value)
                            }
                        >
                            <option value="planned">Planned</option>
                            <option value="active">Active</option>
                            <option value="maintenance">Maintenance</option>
                            <option value="deprecated">Deprecated</option>
                            <option value="retired">Retired</option>
                            <option value="archived">Archived</option>
                        </Select>
                    </label>
                    <label>
                        <FieldLabel>Environment</FieldLabel>
                        <Select
                            value={environment}
                            onChange={(event) =>
                                setEnvironment(event.target.value)
                            }
                        >
                            <option value="production">Production</option>
                            <option value="staging">Staging</option>
                            <option value="development">Development</option>
                            <option value="testing">Testing</option>
                            <option value="shared">Shared</option>
                            <option value="not_applicable">
                                Not applicable
                            </option>
                        </Select>
                    </label>
                    <label>
                        <FieldLabel>Criticality</FieldLabel>
                        <Select
                            value={criticality}
                            onChange={(event) =>
                                setCriticality(event.target.value)
                            }
                        >
                            <option value="low">Low</option>
                            <option value="normal">Normal</option>
                            <option value="high">High</option>
                            <option value="critical">Critical</option>
                        </Select>
                    </label>
                </div>
                <label>
                    <FieldLabel>Description</FieldLabel>
                    <Textarea
                        value={description}
                        onChange={(event) => setDescription(event.target.value)}
                    />
                </label>
            </Card>

            {type === "website" ? (
                <Card className="space-y-5 p-5">
                    <h2 className="text-sm font-semibold text-white">
                        Website details
                    </h2>
                    <div className="grid gap-4 sm:grid-cols-2">
                        <label>
                            <FieldLabel>Website type</FieldLabel>
                            <Select
                                value={websiteType}
                                onChange={(event) =>
                                    setWebsiteType(event.target.value)
                                }
                            >
                                <option value="marketing">
                                    Marketing site
                                </option>
                                <option value="web_app">Web application</option>
                                <option value="ecommerce">E-commerce</option>
                                <option value="cms">CMS site</option>
                                <option value="portal">Portal</option>
                                <option value="static">Static site</option>
                                <option value="other">Other</option>
                            </Select>
                        </label>
                        <label>
                            <FieldLabel>Admin URL</FieldLabel>
                            <Input
                                type="url"
                                value={adminUrl}
                                onChange={(event) =>
                                    setAdminUrl(event.target.value)
                                }
                            />
                        </label>
                        <label>
                            <FieldLabel>CMS</FieldLabel>
                            <Input
                                value={cms}
                                onChange={(event) => setCms(event.target.value)}
                                placeholder="WordPress, Wagtail..."
                            />
                        </label>
                        <label>
                            <FieldLabel>CMS version</FieldLabel>
                            <Input
                                value={cmsVersion}
                                onChange={(event) =>
                                    setCmsVersion(event.target.value)
                                }
                            />
                        </label>
                        <ProviderSelect
                            label="Hosting provider account"
                            value={hostingProviderId}
                            onChange={setHostingProviderId}
                            options={providerAccounts}
                        />
                        <ProviderSelect
                            label="CDN provider account"
                            value={cdnProviderId}
                            onChange={setCdnProviderId}
                            options={providerAccounts}
                        />
                        <ProviderSelect
                            label="WAF provider account"
                            value={wafProviderId}
                            onChange={setWafProviderId}
                            options={providerAccounts}
                        />
                    </div>
                </Card>
            ) : null}

            {type === "website_endpoint" ? (
                <Card className="space-y-5 p-5">
                    <h2 className="text-sm font-semibold text-white">
                        Endpoint details
                    </h2>
                    <div className="grid gap-4 sm:grid-cols-2">
                        <label>
                            <FieldLabel>Website</FieldLabel>
                            <Select
                                value={websiteResourceId}
                                onChange={(event) =>
                                    setWebsiteResourceId(event.target.value)
                                }
                                required
                            >
                                <option value="">Choose Website</option>
                                {websites.map((website) => (
                                    <option
                                        key={website.resource_id}
                                        value={website.resource_id}
                                    >
                                        {website.name}
                                    </option>
                                ))}
                            </Select>
                        </label>
                        <label>
                            <FieldLabel>Application environment</FieldLabel>
                            <Select
                                value={applicationEnvironmentId}
                                onChange={(event) =>
                                    setApplicationEnvironmentId(
                                        event.target.value,
                                    )
                                }
                            >
                                <option value="">None</option>
                                {applicationEnvironments.map((item) => (
                                    <option
                                        key={item.resource_id}
                                        value={item.resource_id}
                                    >
                                        {item.application_name} · {item.name}
                                    </option>
                                ))}
                            </Select>
                        </label>
                        <label>
                            <FieldLabel>Domain</FieldLabel>
                            <Select
                                value={domainResourceId}
                                onChange={(event) =>
                                    setDomainResourceId(event.target.value)
                                }
                            >
                                <option value="">None</option>
                                {domains.map((domain) => (
                                    <option
                                        key={domain.resource_id}
                                        value={domain.resource_id}
                                    >
                                        {domain.domain_name}
                                    </option>
                                ))}
                            </Select>
                        </label>
                        <label>
                            <FieldLabel>TLS certificate</FieldLabel>
                            <Select
                                value={tlsCertificateId}
                                onChange={(event) =>
                                    setTlsCertificateId(event.target.value)
                                }
                            >
                                <option value="">None</option>
                                {certificates.map((certificate) => (
                                    <option
                                        key={certificate.resource_id}
                                        value={certificate.resource_id}
                                    >
                                        {certificate.name}
                                    </option>
                                ))}
                            </Select>
                        </label>
                        <label>
                            <FieldLabel>URL</FieldLabel>
                            <Input
                                type="url"
                                value={url}
                                onChange={(event) => setUrl(event.target.value)}
                                required
                            />
                        </label>
                        <label>
                            <FieldLabel>Role</FieldLabel>
                            <Select
                                value={role}
                                onChange={(event) =>
                                    setRole(event.target.value)
                                }
                            >
                                <option value="primary">Primary</option>
                                <option value="alias">Alias</option>
                                <option value="staging">Staging</option>
                                <option value="development">Development</option>
                                <option value="admin">Admin</option>
                                <option value="api">API</option>
                                <option value="health">Health</option>
                                <option value="other">Other</option>
                            </Select>
                        </label>
                        <label>
                            <FieldLabel>Redirect target</FieldLabel>
                            <Input
                                type="url"
                                value={redirectsTo}
                                onChange={(event) =>
                                    setRedirectsTo(event.target.value)
                                }
                            />
                        </label>
                        <label className="flex items-center gap-2 pt-6 text-sm text-slate-300">
                            <input
                                type="checkbox"
                                checked={isPrimary}
                                onChange={(event) =>
                                    setIsPrimary(event.target.checked)
                                }
                            />
                            Primary endpoint for this Website
                        </label>
                    </div>
                </Card>
            ) : null}

            {type === "domain" ? (
                <Card className="space-y-5 p-5">
                    <h2 className="text-sm font-semibold text-white">
                        Domain registration
                    </h2>
                    <div className="grid gap-4 sm:grid-cols-2">
                        <label>
                            <FieldLabel>Domain name</FieldLabel>
                            <Input
                                value={domainName}
                                onChange={(event) =>
                                    setDomainName(event.target.value)
                                }
                                placeholder="example.com"
                                required
                            />
                        </label>
                        <ProviderSelect
                            label="Registrar account"
                            value={registrarAccountId}
                            onChange={setRegistrarAccountId}
                            options={providerAccounts}
                        />
                        <label>
                            <FieldLabel>Provider domain ID</FieldLabel>
                            <Input
                                value={providerDomainId}
                                onChange={(event) =>
                                    setProviderDomainId(event.target.value)
                                }
                            />
                        </label>
                        <label>
                            <FieldLabel>Status</FieldLabel>
                            <Select
                                value={domainStatus}
                                onChange={(event) =>
                                    setDomainStatus(event.target.value)
                                }
                            >
                                <option value="active">Active</option>
                                <option value="pending">Pending</option>
                                <option value="transferring">
                                    Transferring
                                </option>
                                <option value="expired">Expired</option>
                                <option value="cancelled">Cancelled</option>
                                <option value="unknown">Unknown</option>
                            </Select>
                        </label>
                        <label>
                            <FieldLabel>Registered on</FieldLabel>
                            <Input
                                type="date"
                                value={registeredOn}
                                onChange={(event) =>
                                    setRegisteredOn(event.target.value)
                                }
                            />
                        </label>
                        <label>
                            <FieldLabel>Expires on</FieldLabel>
                            <Input
                                type="date"
                                value={expiresOn}
                                onChange={(event) =>
                                    setExpiresOn(event.target.value)
                                }
                            />
                        </label>
                        <TriStateSelect
                            label="Auto-renew"
                            value={autoRenew}
                            onChange={setAutoRenew}
                        />
                        <TriStateSelect
                            label="Transfer lock"
                            value={transferLock}
                            onChange={setTransferLock}
                        />
                        <TriStateSelect
                            label="WHOIS privacy"
                            value={privacyEnabled}
                            onChange={setPrivacyEnabled}
                        />
                    </div>
                </Card>
            ) : null}

            {type === "dns_zone" ? (
                <Card className="space-y-5 p-5">
                    <h2 className="text-sm font-semibold text-white">
                        DNS zone
                    </h2>
                    <div className="grid gap-4 sm:grid-cols-2">
                        <label>
                            <FieldLabel>Domain</FieldLabel>
                            <Select
                                value={domainResourceId}
                                onChange={(event) =>
                                    setDomainResourceId(event.target.value)
                                }
                                required
                            >
                                <option value="">Choose Domain</option>
                                {domains.map((domain) => (
                                    <option
                                        key={domain.resource_id}
                                        value={domain.resource_id}
                                    >
                                        {domain.domain_name}
                                    </option>
                                ))}
                            </Select>
                        </label>
                        <ProviderSelect
                            label="DNS provider account"
                            value={dnsProviderId}
                            onChange={setDnsProviderId}
                            options={providerAccounts}
                        />
                        <label>
                            <FieldLabel>Zone name</FieldLabel>
                            <Input
                                value={zoneName}
                                onChange={(event) =>
                                    setZoneName(event.target.value)
                                }
                                placeholder="example.com"
                                required
                            />
                        </label>
                        <label>
                            <FieldLabel>Provider zone ID</FieldLabel>
                            <Input
                                value={providerZoneId}
                                onChange={(event) =>
                                    setProviderZoneId(event.target.value)
                                }
                            />
                        </label>
                        <TriStateSelect
                            label="DNSSEC"
                            value={dnssecEnabled}
                            onChange={setDnssecEnabled}
                        />
                        <label className="flex items-center gap-2 pt-6 text-sm text-slate-300">
                            <input
                                type="checkbox"
                                checked={zonePrimary}
                                onChange={(event) =>
                                    setZonePrimary(event.target.checked)
                                }
                            />
                            Primary authoritative zone
                        </label>
                    </div>
                </Card>
            ) : null}

            {type === "tls_certificate" ? (
                <Card className="space-y-5 p-5">
                    <h2 className="text-sm font-semibold text-white">
                        TLS certificate metadata
                    </h2>
                    <p className="text-xs leading-5 text-slate-500">
                        Do not paste a certificate private key, ACME account
                        key, password or provider token here.
                    </p>
                    <div className="grid gap-4 sm:grid-cols-2">
                        <ProviderSelect
                            label="TLS provider account"
                            value={tlsProviderId}
                            onChange={setTlsProviderId}
                            options={providerAccounts}
                        />
                        <label>
                            <FieldLabel>Certificate type</FieldLabel>
                            <Select
                                value={certificateType}
                                onChange={(event) =>
                                    setCertificateType(event.target.value)
                                }
                            >
                                <option value="managed">Managed</option>
                                <option value="acme">ACME</option>
                                <option value="imported">Imported</option>
                                <option value="self_signed">Self-signed</option>
                                <option value="other">Other</option>
                            </Select>
                        </label>
                        <label>
                            <FieldLabel>Issuer</FieldLabel>
                            <Input
                                value={issuer}
                                onChange={(event) =>
                                    setIssuer(event.target.value)
                                }
                            />
                        </label>
                        <label>
                            <FieldLabel>Subject common name</FieldLabel>
                            <Input
                                value={subjectCommonName}
                                onChange={(event) =>
                                    setSubjectCommonName(event.target.value)
                                }
                            />
                        </label>
                        <label>
                            <FieldLabel>Provider certificate ID</FieldLabel>
                            <Input
                                value={providerCertificateId}
                                onChange={(event) =>
                                    setProviderCertificateId(event.target.value)
                                }
                            />
                        </label>
                        <label>
                            <FieldLabel>Serial number</FieldLabel>
                            <Input
                                value={serialNumber}
                                onChange={(event) =>
                                    setSerialNumber(event.target.value)
                                }
                            />
                        </label>
                        <label className="sm:col-span-2">
                            <FieldLabel>SHA-256 fingerprint</FieldLabel>
                            <Input
                                value={fingerprintSha256}
                                onChange={(event) =>
                                    setFingerprintSha256(event.target.value)
                                }
                            />
                        </label>
                        <label>
                            <FieldLabel>Issued at</FieldLabel>
                            <Input
                                value={issuedAt}
                                onChange={(event) =>
                                    setIssuedAt(event.target.value)
                                }
                                placeholder="2026-08-26T12:00:00+00:00"
                            />
                        </label>
                        <label>
                            <FieldLabel>Expires at</FieldLabel>
                            <Input
                                value={tlsExpiresAt}
                                onChange={(event) =>
                                    setTlsExpiresAt(event.target.value)
                                }
                                placeholder="2026-11-24T12:00:00+00:00"
                            />
                        </label>
                        <TriStateSelect
                            label="Auto-renew"
                            value={tlsAutoRenew}
                            onChange={setTlsAutoRenew}
                        />
                    </div>
                </Card>
            ) : null}

            <div className="flex justify-end gap-3">
                <Button
                    type="button"
                    variant="secondary"
                    onClick={onCancel}
                    disabled={isSaving}
                >
                    Cancel
                </Button>
                <Button type="submit" disabled={isSaving}>
                    {isSaving
                        ? "Saving..."
                        : isEditing
                          ? "Save changes"
                          : `Create ${label(type)}`}
                </Button>
            </div>
        </form>
    );
}

function ProviderSelect({
    label: fieldLabel,
    value,
    onChange,
    options,
}: {
    label: string;
    value: string;
    onChange: (value: string) => void;
    options: ProviderAccountOption[];
}) {
    return (
        <label>
            <FieldLabel>{fieldLabel}</FieldLabel>
            <Select
                value={value}
                onChange={(event) => onChange(event.target.value)}
            >
                <option value="">None</option>
                {options.map((option) => (
                    <option key={option.resource_id} value={option.resource_id}>
                        {option.name} · {option.provider_name}
                    </option>
                ))}
            </Select>
        </label>
    );
}

function TriStateSelect({
    label: fieldLabel,
    value,
    onChange,
}: {
    label: string;
    value: string;
    onChange: (value: string) => void;
}) {
    return (
        <label>
            <FieldLabel>{fieldLabel}</FieldLabel>
            <Select
                value={value}
                onChange={(event) => onChange(event.target.value)}
            >
                <option value="">Unknown / not recorded</option>
                <option value="true">Yes</option>
                <option value="false">No</option>
            </Select>
        </label>
    );
}
