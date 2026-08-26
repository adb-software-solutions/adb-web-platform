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

type SpecialistType = "server" | "network" | "subnet";

interface ClientOption {
    id: number;
    name: string;
}

interface ProviderAccountOption {
    resource_id: number;
    name: string;
    provider_name: string;
    ownership_type: string;
    client_id: number | null;
    client_name: string | null;
}

interface NetworkOption {
    resource_id: number;
    name: string;
    ownership_type: string;
    client_id: number | null;
    client_name: string | null;
}

interface SubnetOption {
    resource_id: number;
    name: string;
    network_resource_id: number;
    cidr: string;
    ownership_type: string;
    client_id: number | null;
    client_name: string | null;
}

interface SpecialistOptions {
    clients: ClientOption[];
    provider_accounts: ProviderAccountOption[];
    networks: NetworkOption[];
    subnets: SubnetOption[];
}

interface CreateResult {
    resource_id: number;
}

interface StructuredInfrastructureFormProps {
    allowedTypes: SpecialistType[];
    onCancel: () => void;
    onCreated: (resourceId: number) => void;
}

function numberOrNull(value: string): number | null {
    const trimmed = value.trim();
    return trimmed ? Number(trimmed) : null;
}

function label(value: SpecialistType): string {
    return value === "server" ? "Server" : value === "network" ? "Network" : "Subnet";
}

