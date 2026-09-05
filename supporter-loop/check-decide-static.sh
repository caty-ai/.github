#!/usr/bin/env bash
# Contract §4.4. Conservative source scanner, not a general YAML/shell evaluator.
# Unsupported dynamic Contents targets fail closed; keep ledger/ visible in code.
set -euo pipefail
if [ "$#" -ne 1 ] || [ ! -f "$1" ]; then
  echo 'usage: check-decide-static.sh <workflow.yml>' >&2
  exit 2
fi
awk '
function hit(rule, n, why) {
  print FILENAME ":" n ": " rule ": " why
  bad=1
}
function trim(s) { sub(/^[ \t]+/, "", s); sub(/[ \t]+$/, "", s); return s }
function unquote(s) {
  s=trim(s)
  if (s ~ /^".*"$/ || s ~ /^\047.*\047$/) s=substr(s,2,length(s)-2)
  return s
}
function replace_literal(s, old, value, p, result) {
  result=""
  while ((p=index(s,old)) > 0) {
    result=result substr(s,1,p-1) value
    s=substr(s,p+length(old))
  }
  return result s
}
function resolve(s, k, pass) {
  for (pass=0; pass<8; pass++) {
    for (k in vars) {
      s=replace_literal(s,"${" k "}",vars[k])
      s=replace_literal(s,"${{ env." k " }}",vars[k])
      # Match an entire shell variable; $PATH must not rewrite $PATH_SUFFIX.
      s=replace_variable(s,k,vars[k])
    }
  }
  return s
}
function replace_variable(s,k,v, p,t,nextchar,out) {
  out=""
  while ((p=index(s,"$" k)) > 0) {
    nextchar=substr(s,p+length(k)+1,1)
    t=substr(s,1,p-1)
    if (nextchar ~ /[A-Za-z_0-9]/) {
      out=out t "$" k; s=substr(s,p+length(k)+1)
    } else {
      out=out t v; s=substr(s,p+length(k)+1)
    }
  }
  return out s
}
function inspect(s,n, gh,curl,explicit,implicit,get,write,path,tail,methods,unresolved) {
  s=resolve(s)
  gh=(s ~ /(^|[^A-Za-z_])gh[ \t]+api([ \t]|$)/)
  curl=(s ~ /(^|[^A-Za-z_])curl([ \t]|$)/)
  if (!gh && !curl) return
  # Adjacent quoted shell fragments form one method token ("PU""T" -> PUT).
  methods=s
  gsub(/["\047]/,"",methods)
  unresolved=(methods ~ /(--method[= \t]+|-X[ \t]*|--request[= \t]+)[^ \t]*[$`]/)
  explicit=(methods ~ /(--method[= \t]+|-X[ \t]*|--request[= \t]+)(PUT|POST|PATCH|DELETE)([ \t]|$)/)
  get=(gh && s ~ /--method[= \t]+["\047]?GET(["\047 \t]|$)/) || (curl && s ~ /(-X[ \t]*|--request[= \t]+)["\047]?GET(["\047 \t]|$)/)
  implicit=(gh && s ~ /(^|[ \t])(-[fF]([ \t=]|[^-])|--(input|raw-field|field)([= \t]|$))/) || (curl && s ~ /(^|[ \t])(-[dT]([ \t=]|[^-])|--(data|data-raw|data-binary|data-urlencode|json|upload-file)([= \t]|$))/)
  write=explicit || unresolved || (implicit && !get)
  # GraphQL query transport uses POST; the operation, not transport, decides.
  if (gh && s ~ /api[ \t]+graphql([ \t]|$)/ && s !~ /(^|[^A-Za-z_])mutation([^A-Za-z_]|$)/) {
    if (s ~ /query[= \t]+["\047]*query([ \t({]|$)/ || s ~ /query[= \t]+["\047]*\{/) write=unresolved
    else if (implicit) hit("b",n,"GraphQL operation cannot be proven read-only")
  }
  if (s ~ /(^|[^A-Za-z_])mutation([^A-Za-z_]|$)/) hit("b",n,"GraphQL mutation in decide")
  if (write && (s ~ /\/(collaborators|invitations|comments|graphql)([^A-Za-z_-]|$)|\/contents\/SUPPORTERS[.]md/ || (gh && s ~ /api[ \t]+graphql([ \t]|$)/))) hit("b",n,"write to delivery endpoint")
  if (write && match(s,/\/contents\//)) {
    tail=substr(s,RSTART+RLENGTH)
    # Traversal and encoding must not turn the allowlisted prefix into escape.
    if (tail !~ /^ledger\// || tail ~ /(^|\/)\.\.([\/"\047? \t]|$)|%2[eEfF]|%5[cC]/) hit("a-prime",n,"Contents write outside provable ledger/ prefix")
  }
}
function process(s,n,key,value) {
  s=trim(s)
  if (s ~ /^[A-Za-z_][A-Za-z_0-9]*:[ \t]+/) {
    key=s; sub(/:.*/,"",key)
    value=s; sub(/^[^:]*:[ \t]+/,"",value)
    value=unquote(value)
    if (key !~ /^(run|if|name|uses)$/) {
      if (value !~ /\$\(|`|\$\{\{/) vars[key]=resolve(value)
      else delete vars[key]
    }
  } else if (s ~ /^[A-Za-z_][A-Za-z_0-9]*=/) {
    key=s; sub(/=.*/,"",key)
    value=s; sub(/^[^=]*=/,"",value)
    value=unquote(value)
    if (value !~ /\$\(|`/) vars[key]=resolve(value)
    else delete vars[key]
  }
  inspect(s,n)
}
/^[ \t]*decide:[ \t]*(#.*)?$/ {
  if (inside) hit("structure",NR,"duplicate decide job")
  inside=1; found=1; indent=match($0,/[^ \t]/)-1
  next
}
inside {
  depth=match($0,/[^ \t]/)-1
  if ($0 !~ /^[ \t]*(#.*)?$/ && depth<=indent) inside=0
  if (!inside) next
  lines[++count]=$0; numbers[count]=NR
}
END {
  if (!found) { hit("structure",1,"decide job missing"); exit 1 }
  command=""; start=0; quote=""
  for (i=1;i<=count;i++) {
    line=lines[i]
    if (line ~ /SUPPORTER_LOOP_TOKEN|TELEGRAM_[A-Za-z_0-9]*|api[.]telegram[.]org/) hit("a",numbers[i],"forbidden credential or Telegram host")
    if (line ~ /addDiscussionComment/) hit("c",numbers[i],"discussion comment mutation name")
    if (line ~ /^[ \t]*#/) continue
    # Literal blocks preserve shell lines: do not parse their body as YAML.
    depth=match(line,/[^ \t]/)-1
    if (literal && trim(line)!="" && depth<=literal_depth) literal=0
    if (!literal) {
      if (line ~ /(:[ \t]+|^[ \t]*-[ \t]+)([!&][^ \t]+[ \t]+)*>[0-9+-]*[ \t]*(#.*)?$/) hit("d",numbers[i],"multi-line non-literal scalar in decide is not scannable")
      mapping=trim(line)
      key_depth=depth
      if (mapping ~ /^-[ \t]+/) {
        match(mapping,/^-[ \t]+/)
        key_depth+=RLENGTH
        mapping=substr(mapping,RLENGTH+1)
      }
      # Outside literal bodies, only plain mapping keys are scannable.
      if (mapping!="" && mapping !~ /^[A-Za-z_][A-Za-z_0-9-]*:( |$)/) {
        hit("d",numbers[i],"non-plain key or flow mapping in decide is not scannable")
      }
      if (mapping ~ /^[A-Za-z_][A-Za-z_0-9-]*:( |$)/) {
        key=mapping; sub(/:.*/,"",key)
        value=mapping; sub(/^[^:]*:[ \t]*/,"",value)
        if (value ~ /^[*&]/) hit("d",numbers[i],"alias or anchor in decide is not scannable")
        if (value ~ /^[{\[]/) hit("d",numbers[i],"non-plain key or flow mapping in decide is not scannable")
        # Strip YAML tags before recognizing scalar styles.
        sub(/^(![^ \t]+[ \t]+)+/,"",value)
        if (value ~ /^[*&]/) hit("d",numbers[i],"alias or anchor in decide is not scannable")
        next_line=i+1
        while (next_line<=count && lines[next_line] ~ /^[ \t]*$/) next_line++
        deeper=(next_line<=count && match(lines[next_line],/[^ \t]/)-1>key_depth)
        if ((value=="" || value ~ /^#/) && deeper) {
          following=trim(lines[next_line])
          if (following ~ /^\|[0-9+-]*[ \t]*(#.*)?$/) {
            literal=1; literal_depth=key_depth
          } else if (key ~ /^(run|if)$/ || following !~ /^(-[ ]+)?[A-Za-z_][A-Za-z_0-9-]*:( |$)/) {
            hit("d",numbers[i],"multi-line non-literal scalar in decide is not scannable")
          }
        }
        if (value ~ /^\|[0-9+-]*[ \t]*(#.*)?$/) {
          literal=1; literal_depth=key_depth
        } else if (value!="" && value !~ /^#/) {
          multiline=0
          if (deeper) multiline=1
          first=substr(value,1,1)
          if (first=="\"" || first=="\047") {
            closed=0
            for (j=2;j<=length(value);j++) {
              ch=substr(value,j,1)
              if (first=="\"" && ch=="\\") { j++; continue }
              if (ch==first) {
                if (first=="\047" && substr(value,j+1,1)==first) { j++; continue }
                closed=1; break
              }
            }
            if (!closed) multiline=1
          }
          if (multiline) hit("d",numbers[i],"multi-line non-literal scalar in decide is not scannable")
        }
      }
    }
    if (command=="") start=numbers[i]
    t=trim(line)
    sub(/^- run:[ \t]*/,"",t)
    sub(/^run:[ \t]*/,"",t)
    command=command " " t
    # Track shell quotes to keep multiline GraphQL operations one invocation.
    escaped=0
    for (c=1;c<=length(t);c++) {
      ch=substr(t,c,1)
      if (escaped) { escaped=0; continue }
      if (ch=="\\" && quote!="\047") { escaped=1; continue }
      if (quote=="") {
        if (ch=="\047" || ch=="\"") quote=ch
      } else if (ch==quote) quote=""
    }
    if (command ~ /\\[ \t]*$/) { sub(/\\[ \t]*$/,"",command); continue }
    if (quote!="") continue
    # Separate simple statements outside quotes. Resolve assignments in order:
    # a later safe assignment must never hide an earlier dangerous endpoint.
    segment=""; q=""; escaped=0
    for (c=1;c<=length(command);c++) {
      ch=substr(command,c,1)
      if (!escaped && (ch=="\047" || ch=="\"")) {
        if (q=="") q=ch
        else if (q==ch) q=""
      }
      if (q=="" && (ch==";" || substr(command,c,2)=="&&" || substr(command,c,2)=="||")) {
        process(segment,start); segment=""
        if (ch!=";") c++
      } else segment=segment ch
      if (ch=="\\" && !escaped && q!="\047") escaped=1
      else escaped=0
    }
    process(segment,start)
    command=""
  }
  if (command!="") hit("structure",start,"unterminated command or quote")
  exit bad ? 1 : 0
}
' "$1"
