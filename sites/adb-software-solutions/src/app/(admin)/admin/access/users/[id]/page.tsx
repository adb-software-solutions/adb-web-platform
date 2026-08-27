import { Container, PageHeader } from "@/components/ui";
import { StaffAccessEditor } from "../../StaffAccessEditor";

export default async function StaffUserAccessPage({
    params,
}: {
    params: Promise<{ id: string }>;
}) {
    const { id } = await params;

    return (
        <Container className="py-8">
            <PageHeader
                eyebrow="Users & Access"
                title="Staff access"
                description="Review effective business capabilities and administer Client/Ticket Queue scope for this staff identity."
            />
            <div className="mt-6">
                <StaffAccessEditor userId={id} />
            </div>
        </Container>
    );
}
