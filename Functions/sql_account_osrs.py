from Functions import sql_config

# Flatten the WOM group payload into a list of membership entries, optionally filtered to one player
def _normalize_wom(member_data, member_id=None):
	if not member_data:
		return []
	memberships = member_data.get("groupData", {}).get("memberships", [])
	if member_id is not None:
		memberships = [m for m in memberships if str(m.get("player_id")) == str(member_id)]
	return memberships

#Resolve null strings
def _text(value):
	# Columns are NOT NULL VARCHAR; fall back to "" for None values.
	return "" if value is None else str(value)

# Look up rank_id for a membership's WOM role, falling back to a default rank if unmapped
def _resolve_rank_id(entry, rank_map):
	role = entry.get("role")
	return rank_map.get(role, rank_map.get("_default", 0))

# Load the WOM role -> rank_id mapping.
# For each unseen role, case-insensitively match its name against discord_roles.discord_role_name;
# if a match exists, use discord_promotion_ranks.promotion_rank_id (via discord_role_id) as the
# osrs_role_id so the two stay aligned. Any role with no match gets the next free id.
def _load_rank_map(SQL_Connection, SQL_Cursor, roles: list = None) -> dict:
	rank_map = {
		row["osrs_role_name"]: row["osrs_role_id"]
		for row in Roles_Get(SQL_Cursor)
	}
	roles = [role for role in (roles or []) if role]
	if not roles:
		return rank_map
	missing = [role for role in roles if role not in rank_map]
	if not missing:
		return rank_map
 
	# Pull every discord role name -> promotion_rank_id pair for case-insensitive matching
	SQL_Query = "SELECT dr.discord_role_name, dpr.promotion_rank_id FROM discord_roles AS dr JOIN discord_promotion_ranks AS dpr ON dpr.discord_role_id = dr.discord_role_id";
	discord_rows = sql_config.Query_Dicts_Get(SQL_Cursor, SQL_Query)
	# Ensure the name verification when comparing OSRS and discord roles are compliant (no spaces, all lowercase comparison)
	discord_rank_lookup = {
		row["discord_role_name"].lower().replace(" ", "_"): row["promotion_rank_id"]
		for row in discord_rows
		if row["promotion_rank_id"] is not None
	}
 
	linked = []
	unlinked = []
	for role in missing:
		# Converted space to underscore to match dictionary keys
		rank_id = discord_rank_lookup.get(role.lower().replace(" ", "_"))
		if rank_id is not None:
			linked.append((rank_id, role))
		else:
			unlinked.append(role)
 
	if linked:
		SQL_Cursor.executemany("INSERT IGNORE INTO osrs_roles (osrs_role_id, osrs_role_name) VALUES (%s, %s)", linked)
		#Populate the link table between osrs roles and discord roles
		SQL_Cursor.execute(
			"""INSERT IGNORE INTO link_discord_osrs_roles (discord_role_id, osrs_role_id)
			   SELECT dr.discord_role_id, dpr.promotion_rank_id AS osrs_role_id
			   FROM discord_roles AS dr
			   JOIN discord_promotion_ranks AS dpr ON dpr.discord_role_id = dr.discord_role_id
			   WHERE dpr.promotion_rank_id IS NOT NULL"""
		)
		SQL_Connection.commit()
 
	if unlinked:
		# osrs_role_id is being assigned explicitly here, so compute the next free
		# index ourselves rather than relying on auto-increment (avoids colliding
		# with the promotion_rank_id values just inserted above).
		next_id_rows = sql_config.Query_Dicts_Get(SQL_Cursor, "SELECT COALESCE(MAX(osrs_role_id), 0) AS max_id FROM osrs_roles")
		next_id = next_id_rows[0]["max_id"] + 1
		unlinked_rows = []
		for role in unlinked:
			unlinked_rows.append((next_id, role))
			next_id += 1
		SQL_Cursor.executemany("INSERT IGNORE INTO osrs_roles (osrs_role_id, osrs_role_name) VALUES (%s, %s)", unlinked_rows)
		SQL_Connection.commit()
 
	#Get OSRS roles list
	rank_map = {
		row["osrs_role_name"]: row["osrs_role_id"]
		for row in Roles_Get(SQL_Cursor)
	}
	return rank_map

# Insert or Update OSRS (Wise Old Man) group members
def Members_List_And_Roles_List_Update(SQL_Connection, SQL_Cursor, member_data, member_id=None):
	entries = _normalize_wom(member_data, member_id)
	if not entries:
		return 0
	unique_roles = list({m["role"] for m in member_data["groupData"]["memberships"]})
	print(unique_roles)
	rank_map = _load_rank_map(SQL_Connection, SQL_Cursor, unique_roles)
	rows = [
		(
			entry["player_id"],
			_text(entry.get("display_name")),
			_resolve_rank_id(entry, rank_map),
			entry.get("created_at"),
		)
		for entry in entries
	]
	cursor = SQL_Connection.cursor()
	try:
		sql = "INSERT INTO osrs_members (player_id, current_rsn, rank_id, join_date, current_member) VALUES (%s, %s, %s, %s, TRUE) ON DUPLICATE KEY UPDATE current_rsn = VALUES(current_rsn), rank_id = VALUES(rank_id), current_member = TRUE, leave_date = NULL"
		cursor.executemany(sql, rows)
		SQL_Connection.commit()
		rowcount = cursor.rowcount
	except MySQLError:
		SQL_Connection.rollback()
		raise
	finally:
		cursor.close()
	return rowcount

#Get all osrs members
def Members_Get(SQL_Cursor) -> list[dict]:
	Query = "SELECT player_id, current_rsn, rank_id, join_date, leave_date, current_member, created_at, updated_at FROM osrs_members"
	'''Query = """SELECT om.player_id, om.current_rsn, om.rank_id, om.join_date, om.leave_date, om.current_member, om.created_at, om.updated_at, dpr.promotion_rank_id AS discord_promotion_rank_id FROM osrs_members AS om
	LEFT JOIN link_discord_osrs_roles AS ldo ON om.rank_id = ldo.osrs_role_id
	LEFT JOIN discord_promotion_roles AS dpr ON ldo.discord_role_id = dpr.discord_role_id"""'''
	return sql_config.Query_Dicts_Get(SQL_Cursor, Query)

#Display all osrs members
def Members_Display(members: list[dict]):
	"""Prints osrs_members formatted in the console."""
	print(f"\n--- OSRS MEMBERS ({len(members)} records) ---")
	header = f"{'Player ID':<10} | {'Current RSN':<20} | {'Rank ID':<8} | {'Active':<7} | {'Join Date'}"
	print(header)
	print("-" * len(header))
	for m in members:
		join_str = m['join_date'].strftime('%Y-%m-%d') if m['join_date'] else 'N/A'
		print(
			f"{str(m['player_id']):<10} | "
			f"{str(m['current_rsn']):<20} | "
			f"{str(m['rank_id']):<8} | "
			f"{str(m['current_member']):<7} | "
			f"{join_str}"
		)

#Retrieves every row of osrs_roles (osrs_role_id, osrs_role_name).
def Roles_Get(SQL_Cursor) -> list[dict]:
	Query = "SELECT osrs_role_id, osrs_role_name FROM osrs_roles"
	return sql_config.Query_Dicts_Get(SQL_Cursor, Query)