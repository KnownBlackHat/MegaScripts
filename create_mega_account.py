import re
import sys
import random
import string
import csv

import asyncio
import httpx

PASSWORD = "1235678"


class MegaAccount:
    def __init__(self, password: str, httpx_client: httpx.AsyncClient):
        self.name = ""
        self.password = password
        self.client = httpx_client

    def find_url(self, string):
        regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
        url = re.findall(regex, string)
        return [x[0] for x in url]

    async def register(self):
        mail_req = (
            await self.client.get(
                "https://api.guerrillamail.com/ajax.php?f=get_email_address&lang=en"
            )
        ).json()
        self.email = mail_req.get("email_addr")
        self.email_token = mail_req.get("sid_token")

        registration = await asyncio.create_subprocess_exec(
            "megatools",
            "reg",
            "--scripted",
            "--register",
            "--email",
            self.email,
            "--name",
            self.name,
            "--password",
            self.password,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        await registration.wait()
        if not registration.stdout:
            raise ValueError("No output found by commands")
        self.verify_command = str((await registration.stdout.read()).decode())

    async def verify(self):
        mail_id = None
        for _ in range(5):
            if mail_id is not None:
                break
            await asyncio.sleep(10)
            check_mail = (
                await self.client.get(
                    f"https://api.guerrillamail.com/ajax.php?f=get_email_list&offset=0&sid_token={self.email_token}"
                )
            ).json()
            for email in check_mail.get("list"):
                if "MEGA" in email.get("mail_subject"):
                    mail_id = email.get("mail_id")
                    break

        if mail_id is None:
            return
        view_mail = (
            await self.client.get(
                f"https://api.guerrillamail.com/ajax.php?f=fetch_email&email_id={mail_id}&sid_token={self.email_token}"
            )
        ).json()
        mail_body = view_mail.get("mail_body")
        links = self.find_url(mail_body)

        self.verify_command = self.verify_command.replace("@LINK@", links[2])

        verification = await asyncio.create_subprocess_exec(
            "megatools",
            *self.verify_command.split(" ")[1:],
            stdout=asyncio.subprocess.PIPE,
        )
        await verification.wait()
        if not verification.stdout:
            raise ValueError("No output found by commands")
        if "registered successfully!" in str(
            (await verification.stdout.read()).decode()
        ):
            print(f"[=] {self.email} - {self.password}")

            with open("accounts.csv", "a") as csvfile:
                csvwriter = csv.writer(csvfile)
                csvwriter.writerow([self.email, self.password, self.name, "-"])
        else:
            print("[x] Verification Failed!")

    async def __call__(self) -> None:
        self.name = "".join(random.choice(string.ascii_letters) for x in range(12))
        await self.register()
        print("[+] Registered Completed! Waiting for verification email...")
        await self.verify()


async def main():
    if len(sys.argv) == 2:
        number_account = int(sys.argv[1])
        async with httpx.AsyncClient() as client:
            tasks = (MegaAccount(PASSWORD, client)() for _ in range(number_account))
            await asyncio.gather(*tasks)

    else:
        print(f"Usage: python {sys.argv[0]} <Number of accounts to create>")


if __name__ == "__main__":
    asyncio.run(main())
