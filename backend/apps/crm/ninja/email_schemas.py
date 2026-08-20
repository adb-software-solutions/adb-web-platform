from ninja import Schema


class LeadMailboxOut(Schema):
    id: int
    email_address: str
    display_name: str
    brand_name: str
    purpose: str


class LeadEmailOptionsOut(Schema):
    can_email: bool
    mailboxes: list[LeadMailboxOut]


class LeadEmailIn(Schema):
    mailbox_id: int
    subject: str
    body_text: str


class LeadEmailOut(Schema):
    ticket_id: int
    ticket_reference: str
    message_id: int
    delivery_status: str
