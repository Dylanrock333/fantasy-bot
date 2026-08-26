# Fantasy ESPN Checklist — Transaction

Part of a 5-way split of
[`FANTASY_ESPN_API_CHECKLIST.md`](../FANTASY_ESPN_API_CHECKLIST.md), clustered to match
[`fantasy_transaction_tools.py`](../fantasy_transaction_tools.py). See the main checklist for
Construction params, Return object shapes, Constant maps, and Notes/gotchas (not duplicated
here). 5 of 31 total checklist items.

> Requires an already-constructed `league` object.

- [x] `league.recent_activity(size=25, msg_type=None, offset=0)`
  - Params: confirmed — `size` (default `25`), `msg_type` (`None`, `"FA"`, `"WAIVER"`, or `"TRADED"` — maps to ESPN message-type IDs; `None` includes all of FA/WAIVER/DROP/TRADE), `offset` (default `0`)
  - Summary: Tried default and `msg_type="FA"` calls against this real league (2026, preseason) — both returned an empty list (no adds/drops/trades logged yet this season). Confirmed this endpoint only works for the **current active season**: calling the equivalent for 2024/2025 (past completed seasons on this same league ID) raised `ESPNInvalidLeague('League ... does not exist')` because the `/communication/` endpoint doesn't support the historical `leagueHistory` API path.
  - Returns: `List[Activity]` — Recent adds/drops/trades. **2019+ only, current season only.** Each `Activity` has `.date` (`int`, epoch ms) and `.actions` (`List[Tuple[Team, str, Player|int|str, int]]` — one tuple per roster move: `(team, action, player, bid_amount)`). `action` is one of `'FA ADDED'`, `'WAIVER ADDED'`, `'DROPPED'`, or `'TRADED'`; a trade message emits two tuples tagged `'TRADE_SENT'`/`'TRADE_RECEIVED'` (not `'TRADED'` in practice); `bid_amount` is only non-zero for `'WAIVER ADDED'`. `player` is a `Player` object when resolvable from a team roster, else falls back to `player_info(playerId=...)` or the raw player ID. `repr(activity)` renders as `Activity((team,action,player) (team,action,player) ...)`.
  - Network: live — Side effects: none
  - Wired: `fantasy_transaction_tools.get_recent_activity`

- [x] `league.transactions(scoring_period=None, types={"FREEAGENT","WAIVER","WAIVER_ERROR"})`
  - Params: confirmed — `scoring_period` (optional `int`; defaults to `league.scoringPeriodId` when omitted/falsy), `types` (`Set[str]`, must be a subset of `TRANSACTION_TYPES` = `{"WAIVER","TRADE_UPHOLD","WAIVER_ERROR","TRADE_ACCEPT","FUTURE_ROSTER","ROSTER","FREEAGENT","TRADE_ERROR","TRADE_PROPOSAL","RETRO_ROSTER","TRADE_DECLINE","TRADE_VETO","DRAFT"}` — an invalid member raises `Exception('Invalid transaction type')`)
  - Summary: Called with defaults, with `scoring_period=1`, and with `types={"FREEAGENT"}` against this real league (2026, preseason, `scoringPeriodId=0`) — all three calls raised `Exception('No transactions found')` because the ESPN response for this scoring period has no `'transactions'` key (no waiver/FA moves have happened yet). This is a raised exception, **not** an empty list — callers must catch it.
  - Returns: `List[Transaction]` (when transactions exist) — Transactions for a scoring period, filtered by type set. Each `Transaction` has `.team` (`Team`), `.type` (`str`, e.g. `"WAIVER"`/`"FREEAGENT"`), `.status` (`str`, e.g. `"EXECUTED"`), `.scoring_period` (`int`), `.date` (`int|None`, epoch ms — `processDate` falling back to `proposedDate`), `.bid_amount` (`float|None`), `.items` (`List[TransactionItem]`). Each `TransactionItem` has `.type` (`str`, e.g. `"ADD"`/`"DROP"`), `.playerId` (`int`), `.player` (`str` player name from `player_map`, or `"Unknown"`).
  - Network: live — Side effects: none
  - Wired: `fantasy_transaction_tools.get_transactions` — wraps the documented `Exception('No transactions found')` in a try/except and returns a friendly "No transactions found for this scoring period." string instead of letting it crash; re-raises any other exception. Live-tested against this preseason league with defaults and `scoring_period=1` — both hit the no-data path and returned the friendly string, no traceback.

