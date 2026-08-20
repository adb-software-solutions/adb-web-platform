import { CalendarWorkspace } from "@/app/(admin)/admin/calendar/CalendarWorkspace";
import { Container, PageHeader } from "@/components/ui";

export const metadata = {
    title: "Calendar",
};

export default function CalendarPage() {
    return (
        <Container className="py-8">
            <PageHeader
                title="Calendar"
                description="See dated work across ADB in one place, including Task schedules and Project delivery windows."
            />
            <div className="mt-6">
                <CalendarWorkspace />
            </div>
        </Container>
    );
}
