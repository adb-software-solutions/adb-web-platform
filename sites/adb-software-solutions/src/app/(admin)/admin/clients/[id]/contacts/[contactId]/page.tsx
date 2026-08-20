import { Container } from "@/components/ui";
import { ContactWorkspace } from "./ContactWorkspace";

export const metadata = {
    title: "Client Contact",
};

export default async function ClientContactPage({
    params,
}: {
    params: Promise<{ id: string; contactId: string }>;
}) {
    const { id, contactId } = await params;

    return (
        <Container className="py-8">
            <ContactWorkspace clientId={Number(id)} contactId={Number(contactId)} />
        </Container>
    );
}
