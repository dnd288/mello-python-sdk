# Mello CLI Operations

All commands return JSON. Provide `MELLO_API_KEY` in the environment. Use IDs
from a prior read/search response rather than guessing.

| Intent | Command | Notes |
|---|---|---|
| Current user | `mello-cli me get` or `mello-cli whoami` | Read-only |
| List workspaces | `mello-cli workspace list` | Read-only |
| Members | `mello-cli workspace members --workspace-id ID` | Read-only |
| List boards | `mello-cli board list --workspace-id ID` | Read-only |
| Get board | `mello-cli board get --board-id ID` | Includes columns/tickets |
| Create board | `mello-cli board create --workspace-id ID --name NAME [--code CODE]` | |
| Update board | `mello-cli board update --board-id ID --set name=NAME` | Fields: `name`, `background_color`, `cover_image_url` |
| Delete board | `mello-cli --yes board delete --board-id ID` | **confirm** |
| List columns | `mello-cli column list --board-id ID` | Read-only |
| Create column | `mello-cli column create --board-id ID --name NAME [--position N]` | |
| Update column | `mello-cli column update --column-id ID --set color=#ffcc00` | Fields: `name`, `position`, `color` |
| Reorder columns | `mello-cli column reorder --board-id ID --column-ids ID1,ID2` | Ordered IDs |
| List tickets | `mello-cli ticket list --board-id ID` | Read-only |
| Get ticket | `mello-cli ticket get --ticket-id ID` | Detail includes comments/checklists/activity |
| Create ticket | `mello-cli ticket create --column-id ID --title TITLE [--description TEXT] [--position N]` | |
| Update ticket | `mello-cli ticket update --ticket-id ID --set title=TITLE` | Fields: `title`, `description`, `description_html`, `pic_user_id`, `supervisor_id`, `start_date`, `end_date` |
| Move ticket | `mello-cli ticket move --ticket-id ID --column-id ID --position N` | Atomic move |
| Delete ticket | `mello-cli --yes ticket delete --ticket-id ID` | **confirm**; CLI/SDK-only (not an MCP tool) |
| Search tickets | `mello-cli ticket search --workspace-id ID --query TEXT` | Read-only |
| List comments | `mello-cli comment list --ticket-id ID` | Read-only |
| Create comment | `mello-cli comment create --ticket-id ID --body TEXT [--body-html HTML]` | |
| Ticket history | `mello-cli history list --ticket-id ID` | Read-only |
| Create checklist | `mello-cli checklist create --ticket-id ID --title TITLE [--position N]` | |
| Update checklist | `mello-cli checklist update --checklist-id ID --set title=TITLE` | Fields: `title`, `position` |
| Delete checklist | `mello-cli --yes checklist delete --checklist-id ID` | **confirm** |
| Create item | `mello-cli checklist item-create --checklist-id ID --title TITLE` | |
| Update item | `mello-cli checklist item-update --checklist-item-id ID --set is_checked=true` | Fields: `title`, `is_checked`, `position` |
| Delete item | `mello-cli --yes checklist item-delete --checklist-item-id ID` | **confirm** |
| Upload attachment | `mello-cli attachment upload --ticket-id ID --file PATH [--content-type MIME]` | Reads bytes from path |
| Download attachment | `mello-cli attachment download --attachment-id ID --output PATH` | Omitting output returns Base64 JSON |
| List webhooks | `mello-cli webhook list` | Read-only |
| Create webhook | `mello-cli --yes webhook create --workspace-id ID --model-type board --model-id ID --callback-url URL [--event EVENT]` | **confirm**; repeat `--event` |
| Update webhook | `mello-cli --yes webhook update --webhook-id ID --set active=false` | **confirm**; fields: `active`, `events`, `description`, `callback_url` |
| Delete webhook | `mello-cli --yes webhook delete --webhook-id ID` | **confirm** |
| Delivery history | `mello-cli webhook deliveries --webhook-id ID` | Read-only |
| Redeliver event | `mello-cli --yes webhook redeliver --webhook-id ID --delivery-id ID` | **confirm** |
| GitHub installations | `mello-cli github installations --workspace-id ID` | Read-only |
| GitHub repositories | `mello-cli github repos --workspace-id ID` | Read-only |
| Board GitHub repos | `mello-cli github board-repos --workspace-id ID --board-id ID` | Read-only |
| Replace board repos | `mello-cli --yes github replace-board-repos --workspace-id ID --board-id ID --repositories '[{"installation_id":1,"github_repo_id":2}]'` | **confirm**; replaces full set |
| Start GitHub connect | `mello-cli --yes github connect-start --workspace-id ID [--board-id ID] [--replace]` | **confirm** |
| Delete installation | `mello-cli --yes github delete-installation --workspace-id ID --installation-id ID` | **confirm** |
| Search GitHub objects | `mello-cli github search --ticket-id ID [--query TEXT] [--type issue] [--page N]` | Read-only |
| Link GitHub object | `mello-cli --yes github link --ticket-id ID --installation-id N --github-repo-id N --kind issue [--number N] [--branch-name NAME]` | **confirm** |
| Unlink GitHub object | `mello-cli --yes github unlink --ticket-id ID --link-id ID` | **confirm** |

## Field Values

`--set` accepts strings by default, JSON arrays/objects for structured fields,
`true`/`false` for booleans, integers for `position`, ISO-8601 datetimes for
ticket dates, and `null`/`none` for a nullable value. Use `--clear FIELD` for
the clearest explicit-null syntax.
