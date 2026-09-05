#!/usr/bin/env bash
# CONTRACT §5.3. Read-only; never repairs state or invokes a write API.
# stdin schema (all arrays required; complete must be true):
# {source_repo, ledger:[§6.2 lines], baseline:{collaborators:[{id}],invitations:[]},
#  collaborators:[{id}], invitations:[{invitee:{id}}], invitations_status:403,
#  markers:[{actor_id,tier,subject,author:"github-actions[bot]"}],
#  threads:[{subject,exists,readable,marker_deleted:false}], complete:true,
#  manual_allowlist:[id or {id}], manual_markers_allowlist:[{actor_id,tier,subject}]}
# Owner-only checkpoint #4: stdin checkpoint4:true selects the full zero-send
# audit, including exact pending-invite baseline comparison. This is not a
# workflow input. With --live-gh the owner supplies SUPPORTER_LOOP_TOKEN at step
# scope for that one-off comparison; the ledger-token probe must still be 403.
# Every successful comment subject requires a threads entry in live fixtures.
# marker_deleted=true is explicit moderation evidence supplied by the auditor;
# live collection cannot infer comment deletion from this schema (no comment id),
# so missing markers on existing threads require manual-markers-allowlist.json.
# --live-gh hydrates collaborators/invitations/markers/threads, leaving the owner
# baseline, ledger and allowlists from stdin. These correspond to ledger/baseline-*.json,
# ledger/manual-allowlist.json and ledger/manual-markers-allowlist.json; never inferred.
# SOURCE_REPO, REWARD_REPO, GH_TOKEN (source), SUPPORTER_LEDGER_TOKEN and (live only)
# SUPPORTER_LOOP_TOKEN must be supplied by the caller at step scope. No tokens logged.
# shellcheck disable=SC2016
set -euo pipefail
# GraphQL/jq dollar names are intentionally literal.
mode='' live_gh=false
while [ "$#" -gt 0 ]; do
  case "$1" in
    --mode) [ "$#" -ge 2 ] || exit 2; mode=$2; shift 2 ;;
    --live-gh) live_gh=true; shift ;;
    *) echo 'usage: reconcile-audit.sh --mode record-only|live [--live-gh] < state.json' >&2; exit 2 ;;
  esac
