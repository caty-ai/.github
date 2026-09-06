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
function resolve(s, k) {
  for (k in vars) {
    s=replace_literal(s,"${" k "}",vars[k])
    s=replace_literal(s,"${{ env." k " }}",vars[k])
    # Match an entire shell variable; $PATH must not rewrite $PATH_SUFFIX.
    s=replace_variable(s,k,vars[k])
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
function inspect(s,n, gh,curl,explicit,implicit,get,write,path,tail,facts,unresolved,query_read,request_source) {
  request_source=s
  # Field-only provenance constrains option shape, not GraphQL operation values.
  # Include every possible append before resolving variables or checking writes.
  if (field_vectors[n]) s=replace_literal(s,"\"$@\"",field_values[n])
  s=resolve(s)
  gh=(s ~ /(^|[^A-Za-z_])gh[ \t]+api([ \t]|$)/)
  curl=(s ~ /(^|[^A-Za-z_])curl([ \t]|$)/)
  if (!gh && !curl) return
  # Preserve bundle boundaries for option-argument consumption checks.
  request(resolve(request_source),gh,facts,field_vectors[n])
  unresolved=facts["method_unknown"]
  explicit=facts["write"]
  get=facts["method_seen"] && !facts["non_get"]
  implicit=facts["implicit"]
  query_read=0
  write=explicit || unresolved || (implicit && !get)
  # GraphQL query transport uses POST; the operation, not transport, decides.
  if (gh && s ~ /api[ \t]+graphql([ \t]|$)/ && s !~ /(^|[^A-Za-z_])mutation([^A-Za-z_]|$)/) {
    if (s ~ /query[= \t]+["\047]*query([ \t({]|$)/ || s ~ /query[= \t]+["\047]*\{/) { write=unresolved; query_read=1 }
    else if (implicit) hit("b",n,"GraphQL operation cannot be proven read-only")
  }
  # No write signal means a read, even when its endpoint is dynamic.
  # Only literal PUT/DELETE may use the contract-defined variable ledger tail.
  if (unresolved || (write && facts["target_unknown"] &&
      (!facts["method_seen"] || !facts["ledger_only"] || facts["non_ledger_method"]))) hit("b",n,"unresolvable gh/curl target in decide")
  if (s ~ /(^|[^A-Za-z_])mutation([^A-Za-z_]|$)/) hit("b",n,"GraphQL mutation in decide")
  if (write && (s ~ /\/(collaborators|invitations|comments|graphql)([^A-Za-z_-]|$)|\/contents\/SUPPORTERS[.]md/ || (gh && s ~ /api[ \t]+graphql([ \t]|$)/))) hit("b",n,"write to delivery endpoint")
  if (write && facts["contents_bad"]) hit("a-prime",n,"Contents write outside provable ledger/ prefix")
  if (write && match(s,/\/contents\//)) {
    tail=substr(s,RSTART+RLENGTH)
    # Traversal and encoding must not turn the allowlisted prefix into escape.
    if (tail !~ /^ledger\// || tail ~ /(^|\/)\.\.([\/"\047? \t]|$)|%2[eEfF]|%5[cC]/) hit("a-prime",n,"Contents write outside provable ledger/ prefix")
  }
}
# Inspect actual endpoint words, never a ledger-looking header or payload.
function target(t,facts, path,tail,literal) {
  if (match(t,/\/contents\//)) {
    tail=substr(t,RSTART+RLENGTH)
    if (tail !~ /^ledger\// || tail ~ /[.][.]|%2[eEfF]|%5[cC]/) facts["contents_bad"]=1
  }
  if (t !~ /[$`]/) return
  facts["target_unknown"]=1
  path=t
  sub(/^https:\/\/api[.]github[.]com\//,"",path)
  sub(/^\//,"",path)
  if (match(path,/^repos\/(OPAQUE_CONTEXT_[0-9]+|[^\/$`]+\/[^\/$`]+)\/contents\/ledger\//)) {
    tail=substr(path,RLENGTH+1)
    # A variable filename is allowed only after the complete literal prefix.
    # Reject literal traversal/encoding and nested directories in that tail.
    if (tail ~ /[$][{]?[A-Za-z_][A-Za-z_0-9]*[}]?/ &&
        tail !~ /[.][.]|%2[eEfF]|%5[cC]|\/|`|[$][(]/) {
      literal=tail
      gsub(/[$][{][A-Za-z_][A-Za-z_0-9]*[}]|[$][A-Za-z_][A-Za-z_0-9]*/,"",literal)
      if (literal !~ /[$`{}]/) return
    }
  }
  facts["ledger_only"]=0
}
# Assignments are collected before any invocation is inspected. Conflicts and
# dynamic assignments permanently invalidate a name, independent of key order.
function collect(key,value, expression,token) {
  value=unquote(value)
  while (match(value,/\$\{\{[ \t]*(inputs|github|secrets|vars)[.][A-Za-z_0-9.]+[ \t]*\}\}/)) {
    expression=substr(value,RSTART,RLENGTH)
    if (!(expression in opaque)) opaque[expression]="OPAQUE_CONTEXT_" ++opaque_count
    token=opaque[expression]
    value=substr(value,1,RSTART-1) token substr(value,RSTART+RLENGTH)
  }
  if (value ~ /[$`]/ || (key in vars && vars[key]!=value)) invalid[key]=1
  if (invalid[key]) delete vars[key]
  else vars[key]=value
}
function process(s,n,key,value) {
  s=trim(s)
  if (s ~ /^[A-Za-z_][A-Za-z_0-9]*:[ \t]+/) {
    key=s; sub(/:.*/,"",key)
    value=s; sub(/^[^:]*:[ \t]+/,"",value)
    if (key !~ /^(run|if|name|uses)$/) collect(key,value)
  } else if (s ~ /^[A-Za-z_][A-Za-z_0-9]*=/) {
    key=s; sub(/=.*/,"",key)
    value=s; sub(/^[^=]*=/,"",value)
    collect(key,value)
  }
  statements[++statement_count]=s; statement_lines[statement_count]=n
}
# Read shell words without splitting quoted option values (headers, payloads).
# Classify method options separately from header/payload option arguments.
# Only positional targets and --url values participate in target resolution.
function bundle(s, j,ch,q,escaped) {
  for (j=1;j<=length(s);j++) {
    ch=substr(s,j,1)
    if (escaped) { escaped=0; continue }
    if (ch=="\\" && q!="\047") { escaped=1; continue }
    if (ch=="\047" || ch=="\"") {
      if (q=="") q=ch
      else if (q==ch) q=""
    }
    if (ch=="$" && q!="\047" && substr(s,j) ~ /^[$]([@*]|[{]([@*]([}:])|[^}]*\[[^]]*\][^}]*[}]))/) return 1
  }
  return 0
}
function request(s,gh,facts,fields, words,raw_words,field_word,raw,total,j,ch,q,escaped,word,t,skip,method,target_seen) {
  if (gh) sub(/^.*gh[ \t]+api[ \t]+/,"",s)
  else sub(/^.*curl[ \t]+/,"",s)
  facts["ledger_only"]=1
  total=0; word=""; q=""; escaped=0
  for (j=1;j<=length(s)+1;j++) {
    ch=substr(s,j,1)
    if (j<=length(s) && (q!="" || ch !~ /[ \t]/ || escaped)) raw=raw ch
    if (escaped) { word=word ch; escaped=0; continue }
    if (ch=="\\" && q!="\047") { escaped=1; continue }
    if (ch=="\047" || ch=="\"") {
      if (q=="") { q=ch; continue }
      if (q==ch) { q=""; continue }
    }
    if (j>length(s) || (q=="" && ch ~ /[ \t]/)) {
      if (word!="") { words[++total]=word; raw_words[total]=raw }
      word=""; raw=""
    } else word=word ch
  }
  # A bundle can supply extra options even when its first word is a payload,
  # header, method, or URL argument. Check before consuming option arguments.
  for (j=1;j<=total;j++) {
    if (bundle(raw_words[j])) {
      if (gh && fields && raw_words[j]=="\"$@\"") field_word[j]=1
      else facts["method_unknown"]=1
    }
  }
  for (j=1;j<=total;j++) {
    t=words[j]
    if (t ~ /^[|&]/) break
    # Redirections may precede method flags in the same invocation.
    if (t ~ /^[0-9]*[<>]+$/) {
      if (field_word[++j]) facts["method_unknown"]=1
      continue
    }
    if (t ~ /^[0-9]*[<>]/) continue
    if (skip) {
      if (field_word[j]) facts["method_unknown"]=1
      skip=0; continue
    }
    # Field-pair provenance only holds at an option boundary. Consuming its
    # first -f as a header/value would expose the next word as an option.
    if (field_word[j]) facts["implicit"]=1
    if (t ~ /[$]([0-9]|[{][0-9]+[}])/) facts["method_unknown"]=1
    if (!gh && t ~ /^(-[A-Za-z]*[FK]|--(form|form-string|config)(=|$))/) facts["method_unknown"]=1
    method=""
    if (t=="-X" || (gh && t=="--method") || (!gh && t=="--request")) method=words[++j]
    else if (t ~ /^-X./) method=substr(t,3)
    else if (gh && t ~ /^--method=/) method=substr(t,10)
    else if (!gh && t ~ /^--request=/) method=substr(t,11)
    else if (t=="--url" && !gh) {
      target(words[++j],facts)
      if (field_word[j]) facts["method_unknown"]=1
      continue
    } else if (t ~ /^--url=/ && !gh) {
      target(substr(t,7),facts)
      continue
    } else {
      if ((gh && t ~ /^(-[fF]|--(input|raw-field|field)(=|$))/) || (!gh && t ~ /^(-[dT]|--(data|data-raw|data-binary|data-urlencode|json|upload-file)(=|$))/)) facts["implicit"]=1
      if ((gh && t ~ /^(-H|--header|-f|-F|--field|--raw-field|--input|--hostname|--jq|-q|--template|-t|--cache|-p|--preview)$/) || (!gh && t ~ /^(-H|--header|-F|--form|--form-string|-d|-T|--data|--data-raw|--data-binary|--data-urlencode|--json|--upload-file|-o|--output|-w|--write-out|--connect-timeout|--max-time|-u|--user|-A|--user-agent|-e|--referer)$/)) { skip=1; continue }
      if (t ~ /^-/) continue
      if (!gh || !target_seen) {
        target(t,facts)
        target_seen=1
      }
      continue
    }
    if (field_word[j]) facts["method_unknown"]=1
    method=toupper(method)
    facts["method_seen"]=1
    if (method!="GET") facts["non_get"]=1
    if (method!="PUT" && method!="DELETE") facts["non_ledger_method"]=1
    if (method=="" || method ~ /[$`]|OPAQUE_CONTEXT_/) facts["method_unknown"]=1
    if (method ~ /^(PUT|POST|PATCH|DELETE)$/) facts["write"]=1
  }
}

# A deliberately small provenance grammar for field-only argument builders.
# Proof starts at a function boundary and an unconditional empty reset. Before
# the reset, only local declarations and a single-line return guard are allowed.
# Afterwards only jq/read plumbing and quoted -f/-F pair appends preserve it.
# Anything else (including calls, eval, shift, another reset, or scope exit)
# discards the proof. No endpoint or function name earns an exemption.
function field_builder(s,n, append,plumbing,invocation) {
  s=trim(s)
  if (s=="" || s ~ /^#/) return
  if (s ~ /^[A-Za-z_][A-Za-z_0-9]*[ \t]*\(\)[ \t]*\{[ \t]*$/) {
    field_prefix=1; field_safe=0; field_appends=""; return
  }
  if (field_prefix) {
    if (s=="set --") { field_prefix=0; field_safe=1; return }
    if (s ~ /^local [A-Za-z_]/ && s !~ /[;`{}]|[$][(]/) return
    if (s ~ /^case "[^"`]+" in [A-Za-z_0-9*]+\) ;; \*\) return [0-9]+ ;; esac$/) return
    field_prefix=0
  }
  if (!field_safe) return
  if (s ~ /^gh[ \t]+api[ \t]/) {
    invocation=s
    sub(/[ \t]+\|\|[ \t]+return[ \t]+[0-9]+[ \t]*$/,"",invocation)
    if (invocation !~ /[;|&`]|[$][(]/) {
      field_vectors[n]=1
      field_values[n]=field_appends
    }
    field_safe=0; return
  }
  append="set -- \"\\$@\" -[fF] \"[^\"`]*=[^\"`]*\""
  if (s ~ ("^" append "$") ||
      s ~ ("^if \\[ [^][;`&|]+ \\]; then " append "$") ||
      s ~ ("^else " append "; fi$")) {
    plumbing=s
    sub(/^.*set -- "[$]@" /,"",plumbing)
    sub(/; fi$/,"",plumbing)
    if (s !~ /[$][(]/ && !bundle(plumbing)) {
      field_appends=field_appends " " plumbing
      return
    }
  }
  if (s ~ /^while IFS= read -r [A-Za-z_][A-Za-z_0-9]*; do$/) return
  if (s ~ /^[A-Za-z_][A-Za-z_0-9]*=\$\(jq [^;`]*\)$/ || s ~ /^done < <\(jq [^;`]*\)$/) {
    plumbing=s
    sub(/^[^(]*\(/,"",plumbing); sub(/\)$/,"",plumbing)
    if (plumbing !~ /[()&]/) return
  }
  field_safe=0
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
    if (trim(line)=="") continue
    # Literal blocks preserve shell lines: do not parse their body as YAML.
    depth=match(line,/[^ \t]/)-1
    if (literal && trim(line)!="" && depth<=literal_depth) literal=0
    if (literal) field_builder(line,numbers[i])
    else { field_prefix=0; field_safe=0 }
    if (!literal) {
      if (line ~ /(:[ \t]+|^[ \t]*-[ \t]+)([!&][^ \t]+[ \t]+)*>[0-9+-]*[ \t]*(#.*)?$/) hit("d",numbers[i],"multi-line non-literal scalar in decide is not scannable")
      mapping=trim(line)
      sequence=(mapping ~ /^-[ \t]+/)
      key_depth=depth
      if (mapping ~ /^-[ \t]+/) {
        match(mapping,/^-[ \t]+/)
        key_depth+=RLENGTH
        mapping=substr(mapping,RLENGTH+1)
      }
      # Track YAML ancestry, including indentless sequences, without treating
      # defaults.run (a mapping) as a step run (an executable scalar).
      parent=""; parent_depth=-1
      for (level in keys) {
        if (level+0>=key_depth) delete keys[level]
        else if (level+0>parent_depth) { parent_depth=level; parent=keys[level] }
      }
      scalar_sequence=sequence && parent!="steps" && parent!="run" && parent!="if" && parent!=""
      # Outside literal bodies, only plain mapping keys are scannable.
      if (!scalar_sequence && mapping!="" && mapping !~ /^[A-Za-z_][A-Za-z_0-9-]*:( |$)/) {
        hit("d",numbers[i],"non-plain key or flow mapping in decide is not scannable")
      }
      if (mapping ~ /^[A-Za-z_][A-Za-z_0-9-]*:( |$)/) {
        key=mapping; sub(/:.*/,"",key)
        value=mapping; sub(/^[^:]*:[ \t]*/,"",value)
        keys[key_depth]=key
        if (parent=="env") collect(key,value)
        if (key=="run" && parent!="defaults" && value ~ /^!/) hit("d",numbers[i],"tagged run scalar in decide is not scannable")
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
          } else if ((key=="run" && parent!="defaults") || key=="if" || (following !~ /^-[ ]+/ && following !~ /^[A-Za-z_][A-Za-z_0-9-]*:( |$)/)) {
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
              if (first=="\"" && ch=="\\") {
                if (key=="run") hit("d",numbers[i],"escaped run scalar in decide is not scannable")
                j++; continue
              }
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
    # Separate simple statements outside quotes for the collection pass.
    segment=""; q=""; escaped=0
    for (c=1;c<=length(command);c++) {
      ch=substr(command,c,1)
      if (!escaped && (ch=="\047" || ch=="\"")) {
        if (q=="") q=ch
        else if (q==ch) q=""
      }
      if (q=="" && (ch==";" || ch=="|" || substr(command,c,2)=="&&")) {
        process(segment,start); segment=""
        if (substr(command,c,2)=="&&" || substr(command,c,2)=="||") c++
      } else segment=segment ch
      if (ch=="\\" && !escaped && q!="\047") escaped=1
      else escaped=0
    }
    process(segment,start)
    command=""
  }
  if (command!="") hit("structure",start,"unterminated command or quote")
  for (i=1;i<=statement_count;i++) inspect(statements[i],statement_lines[i])
  exit bad ? 1 : 0
}
' "$1"