export function StructuredInfrastructureForm({
    allowedTypes,
    onCancel,
    onCreated,
}: StructuredInfrastructureFormProps) {
    const [options, setOptions] = useState<SpecialistOptions | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [type, setType] = useState<SpecialistType>(allowedTypes[0] ?? "server");
    const [ownership, setOwnership] = useState("internal");
    const [clientId, setClientId] = useState("");
    const [name, setName] = useState("");
    const [environment, setEnvironment] = useState("production");
    const [criticality, setCriticality] = useState("normal");
    const [description, setDescription] = useState("");

    const [hostname, setHostname] = useState("");
    const [fqdn, setFqdn] = useState("");
    const [purpose, setPurpose] = useState("");
    const [role, setRole] = useState("");
    const [computeType, setComputeType] = useState("cloud_vm");
    const [architecture, setArchitecture] = useState("");
    const [cpuModel, setCpuModel] = useState("");
    const [cpuCores, setCpuCores] = useState("");
    const [ramMb, setRamMb] = useState("");
    const [rootDiskGb, setRootDiskGb] = useState("");
    const [osFamily, setOsFamily] = useState("linux");
    const [distribution, setDistribution] = useState("");
    const [osVersion, setOsVersion] = useState("");
    const [providerAccountId, setProviderAccountId] = useState("");
    const [providerResourceId, setProviderResourceId] = useState("");
    const [region, setRegion] = useState("");
    const [zone, setZone] = useState("");
    const [sshPort, setSshPort] = useState("22");
    const [timezone, setTimezone] = useState("");

    const [networkType, setNetworkType] = useState("vpc");
    const [cidr, setCidr] = useState("");
    const [gateway, setGateway] = useState("");
    const [vlanId, setVlanId] = useState("");
    const [dnsServers, setDnsServers] = useState("");

    const [networkResourceId, setNetworkResourceId] = useState("");
    const [availabilityZone, setAvailabilityZone] = useState("");

    useEffect(() => {
        let active = true;
        async function loadOptions() {
            try {
                setIsLoading(true);
                setError(null);
                const result = (await fetchAPI(
                    `${API_URL}/api/admin/infrastructure/specialist-options`,
                )) as SpecialistOptions;
                if (active) setOptions(result);
            } catch (loadError) {
                if (active) {
                    setError(
                        loadError instanceof Error
                            ? loadError.message
                            : "Unable to load infrastructure options.",
                    );
                }
            } finally {
                if (active) setIsLoading(false);
            }
        }
        void loadOptions();
        return () => {
            active = false;
        };
    }, []);

    useEffect(() => {
        if (ownership === "internal") setClientId("");
        setProviderAccountId("");
        setNetworkResourceId("");
    }, [ownership, clientId]);

    const providerAccounts = useMemo(
        () =>
            options?.provider_accounts.filter(
                (provider) =>
                    ownership === "internal"
                        ? provider.ownership_type === "internal"
                        : provider.ownership_type === "internal" ||
                          provider.client_id === Number(clientId),
            ) ?? [],
        [clientId, options, ownership],
    );

    const networks = useMemo(
        () =>
            options?.networks.filter(
                (network) =>
                    ownership === "internal"
                        ? network.ownership_type === "internal"
                        : network.ownership_type === "internal" ||
                          network.client_id === Number(clientId),
            ) ?? [],
        [clientId, options, ownership],
    );

    async function submit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        if (!name.trim()) {
            setError("Enter a resource name.");
            return;
        }
        if (ownership === "client" && !clientId) {
            setError("Choose the Client that owns this resource.");
            return;
        }
        if (type === "server" && !hostname.trim()) {
            setError("Enter the server hostname.");
            return;
        }
        if (type === "subnet" && !networkResourceId) {
            setError("Choose the parent network.");
            return;
        }
        if ((type === "network" || type === "subnet") && !cidr.trim()) {
            setError("Enter the CIDR for this network resource.");
            return;
        }

        const common = {
            ownership_type: ownership,
            client_id: ownership === "client" ? Number(clientId) : null,
            name: name.trim(),
            lifecycle_status: "active",
            environment,
            criticality,
            description: description.trim(),
        };
        let payload: Record<string, unknown>;
        if (type === "server") {
            payload = {
                ...common,
                hostname: hostname.trim(),
                fqdn: fqdn.trim(),
                purpose: purpose.trim(),
                role: role.trim(),
                compute_type: computeType,
                architecture: architecture.trim(),
                cpu_model: cpuModel.trim(),
                cpu_cores: numberOrNull(cpuCores),
                ram_mb: numberOrNull(ramMb),
                root_disk_gb: numberOrNull(rootDiskGb),
                os_family: osFamily,
                distribution: distribution.trim(),
                os_version: osVersion.trim(),
                provider_account_resource_id: numberOrNull(providerAccountId),
                provider_resource_id: providerResourceId.trim(),
                region: region.trim(),
                zone: zone.trim(),
                ssh_port: numberOrNull(sshPort),
                timezone: timezone.trim(),
            };
        } else if (type === "network") {
            payload = {
                ...common,
                network_type: networkType,
                provider_account_resource_id: numberOrNull(providerAccountId),
                provider_network_id: providerResourceId.trim(),
                cidr: cidr.trim(),
                gateway: gateway.trim() || null,
                region: region.trim(),
                vlan_id: numberOrNull(vlanId),
                dns_servers: dnsServers
                    .split(/[\n,]+/)
                    .map((value) => value.trim())
                    .filter(Boolean),
            };
        } else {
            payload = {
                ...common,
                network_resource_id: Number(networkResourceId),
                cidr: cidr.trim(),
                gateway: gateway.trim() || null,
                vlan_id: numberOrNull(vlanId),
                availability_zone: availabilityZone.trim(),
                purpose: purpose.trim(),
            };
        }

        try {
            setIsSaving(true);
            setError(null);
            const created = (await fetchAPI(
                `${API_URL}/api/admin/infrastructure/${type === "subnet" ? "subnets" : `${type}s`}`,
                {
                    method: "POST",
                    body: JSON.stringify(payload),
                },
            )) as CreateResult;
            onCreated(created.resource_id);
        } catch (saveError) {
            setError(
                saveError instanceof Error
                    ? saveError.message
                    : "Unable to create this infrastructure resource.",
            );
        } finally {
            setIsSaving(false);
        }
    }

    if (isLoading && !options) {
        return <DataLoading label="Loading infrastructure options..." />;
    }
    if (!options && error) {
        return <DataError message={error} />;
    }

    return (
        <form className="space-y-6" onSubmit={submit}>
            <PageHeader
                eyebrow="Structured infrastructure"
                title={`Add ${label(type).toLowerCase()}`}
                description="Create a native typed resource. Credentials remain separate Vault records linked after creation."
            />

            <Card className="space-y-4 p-5">
                <h2 className="text-sm font-semibold text-white">Resource identity</h2>
                <div className="grid gap-4 md:grid-cols-2">
                    <label className="space-y-2 text-xs text-slate-400">
                        Resource type
                        <Select
                            value={type}
                            onChange={(event) => setType(event.target.value as SpecialistType)}
                            disabled={isSaving}
                        >
                            {allowedTypes.map((value) => (
                                <option key={value} value={value}>
                                    {label(value)}
                                </option>
                            ))}
                        </Select>
                    </label>
                    <label className="space-y-2 text-xs text-slate-400">
                        Ownership
                        <Select
                            value={ownership}
                            onChange={(event) => setOwnership(event.target.value)}
                            disabled={isSaving}
                        >
                            <option value="internal">ADB Internal</option>
                            <option value="client">Client-owned</option>
                        </Select>
                    </label>
                    {ownership === "client" ? (
                        <label className="space-y-2 text-xs text-slate-400 md:col-span-2">
                            Client
                            <Select
                                value={clientId}
                                onChange={(event) => setClientId(event.target.value)}
                                disabled={isSaving}
                            >
                                <option value="">Choose client</option>
                                {options?.clients.map((client) => (
                                    <option key={client.id} value={client.id}>
                                        {client.name}
                                    </option>
                                ))}
                            </Select>
                        </label>
                    ) : null}
                    <label className="space-y-2 text-xs text-slate-400 md:col-span-2">
                        Name
                        <Input
                            value={name}
                            onChange={(event) => setName(event.target.value)}
                            placeholder="e.g. ADB LON Web 01"
                            disabled={isSaving}
                        />
                    </label>
                    <label className="space-y-2 text-xs text-slate-400">
                        Environment
                        <Select
                            value={environment}
                            onChange={(event) => setEnvironment(event.target.value)}
                            disabled={isSaving}
                        >
                            <option value="production">Production</option>
                            <option value="staging">Staging</option>
                            <option value="development">Development</option>
                            <option value="testing">Testing</option>
                            <option value="shared">Shared</option>
                            <option value="not_applicable">Not applicable</option>
                        </Select>
                    </label>
                    <label className="space-y-2 text-xs text-slate-400">
                        Criticality
                        <Select
                            value={criticality}
                            onChange={(event) => setCriticality(event.target.value)}
                            disabled={isSaving}
                        >
                            <option value="low">Low</option>
                            <option value="normal">Normal</option>
                            <option value="high">High</option>
                            <option value="critical">Critical</option>
                        </Select>
                    </label>
                    <label className="space-y-2 text-xs text-slate-400 md:col-span-2">
                        Description
                        <Textarea
                            value={description}
                            onChange={(event) => setDescription(event.target.value)}
                            rows={3}
                            disabled={isSaving}
                        />
                    </label>
                </div>
            </Card>

            {type === "server" ? (
                <Card className="space-y-4 p-5">
                    <h2 className="text-sm font-semibold text-white">Server details</h2>
                    <div className="grid gap-4 md:grid-cols-2">
                        <label className="space-y-2 text-xs text-slate-400">
                            Hostname
                            <Input value={hostname} onChange={(event) => setHostname(event.target.value)} disabled={isSaving} />
                        </label>
                        <label className="space-y-2 text-xs text-slate-400">
                            FQDN
                            <Input value={fqdn} onChange={(event) => setFqdn(event.target.value)} disabled={isSaving} />
                        </label>
                        <label className="space-y-2 text-xs text-slate-400">
                            Purpose
                            <Input value={purpose} onChange={(event) => setPurpose(event.target.value)} disabled={isSaving} />
                        </label>
                        <label className="space-y-2 text-xs text-slate-400">
                            Role
                            <Input value={role} onChange={(event) => setRole(event.target.value)} disabled={isSaving} />
                        </label>
                        <label className="space-y-2 text-xs text-slate-400">
                            Compute type
                            <Select value={computeType} onChange={(event) => setComputeType(event.target.value)} disabled={isSaving}>
                                <option value="cloud_vm">Cloud VM</option>
                                <option value="vps">VPS</option>
                                <option value="virtual_machine">Virtual machine</option>
                                <option value="dedicated">Dedicated</option>
                                <option value="bare_metal">Bare metal</option>
                                <option value="hypervisor">Hypervisor</option>
                                <option value="container_host">Container host</option>
                                <option value="nas">NAS</option>
                                <option value="other">Other</option>
                            </Select>
                        </label>
                        <label className="space-y-2 text-xs text-slate-400">
                            Architecture
                            <Input value={architecture} onChange={(event) => setArchitecture(event.target.value)} placeholder="x86_64 / arm64" disabled={isSaving} />
                        </label>
                        <label className="space-y-2 text-xs text-slate-400 md:col-span-2">
                            Provider account
                            <Select value={providerAccountId} onChange={(event) => setProviderAccountId(event.target.value)} disabled={isSaving}>
                                <option value="">No provider account</option>
                                {providerAccounts.map((provider) => (
                                    <option key={provider.resource_id} value={provider.resource_id}>
                                        {provider.name} · {provider.provider_name}
                                    </option>
                                ))}
                            </Select>
                        </label>
                        <label className="space-y-2 text-xs text-slate-400">
                            Provider resource ID
                            <Input value={providerResourceId} onChange={(event) => setProviderResourceId(event.target.value)} disabled={isSaving} />
                        </label>
                        <label className="space-y-2 text-xs text-slate-400">
                            Region
                            <Input value={region} onChange={(event) => setRegion(event.target.value)} disabled={isSaving} />
                        </label>
                        <label className="space-y-2 text-xs text-slate-400">
                            Zone
                            <Input value={zone} onChange={(event) => setZone(event.target.value)} disabled={isSaving} />
                        </label>
                        <label className="space-y-2 text-xs text-slate-400">
                            CPU model
                            <Input value={cpuModel} onChange={(event) => setCpuModel(event.target.value)} disabled={isSaving} />
                        </label>
                        <label className="space-y-2 text-xs text-slate-400">
                            CPU cores
                            <Input type="number" min="1" value={cpuCores} onChange={(event) => setCpuCores(event.target.value)} disabled={isSaving} />
                        </label>
                        <label className="space-y-2 text-xs text-slate-400">
                            RAM (MB)
                            <Input type="number" min="1" value={ramMb} onChange={(event) => setRamMb(event.target.value)} disabled={isSaving} />
                        </label>
                        <label className="space-y-2 text-xs text-slate-400">
                            Root disk (GB)
                            <Input type="number" min="1" value={rootDiskGb} onChange={(event) => setRootDiskGb(event.target.value)} disabled={isSaving} />
                        </label>
                        <label className="space-y-2 text-xs text-slate-400">
                            OS family
                            <Select value={osFamily} onChange={(event) => setOsFamily(event.target.value)} disabled={isSaving}>
                                <option value="linux">Linux</option>
                                <option value="windows">Windows</option>
                                <option value="bsd">BSD</option>
                                <option value="appliance">Appliance</option>
                                <option value="other">Other</option>
                            </Select>
                        </label>
                        <label className="space-y-2 text-xs text-slate-400">
                            Distribution
                            <Input value={distribution} onChange={(event) => setDistribution(event.target.value)} placeholder="Ubuntu" disabled={isSaving} />
                        </label>
                        <label className="space-y-2 text-xs text-slate-400">
                            OS version
                            <Input value={osVersion} onChange={(event) => setOsVersion(event.target.value)} disabled={isSaving} />
                        </label>
                        <label className="space-y-2 text-xs text-slate-400">
                            SSH port
                            <Input type="number" min="1" max="65535" value={sshPort} onChange={(event) => setSshPort(event.target.value)} disabled={isSaving} />
                        </label>
                        <label className="space-y-2 text-xs text-slate-400">
                            Timezone
                            <Input value={timezone} onChange={(event) => setTimezone(event.target.value)} placeholder="Europe/London" disabled={isSaving} />
                        </label>
                    </div>
                </Card>
            ) : null}

            {type === "network" ? (
                <Card className="space-y-4 p-5">
                    <h2 className="text-sm font-semibold text-white">Network details</h2>
                    <div className="grid gap-4 md:grid-cols-2">
                        <label className="space-y-2 text-xs text-slate-400">
                            Network type
                            <Select value={networkType} onChange={(event) => setNetworkType(event.target.value)} disabled={isSaving}>
                                <option value="vpc">VPC</option>
                                <option value="lan">LAN</option>
                                <option value="vlan">VLAN</option>
                                <option value="vpn">VPN</option>
                                <option value="overlay">Overlay</option>
                                <option value="public">Public</option>
                                <option value="other">Other</option>
                            </Select>
                        </label>
                        <label className="space-y-2 text-xs text-slate-400">
                            Provider account
                            <Select value={providerAccountId} onChange={(event) => setProviderAccountId(event.target.value)} disabled={isSaving}>
                                <option value="">No provider account</option>
                                {providerAccounts.map((provider) => (
                                    <option key={provider.resource_id} value={provider.resource_id}>
                                        {provider.name} · {provider.provider_name}
                                    </option>
                                ))}
                            </Select>
                        </label>
                        <label className="space-y-2 text-xs text-slate-400">
                            CIDR
                            <Input value={cidr} onChange={(event) => setCidr(event.target.value)} placeholder="10.42.0.0/16" disabled={isSaving} />
                        </label>
                        <label className="space-y-2 text-xs text-slate-400">
                            Gateway
                            <Input value={gateway} onChange={(event) => setGateway(event.target.value)} disabled={isSaving} />
                        </label>
                        <label className="space-y-2 text-xs text-slate-400">
                            Provider network ID
                            <Input value={providerResourceId} onChange={(event) => setProviderResourceId(event.target.value)} disabled={isSaving} />
                        </label>
                        <label className="space-y-2 text-xs text-slate-400">
                            Region
                            <Input value={region} onChange={(event) => setRegion(event.target.value)} disabled={isSaving} />
                        </label>
                        <label className="space-y-2 text-xs text-slate-400">
                            VLAN ID
                            <Input type="number" min="1" max="4094" value={vlanId} onChange={(event) => setVlanId(event.target.value)} disabled={isSaving} />
                        </label>
                        <label className="space-y-2 text-xs text-slate-400 md:col-span-2">
                            DNS servers
                            <Textarea value={dnsServers} onChange={(event) => setDnsServers(event.target.value)} placeholder="1.1.1.1, 1.0.0.1" rows={2} disabled={isSaving} />
                        </label>
                    </div>
                </Card>
            ) : null}

            {type === "subnet" ? (
                <Card className="space-y-4 p-5">
                    <h2 className="text-sm font-semibold text-white">Subnet details</h2>
                    <div className="grid gap-4 md:grid-cols-2">
                        <label className="space-y-2 text-xs text-slate-400 md:col-span-2">
                            Parent network
                            <Select value={networkResourceId} onChange={(event) => setNetworkResourceId(event.target.value)} disabled={isSaving}>
                                <option value="">Choose network</option>
                                {networks.map((network) => (
                                    <option key={network.resource_id} value={network.resource_id}>
                                        {network.name} · {network.client_name || "ADB Internal"}
                                    </option>
                                ))}
                            </Select>
                        </label>
                        <label className="space-y-2 text-xs text-slate-400">
                            CIDR
                            <Input value={cidr} onChange={(event) => setCidr(event.target.value)} placeholder="10.42.10.0/24" disabled={isSaving} />
                        </label>
                        <label className="space-y-2 text-xs text-slate-400">
                            Gateway
                            <Input value={gateway} onChange={(event) => setGateway(event.target.value)} disabled={isSaving} />
                        </label>
                        <label className="space-y-2 text-xs text-slate-400">
                            VLAN ID
                            <Input type="number" min="1" max="4094" value={vlanId} onChange={(event) => setVlanId(event.target.value)} disabled={isSaving} />
                        </label>
                        <label className="space-y-2 text-xs text-slate-400">
                            Availability zone
                            <Input value={availabilityZone} onChange={(event) => setAvailabilityZone(event.target.value)} disabled={isSaving} />
                        </label>
                        <label className="space-y-2 text-xs text-slate-400 md:col-span-2">
                            Purpose
                            <Input value={purpose} onChange={(event) => setPurpose(event.target.value)} disabled={isSaving} />
                        </label>
                    </div>
                </Card>
            ) : null}

            {error ? <p className="text-sm text-red-300">{error}</p> : null}
            <div className="flex justify-end gap-2">
                <Button type="button" variant="ghost" onClick={onCancel} disabled={isSaving}>
                    Cancel
                </Button>
                <Button type="submit" disabled={isSaving || allowedTypes.length === 0}>
                    {isSaving ? "Creating..." : `Create ${label(type).toLowerCase()}`}
                </Button>
            </div>
        </form>
    );
}