done
case "$mode" in record-only|live) ;; *) echo '::error:: invalid audit mode' >&2; exit 2 ;; esac
state=$(cat)
fail() { echo "::error:: $*" >&2; exit 1; }
jq -e 'type=="object" and (.ledger|type=="array") and (.baseline.collaborators|type=="array") and (.baseline.invitations|type=="array") and (.manual_allowlist|type=="array") and (.manual_markers_allowlist|type=="array")' <<< "$state" >/dev/null || fail 'audit-input: invalid baseline/ledger/allowlists'
jq -e '(has("checkpoint4")|not) or (.checkpoint4|type=="boolean")' <<< "$state" >/dev/null || fail 'audit-input: checkpoint4 must be boolean'
checkpoint4=$(jq -r '.checkpoint4 // false' <<< "$state")
if [ "$live_gh" = true ]; then
  : "${SOURCE_REPO:?}" "${REWARD_REPO:?}" "${GH_TOKEN:?}" "${SUPPORTER_LEDGER_TOKEN:?}"
  [[ $SOURCE_REPO =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ && $REWARD_REPO =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || fail 'invalid repo'
  # gh expects the GitHub host; github.com selects the api.github.com API.
  # gh --paginate follows REST Link headers through exhaustion. JSON is validated
  # after slurping; no partial result survives a failed page.
  rest_array() {
    local token=$1 endpoint=$2 response
    response=$(GH_TOKEN="$token" gh api --hostname github.com --method GET --paginate --slurp "$endpoint") || return 1
    jq -ce 'if all(.[];type=="array") then add // [] else error("non-array page") end' <<< "$response"
  }
  collaborators=$(rest_array "$SUPPORTER_LEDGER_TOKEN" "repos/$REWARD_REPO/collaborators?per_page=100") || fail 'collaborators incomplete'
  invitations='[]'; invitation_status=403
  if [ "$mode" = live ]; then
    : "${SUPPORTER_LOOP_TOKEN:?}"
    invitations=$(rest_array "$SUPPORTER_LOOP_TOKEN" "repos/$REWARD_REPO/invitations?per_page=100") || fail 'invitations incomplete'
    invitation_status=200
  else
    response=$(GH_TOKEN="$SUPPORTER_LEDGER_TOKEN" gh api --hostname github.com --method GET --include "repos/$REWARD_REPO/invitations" 2>/dev/null) && fail 'ledger token can list invitations'
    invitation_status=$(printf '%s\n' "$response" | sed -n 's|^HTTP/[^ ]* \([0-9][0-9][0-9]\).*|\1|p' | head -1)
    [ "$invitation_status" = 403 ] || fail 'invitation probe must return 403'
    if [ "$checkpoint4" = true ]; then
      : "${SUPPORTER_LOOP_TOKEN:?}"
      invitations=$(rest_array "$SUPPORTER_LOOP_TOKEN" "repos/$REWARD_REPO/invitations?per_page=100") || fail 'checkpoint4 invitations incomplete'
    fi
  fi
  comments=$(rest_array "$GH_TOKEN" "repos/$SOURCE_REPO/issues/comments?per_page=100") || fail 'issue markers incomplete'
  markers=$(jq -c '[.[] | select(.user.login=="github-actions[bot]") | . as $c | .body | scan("<!-- supporter-loop:tier([23]):([0-9]+) -->") | {actor_id:(.[1]|tonumber),tier:(.[0]|tonumber),subject:($c.html_url|split("#")[0]),author:"github-actions[bot]"}]' <<< "$comments")
  owner=${SOURCE_REPO%/*}; repo_name=${SOURCE_REPO#*/}
  graphql() {
    local response
    response=$(gh api --hostname github.com graphql -f query="$1" -f owner="$owner" -f name="$repo_name" "${@:2}") || return 1
    jq -e '(.errors // [] | length)==0 and .data != null' <<< "$response" >/dev/null || return 1
    printf '%s\n' "$response"
  }
  # Each level owns its cursor: discussions, top-level comments, and replies.
  source_meta=$(gh api --hostname github.com --method GET "repos/$SOURCE_REPO") || fail 'source metadata unavailable'
  has_discussions=$(jq -er '.has_discussions | if type=="boolean" then tostring else error("missing has_discussions") end' <<< "$source_meta") || fail 'source metadata malformed'
  discussions='[]'; cursor=''
  while [ "$has_discussions" = true ]; do
    page=$(graphql 'query($owner:String!,$name:String!,$cursor:String){repository(owner:$owner,name:$name){discussions(first:100,after:$cursor){nodes{number url} pageInfo{hasNextPage endCursor}}}}' -F cursor="${cursor:-null}") || fail 'discussion listing incomplete'
    connection=$(jq -ce '.data.repository.discussions | select((.nodes|type=="array") and (.pageInfo.hasNextPage|type=="boolean"))' <<< "$page") || fail 'discussion listing malformed'
    discussions=$(jq -cn --argjson all "$discussions" --argjson page "$connection" '$all+$page.nodes')
    [ "$(jq -r '.pageInfo.hasNextPage' <<< "$connection")" = false ] && break
    next=$(jq -er '.pageInfo.endCursor | select(type=="string" and length>0)' <<< "$connection") || fail 'discussion cursor absent'
    [ "$next" != "$cursor" ] || fail 'discussion cursor stalled'; cursor=$next
  done
  while IFS= read -r discussion; do
    number=$(jq -r '.number' <<< "$discussion"); subject=$(jq -r '.url' <<< "$discussion"); cursor=''
    while :; do
      page=$(graphql 'query($owner:String!,$name:String!,$number:Int!,$cursor:String){repository(owner:$owner,name:$name){discussion(number:$number){comments(first:100,after:$cursor){nodes{id body author{login}} pageInfo{hasNextPage endCursor}}}}}' -F number="$number" -F cursor="${cursor:-null}") || fail 'discussion comments incomplete'
      connection=$(jq -ce '.data.repository.discussion.comments | select((.nodes|type=="array") and (.pageInfo.hasNextPage|type=="boolean"))' <<< "$page") || fail 'discussion comments malformed'
      nodes=$(jq -c '.nodes' <<< "$connection")
      while IFS= read -r comment; do
        combined=$(jq -cn --argjson comment "$comment" '[$comment]'); reply_cursor=''
        while :; do
          reply_page=$(graphql 'query($id:ID!,$cursor:String){node(id:$id){... on DiscussionComment{replies(first:100,after:$cursor){nodes{body author{login}} pageInfo{hasNextPage endCursor}}}}}' -f id="$(jq -r '.id' <<< "$comment")" -F cursor="${reply_cursor:-null}") || fail 'discussion replies incomplete'
          replies=$(jq -ce '.data.node.replies | select((.nodes|type=="array") and (.pageInfo.hasNextPage|type=="boolean"))' <<< "$reply_page") || fail 'discussion replies malformed'
          combined=$(jq -cn --argjson all "$combined" --argjson page "$replies" '$all+$page.nodes')
          [ "$(jq -r '.pageInfo.hasNextPage' <<< "$replies")" = false ] && break
          next=$(jq -er '.pageInfo.endCursor | select(type=="string" and length>0)' <<< "$replies") || fail 'reply cursor absent'
          [ "$next" != "$reply_cursor" ] || fail 'reply cursor stalled'; reply_cursor=$next
        done
        found=$(jq -c --arg subject "$subject" '[.[]|select(.author.login=="github-actions[bot]")|.body|scan("<!-- supporter-loop:tier([23]):([0-9]+) -->")|{actor_id:(.[1]|tonumber),tier:(.[0]|tonumber),subject:$subject,author:"github-actions[bot]"}]' <<< "$combined")
        markers=$(jq -cn --argjson all "$markers" --argjson found "$found" '$all+$found')
      done < <(jq -c '.[]' <<< "$nodes")
      [ "$(jq -r '.pageInfo.hasNextPage' <<< "$connection")" = false ] && break
      next=$(jq -er '.pageInfo.endCursor | select(type=="string" and length>0)' <<< "$connection") || fail 'comment cursor absent'
      [ "$next" != "$cursor" ] || fail 'comment cursor stalled'; cursor=$next
    done
  done < <(jq -c '.[]' <<< "$discussions")
  # REST thread listing proves existence without ambiguous per-thread 404s.
  issues=$(rest_array "$GH_TOKEN" "repos/$SOURCE_REPO/issues?state=all&per_page=100") || fail 'threads incomplete'
  threads=$(jq -cn --argjson issues "$issues" --argjson discussions "$discussions" '[$issues[].html_url,$discussions[].url]|unique|map({subject:.,exists:true,readable:true,marker_deleted:false})')
  # Missing subjects are explicitly deleted/unreadable. No successful fetch is guessed.
  threads=$(jq -cn --argjson ledger "$(jq '.ledger' <<< "$state")" --argjson threads "$threads" '$threads + [($ledger|map(select(.action=="comment")|.subject)|unique)[] as $s | select(all($threads[];.subject!=$s))|{subject:$s,exists:false,readable:false,marker_deleted:false}]')
  state=$(jq -c --arg source "$SOURCE_REPO" --argjson c "$collaborators" --argjson i "$invitations" --argjson status "$invitation_status" --argjson m "$markers" --argjson t "$threads" '.source_repo=$source|.collaborators=$c|.invitations=$i|.invitations_status=$status|.markers=$m|.threads=$t|.complete=true' <<< "$state")
fi
jq -e '.complete==true and (.source_repo|type=="string") and ([.collaborators,.invitations,.markers,.threads]|all(.[];type=="array"))' <<< "$state" >/dev/null || fail 'audit-input: incomplete state'
divergences=$(jq -r --arg mode "$mode" '
  def success: .result|(.=="ok" or startswith("ok-") or startswith("already-") or .=="noop" or .=="expired");
  def closes: (.action|IN("revoke","would-revoke","cancel-invite","would-cancel-invite")) and success and .result!="expired";
  def ids: map(if type=="number" then . else .id end)|unique;
  def markkey: [.actor_id,.tier,.subject];
  . as $s | [.markers[]|select(.author=="github-actions[bot]")] as $markers |
  if $mode=="record-only" then
    (if (.collaborators|ids)!=(.baseline.collaborators|ids) then "reduced-collaborators: baseline differs" else empty end),
    (if .invitations_status!=403 then "reduced-probe: expected 403" else empty end),
    (if .checkpoint4==true and (([.invitations[].invitee.id]|unique)!=([.baseline.invitations[].invitee.id]|unique)) then "checkpoint4-invitations: baseline differs" else empty end),
    (if ($markers|length)>0 then "reduced-markers: workflow markers exist" else empty end)
  else
    # File-order duplicates cannot increase the closure count. Latest means ts,
    # with input order as the tie breaker for same-second action attempts.
    [.ledger|to_entries[]|.value+{_order:.key}|select(.repo==$s.source_repo)] as $ledger |
    ([$ledger|group_by(.actor_id)[]|
      . as $history | (1+([$history[]|select(closes)|.run_id]|unique|length)) as $gen |
      [$history[]|select(.gen==$gen)] as $current |
      [$current[]|select(.action=="invite" and success)]|sort_by(.ts,._order)|last as $invite |
      select($invite!=null) |
      select(all($current[]; (.action!="cancel-invite" or .result!="expired") or ([.ts,._order] <= [$invite.ts,$invite._order]))) |
      $invite.actor_id] | unique) as $predicted |
    ([.collaborators[].id,.invitations[].invitee.id]|unique) as $actual |
    ([.baseline.collaborators[].id,.baseline.invitations[].invitee.id]+(.manual_allowlist|ids)|unique) as $allowed |
    (($predicted-$actual)[]|"access: missing actor_id=\(.)"),
    (($actual-$predicted-$allowed)[]|"strangers: unexpected actor_id=\(.)"),
    [$ledger[]|select(.action=="comment" and success)] as $comments |
    ($markers[] as $m|select(all($comments[];.actor_id!=$m.actor_id or .tier!=$m.tier))|"markers-A: unledgered actor_id=\($m.actor_id) tier=\($m.tier) subject=\($m.subject)"),
    ($comments|unique_by(markkey)[] as $c|
      [$s.threads[]|select(.subject==$c.subject)] as $thread |
      if ($thread|length)==0 then "markers-B-state: absent thread evidence subject=\($c.subject)"
      elif any($thread[];.exists and .readable and (.marker_deleted!=true)) and
        all($markers[];markkey!=($c|markkey)) and
        all($s.manual_markers_allowlist[];markkey!=($c|markkey))
      then "markers-B: missing actor_id=\($c.actor_id) tier=\($c.tier) subject=\($c.subject)" else empty end)
  end
' <<< "$state") || fail 'audit-input: invalid state data'
if [ -n "$divergences" ]; then
  while IFS= read -r divergence; do printf '::error:: %s\n' "$divergence"; done <<< "$divergences"
  exit 1
fi
printf 'reconciliation clean (%s)\n' "$mode"
