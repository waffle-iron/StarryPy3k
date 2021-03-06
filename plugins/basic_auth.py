"""
StarryPy Basic Authentication Plugin

Blocks UUID spoofing of staff members by forcing players with Moderator roles
to log in with a whitelisted Starbound account.
Permitted accounts are defined in StarryPy3k's configuration file.

Original Authors: GermaniumSystem
"""

import asyncio

import packets
import utilities
from plugins.player_manager import Owner, Moderator, Player
from base_plugin import SimpleCommandPlugin
from data_parser import ConnectFailure, ServerDisconnect
from pparser import build_packet
from utilities import State
from packets import packets



class BasicAuth(SimpleCommandPlugin):
    name = "basic_auth"
    depends = ["player_manager"]
    default_config = {"enabled" : False,
                      "staff_sb_accounts": [
                         "-- REPLACE WITH STARBOUND ACCOUNT NAME --",
                         "-- REPLACE WITH ANOTHER --",
                         "-- SO ON AND SO FORTH ---"],
                      "owner_sb_account" : "-- REPLACE WITH OWNER ACCOUNT --"}

    def activate(self):
        super().activate()
        if self.config.get_plugin_config(self.name)["enabled"]:
            self.logger.debug("Enabled.")
            self.enabled = True
        else:
            self.enabled = False
            self.logger.warning("+---------------< WARNING >---------------+")
            self.logger.warning("| basic_auth plugin is disabled! You are  |")
            self.logger.warning("| vulnerable to UUID spoofing attacks!    |")
            self.logger.warning("| Consult README for enablement info.     |")
            self.logger.warning("+-----------------------------------------+")

    def on_client_connect(self, data, connection):
        """
        Catch when a the client updates the server with its connection
        details.

        :param data:
        :param connection:
        :return: Boolean: True on successful connection, False on a
                 failed connection.
        """

        if not self.enabled:
            return True
        uuid = data["parsed"]["uuid"].decode("ascii")
        try:
            account = data["parsed"]["account"][0]
            # Why [0]? Because 'account' is a StringSet.
            # ...but it never contains more than one string.
        except:
            # Except sometimes account is empty...
            # I'm not entirely sure why this is, so please feel free to explore.
            account = ''
            #self.logger.debug(data)
        player = self.plugins["player_manager"].get_player_by_uuid(uuid)
        # We're only interested in players who already exist.
        if player:
            # The Owner account is quite dangerous, so it has a separate
            # password to prevent a malicious staff member from taking over.
            # Moderator thru SuperAdmin can still execute spoofing attacks on
            # eachother, but this is being allowed for the sake of usability.
            if (
                   (
                        player.check_role(Owner)
                        and account == self.plugin_config.owner_sb_account
                   ) or (
                        not player.check_role(Owner)
                        and player.check_role(Moderator)
                        and account in self.plugin_config.staff_sb_accounts
                   )
            ):
                # Everything checks out.
                self.logger.info("Player with privileged UUID '{}' "
                                 "successfully authenticated as "
                                 "'{}'".format(uuid, account))
                # We don't need to worry about anything after this.
                # Starbound will take care of an incorrect password.
            elif player.check_role(Owner) or player.check_role(Moderator):
                # They're privileged but failed to authenticate. Kill it.
                yield from connection.raw_write(
                    self.build_rejection("^red;UNAUTHORIZED^reset;\n"
                                         "Privileged players must log in with "
                                         "an account defined in StarryPy3k's "
                                         "config."))
                connection.die()
                self.logger.warning("Player with privileged UUID '{}' FAILED "
                                    "to authenticate as '{}'"
                                    "!".format(uuid, account))
                return False
        return True


    # Helper functions - Used by hooks and commands

    def build_rejection(self, reason):
        """
        Function to build packet to reject connection for client.

        :param reason: String. Reason for rejection.
        :return: Rejection packet.
        """
        return build_packet(packets["connect_failure"],
                            ConnectFailure.build(
                                dict(reason=reason)))

