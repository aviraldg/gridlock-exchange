__author__ = 'aviraldg'

from google.appengine.api import mail
from google.appengine.api.app_identity import get_application_id
import re

def notify(conversation, message, sender):
    to = [p.email for p in conversation.participants if p != sender]
    sender = '%s <conversation-%s@%s.appspotmail.com>' % (sender.name, conversation.key.id(), get_application_id())
    if to:
        mail.send_mail(sender=sender, to=to, subject=conversation.readable_subject, body=message.content)

CONV_ADDRESS_RE = re.compile(r'\<conversation-(.+)@.+\>')
ADDRESS_RE = re.compile(r'\<(.+)\>')

def handle_inbound_email(address, email):
    from .models import Conversation, Message

    if '<' not in address:
        address = '<%s>' % address.strip()
    conv_id = CONV_ADDRESS_RE.findall(address)[0]
    conversation = Conversation.get_by_id(long(conv_id))
    if not conversation:
        return False
    sender_email = ADDRESS_RE.findall(email.sender)[0] if '<' in email.sender else email.sender.strip()
    participants = conversation.participants
    sender = None

    for participant in participants:
        if participant.email == sender_email:
            sender = participant
            break

    if not sender:
        return False

    Message.send(sender, participants, conversation.subject,
                 email.bodies('text/plain').next()[1].decode().replace('\n', '<br>'))

    return True

