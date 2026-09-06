#Get an env variable including required imports, for use inside functions to reduce duplicated imports
def env_get(Variable):
	import os
	import json
	return str(os.getenv(Variable))

#Displays an error due to command permissions
async def Command_Permissions_Issue(interaction, Display_Message = True):
	Message = "You do not have the correct permissions execute this command with the inputs supplied. Please contact a moderator if you believe this is incorrect."
	if Display_Message:
		await interaction.response.send_message(Message, ephemeral=True)
	return Message

#Log channel
async def Notify_Channel(client, Channel_ID = None, Message = None):
	"""Send a plain notification message to a channel by id, best-effort."""
	if Message is None:
		return
	if not Channel_ID:
		return
	try:
		Channel_ID = int(Channel_ID)
	except (TypeError, ValueError):
		return
	Channel = client.get_channel(Channel_ID)
	if Channel is None:
		try:
			Channel = await client.fetch_channel(Channel_ID)
		except Exception:
			return
	try:
		await Channel.send(Message)
	except Exception:
		return