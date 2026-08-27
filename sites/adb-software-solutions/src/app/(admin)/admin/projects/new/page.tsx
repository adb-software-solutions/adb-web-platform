import { Card, Container, PageHeader } from "@/components/ui";
import { ProjectForm } from "../ProjectForm";

export const metadata = {
    title: "New Project",
};

export default async function NewProjectPage({
    searchParams,
}: {
    searchParams: Promise<{ client_id?: string }>;
}) {
    const { client_id: clientIdParam } = await searchParams;
    const parsedClientId = clientIdParam ? Number(clientIdParam) : undefined;
    const initialClientId =
        parsedClientId && Number.isInteger(parsedClientId) && parsedClientId > 0
            ? parsedClientId
            : undefined;

    return (
        <Container className="py-8">
            <PageHeader
                eyebrow="Projects"
                title="Create project"
                description="Create a client delivery project or an internal ADB project."
            />
            <Card className="mt-6 p-6">
                <ProjectForm initialClientId={initialClientId} />
            </Card>
        </Container>
    );
}
