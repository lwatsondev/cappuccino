#  This file is part of cappuccino.
#
#  cappuccino is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  cappuccino is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with cappuccino.  If not, see <https://www.gnu.org/licenses/>.

import asyncio
import secrets
import subprocess

import irc3
from irc3.plugins.command import command
from niquests import AsyncSession, RequestException

from cappuccino.plugins import Plugin


def _is_multiline_string(text: str):
    # require minimum 2 newlines to account for the newline at the end of output.
    return text.count("\n") > 1


async def _exec_wrapper(cmd: list[str], input_data: str | None = None) -> str:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE if input_data else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdin_data = input_data.encode("UTF-8") if input_data else None
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(stdin_data), timeout=5)
    except TimeoutError as ex:
        proc.kill()
        raise subprocess.TimeoutExpired(cmd, 5) from ex
    return stdout.decode("UTF-8").strip()


@irc3.plugin
class ExecShell(Plugin):
    requires = ["irc3.plugins.command"]

    def __init__(self, bot):
        super().__init__(bot)
        self._session: AsyncSession = AsyncSession()

    @command(
        permission="admin", show_in_help_list=False, options_first=True, use_shlex=True
    )
    async def exec(self, mask, target, args):
        """Run a system command and upload the output to 0x0.st.

        %%exec <command>...
        """

        try:
            output = await _exec_wrapper(args["<command>"])
            if not output:
                return f"{mask.nick}: Command returned no output."

            # Don't paste single line outputs.
            if not _is_multiline_string(output):
                return f"{mask.nick}: {output}"

            # Upload multiline output to 0x0.st to avoid flooding channels.
            result = await self._session.post(
                "https://0x0.st",
                files={"file": (f"cappuccino-{secrets.token_hex()}.txt", output)},
                data={"expires": 1},
            )

        except (FileNotFoundError, RequestException, subprocess.TimeoutExpired) as ex:
            return f"{mask.nick}: {ex}"

        return f"{mask.nick}: {result.text}"
