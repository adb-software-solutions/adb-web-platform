import { Container, PageHeader } from "@/components/ui";
import { StaffAccessEditor } from "../StaffAccessEditor";

export default function InviteStaffUserPage() {
    return (
        <Container className="py-8">
            <PageHeader
                eyebrow="Users & Access"
                title="Invite staff user"
                description="Create a staff identity, configure least-privilege access and send a one-hour password-setup invitation."
            />
            <div className="mt-6">
                <StaffAccessEditor />
            </div>
        </Container>
    );
}
