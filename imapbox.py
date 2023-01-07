import imaplib
import mailbox
import os
import re
import time

MESSAGE_HEAD_RE = re.compile(r"(\d+) \(([^\s]+) {(\d+)}$")


def handle_response(response):
    status, data = response
    if status != "OK":
        raise Exception(data[0])

    # print(data)

    return data


class IMAPMessage(mailbox.Message):
    """A Mailbox Message class that uses an IMAPClient object to fetch the message"""

    def __init__(self, message) -> None:
        super().__init__(message)

    @classmethod
    def from_uid(cls, uid, mailbox):
        _uid, message = next(mailbox.fetch(uid, "RFC822"))
        if _uid != uid:
            e = Exception("UID mismatch")
            e.add_note(f"Expected: {uid} Got: {_uid}")
            raise e

        return cls(message)


class IMAPMailbox(mailbox.Mailbox):
    def __init__(self, host, user, password, folder="INBOX"):
        self.host = host
        self.user = user
        self.password = password
        self.folder = folder

    def __enter__(self):
        self.__m = imaplib.IMAP4_SSL(self.host)
        self.__m.login(self.user, self.password)
        self.__m.select(self.folder)
        return self

    def __exit__(self, *args):
        self.__m.close()
        self.__m.logout()

    def __iter__(self):
        data = handle_response(self.__m.search(None, "ALL"))
        for uid in data[0].decode().split():
            yield IMAPMessage.from_uid(uid, self)

    def fetch(self, uids, what):
        messages = handle_response(self.__m.fetch(uids, what))

        for head, body in messages:
            uid, what, size = MESSAGE_HEAD_RE.match(head.decode()).groups()
            if size != str(len(body)):
                raise Exception("Size mismatch")

            yield uid, body

    def list_folders(self):
        """List all folders in the mailbox"""

        return self.__m.list()

    def get_folder(self, folder):
        self.__m.select(folder)
        return self

    def search(self, **kwargs) -> list:
        """Search for messages matching the query"""

        # remove underscores from keys
        kwargs = {key.lstrip("_"): value for key, value in kwargs.items()}
        # create a list of key value pairs
        query = [f'{key.upper()} "{value}"' for key, value in kwargs.items()]
        # join the list with spaces
        full_query = " ".join(query)

        return self.__search(full_query)

    def __search(self, query) -> list:
        """Search for messages matching the query"""
        data = handle_response(self.__m.search(None, query))

        return data[0].decode().split()