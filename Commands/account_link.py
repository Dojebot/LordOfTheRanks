async def Link_Update(interaction: discord.Interaction, member: discord.member, runescape_name: str = None, is_main_account: bool = False) -> None:

	return sql_account_link.Linked_Accounts_Update(interaction, SQL_Connection, SQL_Cursor, member, osrs_id = 0, is_main_account = False)

async def Link_Delete(interaction: discord.Interaction, member: discord.member, runescape_name: str = None) -> None:

	return sql_account_link.Linked_Accounts_Delete(interaction, SQL_Connection, SQL_Cursor, member, osrs_id = 0, is_main_account = False)

async def Link_Lock(interaction: discord.Interaction, member: discord.member) -> None:

	return sql_account_link.Linked_Accounts_Lock_Toggle(interaction, SQL_Connection, SQL_Cursor, member)


# Points subcommand group; appears in Discord as "/Linked_Accounts <subcommand>"
Points_Group = app_commands.Group(name="linked_accounts", description="Manage OSRS RSN and Discord links", guild_ids=[int(DISCORD_GUILD)])
#Command for adding points
@Points_Group.command(name="add_or_update", description="Add or Update a link between a discord member and RSN")
async def link_add(interaction: discord.Interaction, member: discord.Member, runescape_name: str = None, is_main_account: bool = False) -> None:
	await Link_Update(interaction, member, runescape_name, is_main_account)

@Points_Group.command(name="delete", description="Delete a link between a discord member and RSN")
async def link_delete(interaction: discord.Interaction, member: discord.Member, runescape_name: str = None) -> None:
	await Link_Delete(interaction, member, runescape_name)

@Points_Group.command(name="toggle_lock", description="Lock changing or deleting account links for a specific discord id")
async def link_delete(interaction: discord.Interaction, member: discord.Member) -> None:
	await Link_Lock(interaction, member)

@Points_Group.command(name="set_main_rsn", description="Set an already linked OSRS account as a main")
async def set_main(interaction: discord.Interaction, member: discord.Member, runescape_name: str = None, is_main_account: bool = False) -> None:
	await Link_Update(interaction, SQL_Connection, SQL_Cursor, discord_id, osrs_id)