- [ ] `league.message_board(msg_types=None)`
  - Params: confirmed — `msg_types` (optional `List[str]` of topic-type keys, e.g. `["CHAT_ALL_MEMBERS"]`; unsupported/unknown values raise `ESPNUnknownError('ESPN returned an HTTP 400')` — e.g. `msg_types=["FEATURED"]` failed)
  - Summary: Called with defaults against this real league and got 31 real topic threads back (draft/waiver chat between league members from prior seasons, still surfaced on the 2026 board). Filtering with `msg_types=["CHAT_ALL_MEMBERS"]` narrowed it to 1 matching topic.
  - Returns: `List[dict]` — Raw league message board topics. Each topic dict has keys: `author` (`str`, e.g. `"NightlyLeagueUpdateTaskProcessor"` or a member GUID), `creationInfo`/`lastUpdateInfo` (`dict`), `date`/`dateEdited` (`int`, epoch ms), `id` (`str` UUID), `isDeleted`/`isEdited` (`bool`), `messages` (`List[dict]` — individual posts, each with `author` (member GUID `str`), `content` (`str`, the post text), `date` (epoch ms), `id`, `messageTypeId` (`int`), `topicId`), `totalMessageCount` (`int`), `type` (`str`, e.g. `"CHAT_ALL_MEMBERS"`), `unreadMessageCount` (`int`).
  - Network: live — Side effects: none
  - Not wired: re-confirmed live (31 topics, e.g. `type="CHAT_ALL_MEMBERS"`) but skipped — this is raw league-member chat/banter, not roster or league data, and `author`/`messages[].author` are opaque member GUID strings (e.g. `"{25DA9CB5-6D7C-41D9-9464-41F4751CDA04}"`) with no name resolution available here, so a wired tool would surface unreadable IDs instead of usable content. Doesn't fit this file's transaction/activity theme.

- [ ] `league.refresh()`
  - Params: confirmed — none
  - Summary: Called on this real league — ran without error and returned nothing. `league.teams` stayed at 12 (unchanged before/after), and `league.settings`/`league.draft` were re-populated from a fresh fetch (`league.draft` came back as an empty list since the 2026 draft hasn't happened yet).
  - Returns: `None` — Re-fetches league + team data (use instead of re-instantiating)
  - Network: live — Side effects: overwrites `league.teams`, `league.settings`, `league.draft`, and other cached attributes with fresh data
  - Not wired: pure cache-refresh side effect with no return value to surface to the calling LLM; no natural "refresh my league data" chat use case in this transaction-focused file, and every other tool already re-fetches live on each call via `league_singleton()`.

- [ ] `league.previousSeasons`
  - Type: `List[int]`
  - Summary: For this real league (year=2026) this returned `[2024, 2025]`. Note: constructing a `League` for those past years and calling `recent_activity()`/`message_board()` on them fails (`ESPNInvalidLeague`) — only `transactions()`/roster-style endpoints work across historical years, not the communication-based ones.
  - Returns: `List[int]` — Prior seasons for this league ID, e.g. `[2024, 2025]` for this league — useful for cross-referencing historical transaction patterns
  - Not wired: a bare list of years (`[2024, 2025]`) has no standalone chat value on its own — it's only useful to cross-reference historical transactions/activity, and those endpoints (`recent_activity`, `message_board`) confirmed fail for past seasons on this league anyway, so there's no working tool to pair it with.
